"""Exterior placement, mass frame and hollow-core crossing regressions."""
import itertools
import tempfile
import threading
import unittest
from unittest import mock
import numpy as np
import TinOxoStudio as c
import TinOxoWeb as w
from TinOxoPlacement import CorePlacement, atom_mass


def box_core(planar=False):
    p=c.new_project()
    points=list(itertools.product((-2.,2.),(-2.,2.),(0.,) if planar else (-2.,2.)))
    p['atoms']=[dict(id=i+1,element='Sn',x=x,y=y,z=z,core=True) for i,(x,y,z) in enumerate(points)]
    p['bonds']=[dict(a=1,b=i,order=1) for i in range(2,len(points)+1)]
    return p


def two_box_cores():
    p=box_core()
    for atom in p['atoms']:c.set_xyz(atom,1.5*c.xyz(atom))
    second=c.clone(p)
    for atom in second['atoms']:p['atoms'].append({**atom,'id':atom['id']+100,'x':atom['x']+8})
    for bond in second['bonds']:p['bonds'].append({**bond,'a':bond['a']+100,'b':bond['b']+100})
    p['atoms'].append(dict(id=9,element='Sn',x=3.,y=0.,z=0.,core=True))
    p['bonds'].append(dict(a=9,b=1,order=1))
    return p


def assert_exterior(test,p,slot):
    atoms=c.index_atoms(p);new=[atoms[i] for i in slot['ligandIds']]
    guard=CorePlacement(p,slot['sn'],new,p['bonds'])
    test.assertTrue(guard.safe([c.xyz(a) for a in new]))
    if len(slot['sn'])==1 and atoms[slot['sn'][0]].get('core'):
        vector=c.xyz(atoms[slot['anchor']])-c.xyz(atoms[slot['sn'][0]])
        test.assertGreater(float(vector@guard.outward(c.xyz(atoms[slot['sn'][0]]))),0.)


class CoreGeometryTests(unittest.TestCase):
    def test_mass_center_uses_core_only_and_isotope_mass(self):
        p=c.new_project();p['atoms']=[dict(id=1,element='Sn',x=0,y=0,z=0,core=True,isotope=120),
            dict(id=2,element='O',x=4,y=0,z=0,core=True),dict(id=3,element='H',x=-2,y=0,z=0,core=True),
            dict(id=4,element='Au',x=1000,y=500,z=100,core=False)]
        p['bonds']=[dict(a=1,b=i,order=1) for i in (2,3,4)]
        guard=CorePlacement(p,[1],[],[])
        masses=[atom_mass(a) for a in p['atoms'][:3]]
        expected=(masses[1]*4-masses[2]*2)/sum(masses)
        np.testing.assert_allclose(guard.center,[expected,0,0],atol=1.e-12)
        self.assertNotAlmostEqual(expected,2/3)
        p['atoms'][3]['x']=-9999
        np.testing.assert_array_equal(guard.center,CorePlacement(p,[1],[],[]).center)

    def test_separate_core_components_do_not_shift_the_host_frame(self):
        p=c.template(12);reference=CorePlacement(p,[1],[],[])
        second=c.template(3)
        for a in second['atoms']:p['atoms'].append({**a,'id':a['id']+1000,'x':a['x']+100})
        for b in second['bonds']:p['bonds'].append({**b,'a':b['a']+1000,'b':b['b']+1000})
        result=CorePlacement(p,[1],[],[])
        np.testing.assert_array_equal(result.center,reference.center)
        self.assertEqual(result.ids,reference.ids)

    def test_atoms_and_bonds_cannot_cross_an_empty_core_cavity(self):
        p=box_core();new=[dict(id=100,element='C'),dict(id=101,element='C')]
        guard=CorePlacement(p,[1],new,[dict(a=100,b=101)])
        self.assertFalse(guard.safe([[0,0,0],[3,0,0]]))
        # Both atoms are outside, but their bond passes through the hollow cage.
        self.assertFalse(guard.safe([[-3,0,0],[3,0,0]]))
        self.assertTrue(guard.safe([[-3,2.2,0],[3,2.2,0]]))
        self.assertFalse(guard.safe([[float('nan'),0,0],[3,2.2,0]]))
        # An organic branch's new attachment bond must not tunnel through it.
        p['atoms'].append(dict(id=99,element='C',x=-3,y=0,z=0,core=False))
        branch=CorePlacement(p,[99],[new[0]],[dict(a=99,b=100)])
        self.assertFalse(branch.safe([[3,0,0]]))
        self.assertTrue(branch.safe([[-3,0,2]]))

    def test_all_core_envelopes_are_checked_without_filling_the_gap(self):
        p=two_box_cores();new=[dict(id=200,element='C'),dict(id=201,element='C')]
        guard=CorePlacement(p,[9],new,[dict(a=200,b=201)])
        self.assertFalse(guard.safe([[8,0,0],[12,0,0]]))
        self.assertFalse(guard.safe([[4,0,0],[12,0,0]]))
        self.assertTrue(guard.safe([[3.5,0,0],[4.5,0,0]]))
        p['atoms'].append(dict(id=50,element='C',x=4.,y=0.,z=0.,core=False))
        branch=CorePlacement(p,[50],[new[0]],[dict(a=50,b=200)])
        self.assertFalse(branch.safe([[12,0,0]]))

    def test_planar_core_and_rigid_frame_transform(self):
        p=box_core(planar=True);new=[dict(id=100,element='C')]
        guard=CorePlacement(p,[1],new,[])
        self.assertFalse(guard.safe([[0,0,.5]]));self.assertTrue(guard.safe([[0,0,1.]]))
        rotation=c.axis_rotation([1,2,3],.7);shift=np.array([10.,-4.,7.])
        for atom in p['atoms']:c.set_xyz(atom,c.xyz(atom)@rotation.T+shift)
        moved=CorePlacement(p,[1],new,[])
        np.testing.assert_allclose(moved.center,guard.center@rotation.T+shift,atol=1.e-12)
        self.assertFalse(moved.safe(np.array([[0,0,.5]])@rotation.T+shift))
        self.assertTrue(moved.safe(np.array([[0,0,1.]])@rotation.T+shift))


