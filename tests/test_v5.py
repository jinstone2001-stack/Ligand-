"""v5 scope/rigidity, actual force fields, contact gradients and async jobs."""
import tempfile
import threading
import unittest
from unittest import mock
import numpy as np
from scipy.optimize._numdiff import approx_derivative
import TinOxoStudio as c
import TinOxoWeb as w
from TinOxoOptimize import Coordinates, ContactObjective


def molecule():
    f=c.build_fragment('CCCCO',mode='coordinate',conformers=1)
    p=c.new_project();p['atoms']=c.clone(f['atoms']);p['bonds']=c.clone(f['bonds'])
    for a in p['atoms']:a['id']+=1
    for b in p['bonds']:b['a']+=1;b['b']+=1
    a=c.index_atoms(p);g=c.adjacency(p);first=p['atoms'][0]['id']
    core={first}|{i for i in g[first] if a[i]['element']=='H'}
    for atom in p['atoms']:atom['core']=atom['id'] in core;atom['fixed']=atom['core']
    # Deliberately strain the core/ligand junction so optimization must move.
    p['atoms'][0]['x']+=.45
    return p


def positions(p):return np.array([c.xyz(a) for a in p['atoms']])
def distances(p,ids):
    a=c.index_atoms(p);r=np.array([c.xyz(a[i]) for i in ids])
    return np.linalg.norm(r[:,None,:]-r[None,:,:],axis=2)


class ScopeTests(unittest.TestCase):
    def test_exact_fixed_sets_and_manual_override(self):
        p=molecule();allids={a['id'] for a in p['atoms']};core={a['id'] for a in p['atoms'] if a['core']}
        for scope,expected in [('core_fixed',core),('all',set()),('core_only',allids-core),('rigid',core)]:
            self.assertEqual(set(c.scope_plan(p,scope,False)['fixedIds']),expected)
        self.assertEqual(set(c.scope_plan(p,'all',True)['fixedIds']),core)
        self.assertEqual(c.scope_plan(p,'core_only',True)['movingCount'],0)

    def test_real_forcefield_modes_move_only_allowed_atoms(self):
        for ff in ('MMFF94','UFF'):
            for scope in c.SCOPES:
                with self.subTest(ff=ff,scope=scope):
                    p=molecule();before=c.clone(p);plan=c.scope_plan(p,scope,False);updates=[]
                    out,logs=c.optimize_project(p,ff,scope,steps=120,respect_fixed=False,progress=updates.append)
                    self.assertEqual(p,before)
                    self.assertLessEqual(logs[0]['after_kcal_mol'],logs[0]['before_kcal_mol']+1.e-7)
                    self.assertGreater(np.linalg.norm(positions(out)-positions(p)),1.e-6)
                    aa,bb=c.index_atoms(out),c.index_atoms(p)
                    for i in plan['fixedIds']:np.testing.assert_array_equal(c.xyz(aa[i]),c.xyz(bb[i]))
                    if scope=='rigid':
                        for group in [plan['coreIds']]+plan['groups']:
                            np.testing.assert_allclose(distances(out,group),distances(p,group),atol=1.e-10)
                    self.assertTrue(updates)

    def test_rigid_nested_and_bridge_groups_ignore_slot_boundaries(self):
        p=c.template(6);s=c.attach_fragment(p,'CC(=O)O',slot_id='L1',cleanup=False)
        parent=next(a['id'] for a in p['atoms'] if a['id'] in s['ligandIds'] and a['element']=='C' and len(c.adjacency(p)[a['id']])==4)
        child=c.attach_fragment(p,'[*:1]O',parent=parent,cleanup=False)
        plan=c.scope_plan(p,'rigid',False)
        expected=set(s['ligandIds']+child['ligandIds']) & set(c.index_atoms(p))
        self.assertTrue(any(set(g)==expected for g in plan['groups']))
        coords=Coordinates(p,plan);v=np.linspace(-.3,.5,len(coords.x0));r=coords.decode(v)
        ix={a['id']:i for i,a in enumerate(p['atoms'])}
        for group in [plan['coreIds']]+plan['groups']:
            points=np.array([r[ix[i]] for i in group]);d=np.linalg.norm(points[:,None,:]-points[None,:,:],axis=2)
            np.testing.assert_allclose(d,distances(p,group),atol=1.e-10)
        c.index_atoms(p)[child['anchor']]['fixed']=True
        locked=c.scope_plan(p,'rigid',True)
        self.assertTrue(expected<=set(locked['fixedIds']))

    def test_rigid_gradient_matches_numerical_derivative(self):
        p=molecule();coords=Coordinates(p,c.scope_plan(p,'rigid',False))
        x=np.linspace(-.5,.8,len(coords.x0));target=coords.initial+.2
        def energy(v):return np.sum((coords.decode(v)-target)**2)
        analytic=coords.gradient(x,2*(coords.decode(x)-target))
        np.testing.assert_allclose(analytic,approx_derivative(energy,x).ravel(),rtol=1.e-5,atol=1.e-6)

    def test_bad_scope_no_core_empty_or_no_moving_fail(self):
        p=molecule()
        with self.assertRaises(ValueError):c.scope_plan(p,'typo')
        with self.assertRaises(ValueError):c.cleanup_project(c.clone(p),scope='core_only',respect_fixed=True)
        for a in p['atoms']:a['core']=False
        with self.assertRaises(ValueError):c.scope_plan(p,'rigid')
        self.assertEqual(c.scope_plan(p,'all',False)['movingCount'],len(p['atoms']))
        with self.assertRaises(ValueError):c.scope_plan(c.new_project(),'all')


