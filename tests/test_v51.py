"""Real Sn force-field regression, not an ignored-parameter smoke test."""
import tempfile
import unittest
import numpy as np
import TinOxoStudio as c
import TinOxoWeb as w


def completed(n):
    project=c.template(n)
    for slot in list(project['slots']):
        smiles='CC(=O)O' if slot['kind']=='L' else 'CP(C)(=O)O' if slot['kind']=='P' else '[*:1]CCC'
        c.attach_fragment(project,smiles,slot_id=slot['id'],cleanup=False)
    return project


class SnForcefieldTests(unittest.TestCase):
    def test_sn12_valence_failure_is_reproduced_and_uff_model_preserves_chemistry(self):
        for n in (3,6,12):
            for p in (c.template(n),completed(n)):
                before=c.clone(p)
                with c.rdBase.BlockLogs():
                    if n==12:
                        with self.assertRaises(c.Chem.AtomValenceException):c.project_to_rdkit(p,sanitize=True)
                    mol,mapping=c.forcefield_model(p)
                    self.assertTrue(c.AllChem.UFFHasAllMoleculeParams(mol))
                    ff=c.make_forcefield(mol,'UFF');ff.Initialize()
                self.assertTrue(np.isfinite(ff.CalcEnergy()))
                self.assertTrue(np.isfinite(ff.CalcGrad()).all())
                self.assertEqual(mol.GetNumBonds(),len(p['bonds']))
                for atom in p['atoms']:
                    rd=mol.GetAtomWithIdx(mapping[atom['id']])
                    self.assertEqual(rd.GetFormalCharge(),atom.get('charge',0))
                    self.assertEqual(rd.GetNumRadicalElectrons(),atom.get('radical',0))
                self.assertEqual(p,before)

    def test_real_sn_uff_runs_all_scopes_and_preserves_fixed_or_rigid_atoms(self):
        for n in (3,6,12):
            p=completed(n);before=c.clone(p)
            for scope in c.SCOPES:
                plan=c.scope_plan(p,scope,False)
                with c.rdBase.BlockLogs():out,logs=c.optimize_project(p,'UFF',scope,steps=40,respect_fixed=False)
                result=logs[0];self.assertEqual(result['forcefield'],'UFF');self.assertFalse(result['fallback'])
                self.assertLessEqual(result['after_kcal_mol'],result['before_kcal_mol']+1.e-7)
                a,b=c.index_atoms(p),c.index_atoms(out)
                self.assertTrue(any(np.linalg.norm(c.xyz(a[i])-c.xyz(b[i]))>1.e-6 for i in plan['movingIds']))
                for i in plan['fixedIds']:np.testing.assert_array_equal(c.xyz(a[i]),c.xyz(b[i]))
                if scope=='rigid':
                    for group in [plan['coreIds']]+plan['groups']:
                        x=np.array([c.xyz(a[i]) for i in group]);y=np.array([c.xyz(b[i]) for i in group])
                        np.testing.assert_allclose(np.linalg.norm(x[:,None]-x[None,:],axis=-1),np.linalg.norm(y[:,None]-y[None,:],axis=-1),atol=1.e-10)
                self.assertEqual(out['bonds'],p['bonds'])
            self.assertEqual(p,before)

    def test_mmff_fallback_is_opt_in_recorded_and_keeps_requested_scope(self):
        p=completed(12);before=c.clone(p);updates=[]
        with self.assertRaisesRegex(ValueError,'MMFF94에는 Sn 원자형이 없습니다'):c.optimize_project(p,'MMFF94','all',steps=15,respect_fixed=False)
        with c.rdBase.BlockLogs():
            out,logs=c.optimize_project(p,'MMFF94','rigid',steps=15,respect_fixed=False,allow_uff_fallback=True,progress=updates.append)
            direct,dlogs=c.optimize_project(p,'UFF','rigid',steps=15,respect_fixed=False)
        r=logs[0];self.assertTrue(r['fallback']);self.assertEqual(r['requestedForcefield'],'MMFF94')
        self.assertEqual(r['forcefield'],'UFF');self.assertEqual(r['scope'],'rigid')
        self.assertIn('Sn',r['notice']);self.assertTrue(any('MMFF94 → UFF' in u['message'] for u in updates))
        self.assertEqual(out['atoms'],direct['atoms']);self.assertEqual(p,before)

    def test_organic_valence_errors_are_still_rejected_in_sn_models(self):
        p=c.template(12);start=max(a['id'] for a in p['atoms'])+1
        for k in range(6):p['atoms'].append(dict(id=start+k,element='C' if k==0 else 'H',x=20+k,y=0,z=0))
        for k in range(1,6):p['bonds'].append(dict(a=start,b=start+k,order=1))
        with c.rdBase.BlockLogs():
            with self.assertRaises(c.Chem.AtomValenceException):c.forcefield_model(p)

    def test_fallback_also_handles_other_unsupported_mmff_types(self):
        f=c.build_fragment('B(O)(O)O',mode='coordinate',ff_choice='UFF',conformers=1)
        p=c.new_project();p['atoms']=f['atoms'];p['bonds']=f['bonds']
        out,logs=c.optimize_project(p,'MMFF94','all',steps=10,respect_fixed=False,allow_uff_fallback=True)
        self.assertEqual(logs[0]['forcefield'],'UFF');self.assertTrue(logs[0]['fallback'])
        self.assertNotIn('Sn',logs[0]['notice'])

    def test_supported_mmff_stays_mmff_when_fallback_enabled(self):
        f=c.build_fragment('CCCO',mode='coordinate',conformers=1)
        p=c.new_project();p['atoms']=f['atoms'];p['bonds']=f['bonds']
        out,logs=c.optimize_project(p,'MMFF94','all',steps=10,respect_fixed=False,allow_uff_fallback=True)
        self.assertEqual(logs[0]['forcefield'],'MMFF94');self.assertFalse(logs[0]['fallback'])

    def test_sn_web_job_reports_actual_uff_and_can_disable_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            ws=w.Workspace(directory);ws.project=completed(6)
            try:
                with c.rdBase.BlockLogs():
                    ws.start_job('optimize',dict(revision=0,scope='core_fixed',steps=15,ff='MMFF94',respect_fixed=False,allow_uff_fallback=True))
                    ws.job['thread'].join(20)
                job=ws.public_job();self.assertEqual(job['status'],'done',job)
                self.assertEqual(job['percent'],100);self.assertEqual(job['results'][0]['forcefield'],'UFF')
                before=c.clone(ws.project)
                ws.start_job('optimize',dict(revision=1,scope='all',steps=15,ff='MMFF94',allow_uff_fallback=False))
                ws.job['thread'].join(20);self.assertEqual(ws.public_job()['status'],'error')
                self.assertEqual(ws.project,before);self.assertEqual(ws.revision,1)
            finally:ws.close()


if __name__=='__main__':unittest.main()