class AttachmentTests(unittest.TestCase):
    def test_automatic_attachment_avoids_a_second_hollow_core(self):
        p=two_box_cores();reference=CorePlacement(p,[9],[],[])
        slot=c.attach_fragment(p,'[*:1]C',parent=9)
        points=np.array([c.xyz(c.index_atoms(p)[i]) for i in slot['ligandIds']])
        self.assertFalse(np.any(np.all((points>[5.05,-2.95,-2.95])&(points<[10.95,2.95,2.95]),axis=1)))
        np.testing.assert_array_equal(slot['placement']['coreCenterOfMass'],reference.center)
        before=c.clone(p)
        with self.assertRaisesRegex(ValueError,'배치를 찾지 못했습니다'):
            c.attach_fragment(p,'[*:1]C',slot_id=slot['id'],direction=[1,0,0])
        self.assertEqual(p,before)

    def test_all_template_r_sites_use_exterior_poses_and_preserve_core(self):
        cache={}
        for n in (3,6,12):
            for oldslot in c.template(n)['slots']:
                if oldslot['kind']!='R':continue
                p=c.template(n);before={a['id']:c.xyz(a).copy() for a in p['atoms']}
                slot=c.attach_fragment(p,'[*:1]CCCCCC',slot_id=oldslot['id'],fragment_cache=cache)
                assert_exterior(self,p,slot);self.assertEqual(slot['placement']['policy'],'core-outward-5.2')
                for i,point in before.items():np.testing.assert_array_equal(c.xyz(c.index_atoms(p)[i]),point)
                self.assertAlmostEqual(np.linalg.norm(c.xyz(c.index_atoms(p)[slot['anchor']])-before[slot['sn'][0]]),2.15,places=10)

    def test_general_sn_attachment_and_all_six_hydroxo_sites(self):
        p=c.template(12);slot=c.attach_fragment(p,'CCN',parent=1,mode='coordinate',attachment_index=2)
        assert_exterior(self,p,slot)
        p=c.template(12);ids,removed=c.prepare_hydroxo(p)
        before={a['id']:c.xyz(a).copy() for a in p['atoms']}
        for parent in ids:
            slot=c.attach_fragment(p,'[*:1]CCCC',parent=parent,cleanup=False)
            assert_exterior(self,p,slot)
        for i,point in before.items():np.testing.assert_array_equal(c.xyz(c.index_atoms(p)[i]),point)

    def test_old_inward_slot_is_corrected_and_explicit_inward_is_rejected(self):
        p=c.template(12);slot=p['slots'][0];host=c.index_atoms(p)[slot['sn'][0]]
        radial=CorePlacement(p,slot['sn'],[],[]).outward(c.xyz(host))
        slot['direction']=(-radial).tolist()
        slot=c.attach_fragment(p,'[*:1]CCCCCC',slot_id=slot['id'])
        assert_exterior(self,p,slot)
        before=c.clone(p)
        with self.assertRaisesRegex(ValueError,'무게중심을 향합니다'):
            c.attach_fragment(p,'[*:1]CC',slot_id=slot['id'],direction=-radial)
        self.assertEqual(p,before)

    def test_cluttered_hollow_core_prioritizes_exterior_poses(self):
        # In v5.1 the anchor faced outward, yet part of this folded chain
        # entered the empty cage. A radial anchor alone is insufficient.
        p=c.new_project()
        p['atoms']=[dict(id=i+1,element='C',x=x,y=y,z=z,core=True)
            for i,(x,y,z) in enumerate(itertools.product((-3.,3.),repeat=3))]
        p['atoms'].append(dict(id=9,element='Sn',x=3.,y=0.,z=0.,core=True))
        p['bonds']=[dict(a=9,b=i,order=1) for i in range(1,9)]
        for i,(y,z) in enumerate(itertools.product((-.6,.6),repeat=2),10):
            p['atoms'].append(dict(id=i,element='C',x=5.15,y=y,z=z,core=False))
            p['bonds'].append(dict(a=9,b=i,order=1))
        slot=c.attach_fragment(p,'[*:1]CCCCCC',parent=9)
        assert_exterior(self,p,slot);self.assertGreater(slot['placement']['rejectedPoses'],0)

    def test_no_safe_pose_or_cancellation_restores_slot_and_core_h(self):
        p=c.template(12);c.attach_fragment(p,'[*:1]CC',slot_id='R1');before=c.clone(p)
        with mock.patch.object(CorePlacement,'safe',return_value=False):
            with self.assertRaisesRegex(ValueError,'배치를 찾지 못했습니다'):c.attach_fragment(p,'[*:1]CCC',slot_id='R1')
        self.assertEqual(p,before)
        p=c.template(12);hydroxo=next(a['id'] for a in p['atoms'] if a['element']=='O' and any(c.index_atoms(p)[i]['element']=='H' for i in c.adjacency(p)[a['id']]))
        before=c.clone(p)
        with mock.patch.object(CorePlacement,'safe',return_value=False):
            with self.assertRaises(ValueError):c.attach_fragment(p,'[*:1]CC',parent=hydroxo)
        self.assertEqual(p,before)
        cancel=threading.Event();cancel.set()
        with self.assertRaises(InterruptedError):c.attach_fragment(p,'[*:1]CCC',slot_id='R1',cancel=cancel)
        self.assertEqual(p,before)

    def test_bridges_keep_donor_positions_and_rigid_internal_shape(self):
        for n,sid,smiles in ((6,'L1','CCCCCC(=O)O'),(3,'P1','CCCCCP(CCCCC)(=O)O')):
            p=c.template(n);before=c.clone(p)
            cache={};slot=c.attach_fragment(p,smiles,slot_id=sid,fragment_cache=cache)
            assert_exterior(self,p,slot);self.assertLess(slot['fitRMSD'],.1)
            fragment=next(iter(cache.values()));new=[c.index_atoms(p)[i] for i in slot['ligandIds']]
            x=np.array([c.xyz(a) for a in fragment['atoms']]);y=np.array([c.xyz(a) for a in new])
            np.testing.assert_allclose(np.linalg.norm(x[:,None]-x[None,:],axis=-1),np.linalg.norm(y[:,None]-y[None,:],axis=-1),atol=1.e-10)
            for atom in before['atoms']:np.testing.assert_array_equal(c.xyz(c.index_atoms(p)[atom['id']]),c.xyz(atom))

    def test_no_core_keeps_local_organic_attachment_and_clears_old_record(self):
        f=c.build_fragment('C',mode='coordinate',conformers=1);p=c.new_project()
        p['atoms']=c.clone(f['atoms']);p['bonds']=c.clone(f['bonds'])
        for a in p['atoms']:a['id']+=1
        for b in p['bonds']:b['a']+=1;b['b']+=1
        slot=c.attach_fragment(p,'[*:1]O',parent=1)
        self.assertEqual(slot['placement']['policy'],'local-valence');self.assertIsNone(slot['placement']['coreCenterOfMass'])
        c.validate_project(p)
        p=c.template(12);slot=c.attach_fragment(p,'[*:1]CCC',slot_id='R1')
        slot=c.attach_fragment(p,'',slot_id='R1');self.assertNotIn('placement',slot)

    def test_http_attachment_and_rejected_manual_pose_keep_history_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            ws=w.Workspace(directory)
            try:
                ws.start_job('attach',dict(revision=0,ids=[1],plans=[dict(smiles='[*:1]CCCCCC')]))
                ws.job['thread'].join(20);self.assertEqual(ws.public_job()['status'],'done')
                slot=next(s for s in ws.project['slots'] if s.get('custom'));assert_exterior(self,ws.project,slot)
                before=c.clone(ws.project);radial=np.array(slot['placement']['outwardVector'])
                ws.start_job('attach',dict(revision=1,plans=[dict(slot_id=slot['id'],smiles='[*:1]CC',direction=(-radial).tolist())]))
                ws.job['thread'].join(20);self.assertEqual(ws.public_job()['status'],'error')
                self.assertEqual(ws.revision,1);self.assertEqual(ws.project,before)
                ws.mutate('undo',dict(revision=1));self.assertEqual(len(ws.project['atoms']),38)
            finally:ws.close()


