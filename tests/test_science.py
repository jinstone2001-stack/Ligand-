"""Scientific regressions. Run from package root: python -m unittest discover -s tests -v"""
import importlib.util,json,tempfile,threading,unittest
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('tinoxo',Path(__file__).parents[1]/'TinOxoStudio.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

class CoreTests(unittest.TestCase):
 def test_sn3_is_six_atom_ring(self):
  p=t.template(3);self.assertEqual(t.Counter(a['element'] for a in p['atoms']),{'Sn':3,'O':3})
  self.assertEqual(len(p['bonds']),6);self.assertTrue(all(len(ns)==2 for ns in t.adjacency(p).values()))
  self.assertIsNone(p['metadata']['totalCharge'])
 def test_literature_coordinates_unchanged(self):
  for n in [6,12]:
   p=t.template(n);ref=t.DATA['templates'][str(n)];self.assertEqual(p['atoms'],ref['atoms']);self.assertEqual(len(p['bonds']),len(ref['bonds']))
 def test_hydroxo_idempotent_and_direction(self):
  p=t.template(12);old=t.index_atoms(p);ids,removed=t.prepare_hydroxo(p)
  self.assertEqual(len(ids),6);self.assertEqual(len(removed),6)
  for oid in ids:
   h=next(i for i in t.adjacency(t.template(12))[oid] if old[i]['element']=='H')
   expected=t.unit(t.xyz(old[h])-t.xyz(old[oid]));np.testing.assert_allclose(p['metadata']['hydroxoDirections'][str(oid)],expected)
  ids2,removed2=t.prepare_hydroxo(p);self.assertEqual(ids2,ids);self.assertEqual(removed2,[])
 def test_vesta_default_colors(self):
  self.assertEqual(t.DEFAULT_ELEMENT_COLORS['Sn'],'#9b8fba');self.assertEqual(t.DEFAULT_ELEMENT_COLORS['O'],'#ff0300');self.assertEqual(len(t.DEFAULT_ELEMENT_COLORS),118)

class ChemistryTests(unittest.TestCase):
 def test_methyl_attachment_graph_and_core_fixed(self):
  p=t.template(12);before={a['id']:t.xyz(a).copy() for a in p['atoms']};s=t.attach_fragment(p,'[*:1]C',slot_id='R1',cleanup=False)
  for aid,pos in before.items():np.testing.assert_allclose(t.xyz(t.index_atoms(p)[aid]),pos,atol=1e-12)
  self.assertEqual(len(s['ligandIds']),4);a=t.index_atoms(p);self.assertAlmostEqual(float(np.linalg.norm(t.xyz(a[s['anchor']])-t.xyz(a[1]))),2.15,places=7)
 def test_coordinate_ammonia_keeps_three_h(self):
  p=t.template(12);s=t.attach_fragment(p,'N',parent=1,mode='coordinate',cleanup=False)
  self.assertEqual(sum(a['element']=='H' for a in p['atoms'] if a.get('slot')==s['id']),3)
  self.assertEqual(next(b for b in p['bonds'] if b['a']==s['anchor'] and b['b']==1)['kind'],'coordinate')
 def test_organic_parent_h_replacement(self):
  p=t.template(12);s=t.attach_fragment(p,'[*:1]C',slot_id='R1',cleanup=False);a=t.index_atoms(p);root=s['anchor']
  count=lambda:sum(t.index_atoms(p)[i]['element']=='H' for i in t.adjacency(p)[root])
  self.assertEqual(count(),3);t.attach_fragment(p,'[*:1]O',parent=root,cleanup=False);self.assertEqual(count(),2)
 def test_acetate_resonance_geometry_both_forcefields(self):
  for ff in ['MMFF94','UFF']:
   f=t.build_fragment('CC(=O)[O-]','L',ff_choice=ff,conformers=1);a=t.index_atoms(f);center=f['center'];d=[float(np.linalg.norm(t.xyz(a[center])-t.xyz(a[i]))) for i in f['donors']]
   self.assertGreaterEqual(f['resonance']['forms'],2);self.assertLess(abs(d[0]-d[1]),.008);self.assertTrue(all(1.23<v<1.30 for v in d))
   if ff=='UFF':self.assertTrue(f['resonanceRestraints'])
 def test_aromatic_geometry_planar(self):
  f=t.build_fragment('[*:1]c1ccccc1','R',conformers=1);r=np.array([t.xyz(a) for a in f['atoms'] if a['element']=='C']);_,s,_=np.linalg.svd(r-r.mean(0));self.assertLess(s[-1],.02)
  self.assertEqual(sum(b['order']==1.5 for b in f['bonds']),6)
 def test_l_and_p_bridge_preserve_organic_geometry(self):
  for n,sid,smiles in [(6,'L1','CC(=O)[O-]'),(3,'P1','CP(C)(=O)[O-]')]:
   p=t.template(n);before={a['id']:t.xyz(a).copy() for a in p['atoms']};s=t.attach_fragment(p,smiles,slot_id=sid,cleanup=False)
   self.assertEqual(len(s['donorIds']),2)
   for aid,r in before.items():np.testing.assert_allclose(t.xyz(t.index_atoms(p)[aid]),r,atol=1e-12)
   self.assertTrue(np.isfinite(s['fitRMSD']))
 def test_single_atom_halogen(self):
  for x in ['F','Cl','Br','I']:
   f=t.build_fragment('[*:1]'+x,ff_choice='MMFF94',conformers=1);self.assertEqual(len(f['atoms']),1)
 def test_all_builtin_smiles_parse(self):
  for _,name,smiles,_ in t.BUILTIN_LIGANDS:self.assertIsNotNone(t.Chem.MolFromSmiles(smiles),name)
 def test_fixed_core_optimization(self):
  p=t.template(12);s=t.attach_fragment(p,'[*:1]CCC',slot_id='R1',cleanup=False);a=t.index_atoms(p);core={i:t.xyz(v).copy() for i,v in a.items() if v.get('core')}
  out,logs=t.optimize_project(p,choice='MMFF94');self.assertTrue(logs);self.assertLessEqual(logs[0]['after_kcal_mol'],logs[0]['before_kcal_mol']+1e-7)
  for i,r in core.items():np.testing.assert_allclose(t.xyz(t.index_atoms(out)[i]),r,atol=1e-12)
 def test_no_silent_unsupported_forcefield(self):
  with self.assertRaises(ValueError):t.make_forcefield(t.Chem.AddHs(t.Chem.MolFromSmiles('[Xe]')),'MMFF94')
 def test_cancellation(self):
  ev=threading.Event();ev.set()
  with self.assertRaises(InterruptedError):t.build_fragment('[*:1]CCCCCCCC',cancel=ev)
 def test_nested_ligand_clear(self):
  p=t.template(12);s=t.attach_fragment(p,'[*:1]C',slot_id='R1',cleanup=False);u=t.attach_fragment(p,'[*:1]O',parent=s['anchor'],cleanup=False);child=set(u['ligandIds']);t.clear_slot(p,'R1');self.assertFalse(child&set(t.index_atoms(p)));t.validate_project(p)

class GeometryBondTests(unittest.TestCase):
 def test_distances_angles(self):
  p=t.new_project();p['atoms']=[dict(id=i+1,element='C',x=r[0],y=r[1],z=r[2]) for i,r in enumerate([[1,0,0],[0,0,0],[0,1,0],[0,1,1]])]
  self.assertAlmostEqual(t.measurement(p,[1,2])[1],1.);self.assertAlmostEqual(t.measurement(p,[1,2,3])[1],90.);self.assertAlmostEqual(abs(t.measurement(p,[1,2,3,4])[1]),90.)
 def test_bonds_not_removed_by_distance(self):
  p=t.template(12);count=len(p['bonds']);p['atoms'][0]['x']+=10;t.bond_audit(p);self.assertEqual(len(p['bonds']),count)
 def test_long_sn_o_donor_candidate(self):
  p=t.new_project();p['atoms']=[dict(id=1,element='Sn',x=0.,y=0.,z=0.),dict(id=2,element='O',x=2.75,y=0.,z=0.)]
  rows=t.bond_audit(p);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'coordinate')
 def test_radii_are_element_specific(self):
  self.assertAlmostEqual(t.radius('C','vdw'),1.7);self.assertNotEqual(t.radius('O','vdw'),t.radius('Sn','vdw'))
 def test_xyz_rdkit_bond_orders(self):
  f=t.build_fragment('CC(=O)C',mode='coordinate',conformers=1);p=t.new_project();p['atoms']=t.clone(f['atoms'])
  for i,a in enumerate(p['atoms']):a['id']=i+1
  t.infer_xyz_bonds(p,charge=0)
  self.assertIn('RDKit xyz2mol',p['metadata']['bondInference']);self.assertTrue(any(b['order']==2 for b in p['bonds']))