class ContactTests(unittest.TestCase):
    def fixture(self):
        p=c.template(3);s=c.attach_fragment(p,'[*:1]CCC',slot_id='R1',cleanup=False)
        # Add a close, unbonded probe to create a real movable contact.
        a=c.index_atoms(p);probe=c.xyz(a[s['ligandIds'][-1]])+np.array([.25,.3,.15])
        p['atoms'].append(dict(id=max(a)+1,element='O',x=probe[0],y=probe[1],z=probe[2],core=False))
        return p

    def test_contact_objective_gradient_and_inspector_agree(self):
        p=self.fixture()
        for mode in ('radii','minimum'):
            criteria={**c.DEFAULTS['contact'],'mode':mode};o=ContactObjective(p,c.radius,criteria);x=positions(p)
            energy,grad=o(x)
            score=sum((r['threshold']-r['distance'])**2 for r in c.clashes(p,criteria))
            self.assertAlmostEqual(energy,score,places=10)
            numerical=approx_derivative(lambda v:o(v.reshape(-1,3))[0],x.ravel()).ravel()
            np.testing.assert_allclose(grad.ravel(),numerical,atol=2.e-5,rtol=1.e-4)

    def test_all_cleanup_scopes_preserve_constraints_and_reduce_objective(self):
        for scope in c.SCOPES:
            p=self.fixture();before=c.clone(p);plan=c.scope_plan(p,scope,False)
            c.cleanup_project(p,scope=scope,steps=100,respect_fixed=False)
            result=p['metadata']['lastCleanup']
            self.assertLessEqual(result['after'],result['before']+1.e-7)
            self.assertLessEqual(result['afterOverlapScore'],result['beforeOverlapScore']+1.e-7)
            a,b=c.index_atoms(p),c.index_atoms(before)
            for i in plan['fixedIds']:np.testing.assert_array_equal(c.xyz(a[i]),c.xyz(b[i]))
            if scope=='rigid':
                for group in [plan['coreIds']]+plan['groups']:
                    np.testing.assert_allclose(distances(p,group),distances(before,group),atol=1.e-10)

    def test_cancellation_during_evaluation_keeps_input(self):
        p=self.fixture();before=c.clone(p);ev=threading.Event()
        def progress(v):ev.set()
        with self.assertRaises(InterruptedError):c.cleanup_project(p,scope='rigid',cancel=ev,progress=progress,respect_fixed=False)
        self.assertEqual(p,before)