class LegacyCleanupTests(unittest.TestCase):
    def test_successful_cleanup_keeps_the_project_and_core(self):
        p=c.template(12);slot=c.attach_fragment(p,'[*:1]CCC',slot_id='R1',cleanup=False)
        core=c.clone([a for a in p['atoms'] if a.get('core')])
        self.assertIs(c.cleanup_project(p),p)
        self.assertEqual([a for a in p['atoms'] if a.get('core')],core)
        assert_exterior(self,p,slot)

    def test_unsafe_pose_or_cancellation_restores_earlier_rotations(self):
        for cancel_later in (False,True):
            with self.subTest(cancel=cancel_later):
                p=c.template(12);c.attach_fragment(p,'[*:1]CC',slot_id='R1',cleanup=False)
                slot=c.attach_fragment(p,'[*:1]C',slot_id='R2',cleanup=False)
                if not cancel_later:
                    atoms=c.index_atoms(p);origin=c.xyz(atoms[slot['sn'][0]])
                    axis=c.xyz(atoms[slot['anchor']])-origin;rotation=c.rotate_matrix(axis,-axis)
                    for i in slot['ligandIds']:c.set_xyz(atoms[i],(c.xyz(atoms[i])-origin)@rotation.T+origin)
                    guard=CorePlacement(p,slot['sn'],[atoms[i] for i in slot['ligandIds']],p['bonds'])
                    self.assertFalse(guard.safe([c.xyz(atoms[i]) for i in slot['ligandIds']]))
                before=c.clone(p);cancel=threading.Event();changed=[];scores=itertools.count()
                def progress(value):
                    if p!=before:
                        changed.append(True)
                        if cancel_later:cancel.set()
                with mock.patch.object(c.PlacementScorer,'score',side_effect=lambda points:-next(scores)):
                    with self.assertRaises(InterruptedError if cancel_later else ValueError):
                        c.cleanup_project(p,cancel=cancel,progress=progress)
                self.assertTrue(changed)
                self.assertEqual(p,before)


if __name__=='__main__':unittest.main()