class GaussianIOTests(unittest.TestCase):
 def test_sn_genecp_and_final_blank(self):
  p=t.template(3);s,r=t.build_gaussian(p,t.gaussian_defaults(p));self.assertIn('/GenECP',s);self.assertIn('Sn 0\nDef2\n',s);self.assertTrue(s.endswith('\n\n'));self.assertEqual(r['electrons'],174)
 def test_parity_rejected(self):
  p=t.template(3);o=t.gaussian_defaults(p);o.update(charge=1,multiplicity=1)
  with self.assertRaises(ValueError):t.build_gaussian(p,o)
 def test_incompatible_sn_basis_rejected(self):
  p=t.template(3);o=t.gaussian_defaults(p);o.update(basis_mode='single',basis='6-31G(d)')
  with self.assertRaises(ValueError):t.build_gaussian(p,o)
 def test_no_double_dispersion(self):
  p=t.template(3);o=t.gaussian_defaults(p);o.update(method='wB97XD',dispersion='GD3BJ')
  with self.assertRaises(ValueError):t.build_gaussian(p,o)
 def test_all_job_builders(self):
  p=t.template(3)
  for job in t.GAUSSIAN_JOBS:
   o=t.gaussian_defaults(p);o['job']=job;s,r=t.build_gaussian(p,o);self.assertIn('0 1\n',s)
 def test_mixed_basis_coverage(self):
  p=t.template(12);o=t.gaussian_defaults(p);o['basis_by_element']={'Sn':'SDD','O':'6-31G(d)','H':'6-31G(d)'};s,r=t.build_gaussian(p,o);self.assertIn('Sn 0\nSDD',s);self.assertEqual(r['ecp'],{'SDD':['Sn']})
 def test_roundtrip_json_and_html(self):
  p=t.template(3);bank={'version':2,'entries':[],'trash':[],'activeId':None};settings=t.clone(t.DEFAULTS)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'project.json';t.atomic_write(path,json.dumps({'project':p,'bank':bank,'settings':settings}));out,_,_=t.read_structure(path);self.assertEqual(out,p)
   path=Path(d)/'project.html';t.atomic_write(path,t.portable_html(p,bank,settings));out,b,s=t.read_structure(path);self.assertEqual(out,p);self.assertEqual(s,settings)
 def test_sdf_coordinate_bond_preserved(self):
  p=t.template(12);s=t.attach_fragment(p,'O',parent=1,mode='coordinate',cleanup=False)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.sdf';t.atomic_write(path,t.export_sdf(p));out,_,_=t.read_structure(path);self.assertEqual(len(out['bonds']),len(p['bonds']));self.assertTrue(any(b['kind']=='coordinate' for b in out['bonds']))
 def test_atomic_write_path(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'sub'/'input.gjf';t.atomic_write(path,'x\n');self.assertEqual(path.read_text(),'x\n')

if __name__=='__main__':unittest.main()