class LibraryTests(unittest.TestCase):
    def test_builtin_acids_are_neutral_and_nitro_valid(self):
        for category,name,smiles,mode in c.BUILTIN_LIGANDS:
            mol=c.Chem.MolFromSmiles(smiles)
            self.assertIsNotNone(mol,name);self.assertEqual(c.Chem.GetFormalCharge(mol),0,name)
            if mode=='bridge':
                self.assertTrue(any(a.GetSymbol()=='O' and a.GetTotalNumHs()==1 for a in mol.GetAtoms()),name)
                kind='P' if 'P 전구체' in category else 'L'
                f=c.build_fragment(smiles,kind,conformers=1)
                self.assertEqual(sum(a['charge'] for a in f['atoms']),-1)
        nitro=next(s for _,n,s,_ in c.BUILTIN_LIGANDS if n=='니트로')
        self.assertIn('[N+]',nitro);self.assertIn('[O-]',nitro)


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ws=w.Workspace(self.tmp.name);self.ws.project=molecule()
    def tearDown(self):self.tmp.cleanup()
    def wait(self):
        self.ws.job['thread'].join(20);self.assertFalse(self.ws.job['thread'].is_alive());return self.ws.public_job()
    def test_scope_preview_and_progress_done(self):
        plan=self.ws.query('scope',dict(scope='core_only',respect_fixed=False));self.assertGreater(plan['movingCount'],0)
        self.ws.start_job('optimize',dict(revision=0,scope='core_only',respect_fixed=False,steps=50))
        job=self.wait();self.assertEqual(job['status'],'done',job);self.assertEqual(job['percent'],100)
        self.assertIn('results',job);self.assertGreaterEqual(job['finishedAt'],job['startedAt'])
        self.ws.mutate('undo',dict(revision=1));np.testing.assert_allclose(positions(self.ws.project),positions(molecule()))
    def test_error_keeps_original_and_does_not_show_100(self):
        p=self.ws.project
        self.ws.start_job('optimize',dict(revision=0,scope='bad'));job=self.wait()
        self.assertEqual(job['status'],'error');self.assertLess(job['percent'],100);self.assertIs(self.ws.project,p)
    def test_noninteger_iteration_budgets_are_rejected(self):
        for steps in (True,1.5,0,10001):
            for action in ('optimize','cleanup'):
                self.ws.start_job(action,dict(revision=0,scope='all',respect_fixed=False,steps=steps))
                self.assertEqual(self.wait()['status'],'error')
                self.assertEqual(self.ws.revision,0)
    def test_active_contact_fields_only_and_inactive_values_preserved(self):
        self.ws.mutate('contacts',dict(revision=0,criteria=dict(mode='minimum',minimum=2.2,vdw='ignored')))
        self.assertEqual(self.ws.settings['contact']['vdw'],.75)
        self.ws.mutate('contacts',dict(revision=1,criteria=dict(mode='radii',vdw=.8,covalent=1.2,minimum='ignored')))
        self.assertEqual(self.ws.settings['contact']['minimum'],2.2)
        with self.assertRaises(ValueError):self.ws.mutate('contacts',dict(revision=2,criteria=dict(mode='minimum',minimum=float('nan'))))
        self.assertEqual(self.ws.revision,2)
    def test_mid_job_percentage_and_cancel_no_partial_commit(self):
        reached=threading.Event()
        def calculation(p,*args,**kw):
            kw['progress'](dict(message='실제 1/2 작업 완료',percent=50));reached.set()
            kw['cancel'].wait(3);raise InterruptedError('취소')
        original=self.ws.project
        with mock.patch.object(c,'optimize_project',side_effect=calculation):
            self.ws.start_job('optimize',dict(revision=0));self.assertTrue(reached.wait(3))
            self.assertEqual(self.ws.public_job()['percent'],50)
            self.ws.job['cancel'].set();job=self.wait()
        self.assertEqual(job['status'],'cancelled');self.assertEqual(job['percent'],50)
        self.assertIs(self.ws.project,original);self.assertEqual(self.ws.revision,0)


if __name__=='__main__':unittest.main()
