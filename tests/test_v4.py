"""Selected attachment graphs, popup transactions and shared Gaussian settings."""
import importlib.util,json,os,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import numpy as np

spec=importlib.util.spec_from_file_location('tinoxo_v4',Path(__file__).parents[1]/'TinOxoStudio.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def descendants(widget):
 for child in widget.winfo_children():
  yield child
  yield from descendants(child)

class SelectedAttachmentTests(unittest.TestCase):
 def test_nonfirst_nitrogen_coordinate_keeps_hydrogens(self):
  p=t.template(12);s=t.attach_fragment(p,'CCN',parent=1,mode='coordinate',attachment_index=2,cleanup=False)
  atoms=t.index_atoms(p);self.assertEqual(atoms[s['anchor']]['element'],'N')
  self.assertEqual(s['attachmentIndex'],2)
  self.assertEqual(sum(atoms[i]['element']=='H' for i in t.adjacency(p)[s['anchor']]),2)
 def test_nonfirst_oxygen_covalent_loses_one_h(self):
  f=t.build_fragment('CCO',attachment_index=2,conformers=1)
  self.assertEqual(f['anchor'],2);self.assertEqual(t.Counter(a['element'] for a in f['atoms']),{'C':2,'H':5,'O':1})
  self.assertEqual(len([b for b in f['bonds'] if 2 in (b['a'],b['b'])]),1)
 def test_nonfirst_carbon_is_real_sn_c_anchor(self):
  p=t.template(12);s=t.attach_fragment(p,'CCO',slot_id='R1',attachment_index=1,cleanup=False)
  atoms=t.index_atoms(p);root=s['anchor'];self.assertEqual(atoms[root]['element'],'C')
  neighbors=[atoms[i]['element'] for i in t.adjacency(p)[root]]
  self.assertCountEqual(neighbors,['C','O','H','Sn'])
 def test_moving_dummy_attachment_caps_previous_position(self):
  f=t.build_fragment('[*:1]CCO',attachment_index=3,conformers=1);atoms=t.index_atoms(f)
  self.assertEqual(f['anchor'],3);self.assertEqual(atoms[0]['element'],'H')
  self.assertEqual(t.Counter(a['element'] for a in f['atoms']),{'C':2,'H':5,'O':1})
 def test_coordinate_dummy_preserves_capping_h(self):
  f=t.build_fragment('[*:1]CN',mode='coordinate',attachment_index=2,conformers=1)
  self.assertEqual(t.Counter(a['element'] for a in f['atoms']),{'C':1,'N':1,'H':5})
 def test_aromatic_nitrogen_and_graph_preserved(self):
  f=t.build_fragment('c1ccncc1',mode='coordinate',attachment_index=3,conformers=1)
  self.assertEqual(t.index_atoms(f)[f['anchor']]['element'],'N');self.assertEqual(sum(b['order']==1.5 for b in f['bonds']),6)
 def test_invalid_indices_and_dummy_rejected(self):
  for index in (-1,99,True,'2',0):
   with self.subTest(index=index),self.assertRaises(ValueError):t.build_fragment('[*:1]CCO',attachment_index=index,conformers=1)
 def test_saturated_oxygen_cannot_add_covalent_bond(self):
  with self.assertRaises(ValueError):t.build_fragment('COC',attachment_index=1,conformers=1)
  self.assertIn(1,t.ligand_attachment_info('COC',mode='coordinate')['candidates'])
 def test_bridge_selected_oxygen_sets_first_host(self):
  p=t.template(6);s=t.attach_fragment(p,'CC(=O)[O-]',slot_id='L1',attachment_index=3,cleanup=False)
  self.assertEqual(s['attachmentIndex'],3);self.assertEqual(s['anchor'],s['donorIds'][0])
  self.assertTrue(any(b['a']==s['donorIds'][0] and b['b']==s['sn'][0] for b in p['bonds']))
 def test_multifunctional_bridge_group_selected_explicitly(self):
  f=t.build_fragment('[O-]C(=O)CCC(=O)[O-]','L',attachment_index=7,conformers=1)
  self.assertEqual(f['center'],5);self.assertEqual(f['donors'],[7,6])
 def test_original_stereochemical_graph_kept(self):
  smiles='C[C@H](F)CO';mol=t.Chem.MolFromSmiles(smiles)
  f=t.build_fragment(smiles,mode='coordinate',attachment_index=4,conformers=1)
  for atom in mol.GetAtoms():
   self.assertEqual(t.index_atoms(f)[atom.GetIdx()]['chirality'],int(atom.GetChiralTag()))
 def test_attachment_index_roundtrip_reedit_and_clear(self):
  p=t.template(12);t.attach_fragment(p,'CCO',slot_id='R1',attachment_index=1,cleanup=False)
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'selected.json';t.atomic_write(path,json.dumps({'project':p}));out,_,_=t.read_structure(path)
  s=t.attach_fragment(out,'CCO',slot_id='R1',cleanup=False)
  self.assertEqual(s['attachmentIndex'],1);t.clear_slot(out,'R1')
  self.assertNotIn('attachmentIndex',next(s for s in out['slots'] if s['id']=='R1'))

@unittest.skipUnless(os.environ.get('DISPLAY'),'requires X11 DISPLAY')
class V4GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  t.import_tk();cls.root=t.tk.Tk();cls.tmp=tempfile.TemporaryDirectory();cls.app=t.NativeApp(cls.root,config_dir=cls.tmp.name,recover_prompt=False);cls.root.update()
 @classmethod
 def tearDownClass(cls):cls.root.destroy();cls.tmp.cleanup()
 def setUp(self):
  self.app.project=t.template(12);self.app.selection=[];self.app.history=[];self.app.future=[];self.app.refresh();self.root.update();self.errors=[]
  self.root.report_callback_exception=lambda ty,value,tb:self.errors.append(str(value))
  self.patcher=mock.patch.object(t.messagebox,'showerror',side_effect=lambda *args,**kw:self.errors.append(str(args)));self.patcher.start()
 def tearDown(self):
  for widget in self.root.winfo_children():
   if isinstance(widget,t.tk.Toplevel):widget.destroy()
  self.patcher.stop();self.assertFalse(self.errors,self.errors)
 def dialog(self):return [w for w in self.root.winfo_children() if isinstance(w,t.tk.Toplevel)][-1]
 def button(self,win,label):return next(w for w in descendants(win) if isinstance(w,t.ttk.Button) and w.cget('text')==label)
 def test_popup_click_maps_original_index_and_cancel_keeps_project(self):
  before=json.dumps(self.app.project,sort_keys=True);selected=[]
  picker=t.LigandAtomDialog(self.app,self.root,'CCO','A','coordinate',selected.append)
  self.root.update();picker.draw();x,y=picker.points[2];picker.click(SimpleNamespace(x=x,y=y))
  self.assertEqual(picker.selected,2);self.assertGreater(picker.image.width(),100)
  picker.win.destroy();self.assertEqual(selected,[]);self.assertEqual(before,json.dumps(self.app.project,sort_keys=True))
 def test_selected_atom_applies_to_all_hosts_and_undo(self):
  self.app.select([1,2]);self.app.attach_dialog(preset=('CCN','coordinate'));self.root.update()
  picker=next(w.atom_picker for w in self.root.winfo_children() if hasattr(w,'atom_picker'))
  picker.draw();x,y=picker.points[2];picker.click(SimpleNamespace(x=x,y=y));picker.confirm()
  self.button(self.dialog(),'모두 적용').invoke()
  deadline=time.monotonic()+20
  while self.app.busy and time.monotonic()<deadline:self.root.update();time.sleep(.01)
  self.root.update();self.assertFalse(self.app.busy)
  slots=[s for s in self.app.project['slots'] if s.get('custom')];self.assertEqual(len(slots),2)
  self.assertTrue(all(t.index_atoms(self.app.project)[s['anchor']]['element']=='N' for s in slots))
  self.app.undo();self.assertEqual(len(self.app.project['atoms']),38)
 def test_gaussian_tabs_share_method_and_compact_controls(self):
  self.app.gaussian_dialog();self.root.update();win=self.dialog();ui=win.gaussian_ui
  self.assertEqual([ui['notebook'].tab(i,'text') for i in range(3)],['간편 설정','커스텀 설정','입력 미리보기'])
  ui['variables']['method'].set('wB97XD');ui['variables']['basis'].set('Def2TZVP')
  quick_combos=[w for w in descendants(ui['quick']) if isinstance(w,t.ttk.Combobox)]
  self.assertTrue(all(int(w.cget('width'))==16 for w in quick_combos))
  self.root.geometry('1320x950');win.geometry('1250x850');self.root.update()
  self.assertTrue(all(w.winfo_width()<400 for w in quick_combos))
  text=ui['generate']();self.assertIn('wB97XD/GenECP',text);self.assertIn('Def2TZVP',text)
 def test_custom_element_basis_and_quick_reset(self):
  self.app.gaussian_dialog();self.root.update();win=self.dialog();ui=win.gaussian_ui
  ui['basis_tree'].selection_set('Sn');ui['basis_value'].set('SDD');ui['ecp_value'].set('SDD')
  self.button(win,'선택 원소 적용').invoke();self.assertEqual(ui['basis_maps']['Sn'],'SDD')
  text=ui['generate']();self.assertIn('Sn 0\nSDD',text)
  self.button(win,'이 기저함수를 모든 원소에 간편 적용').invoke()
  self.assertEqual(ui['basis_maps'],{});self.assertEqual(ui['variables']['basis_mode'].get(),'mixed')
  self.assertIn('Sn 0\nDef2',ui['generate']())
 def test_custom_genecp_block_is_used_from_shared_settings(self):
  self.app.gaussian_dialog();self.root.update();ui=self.dialog().gaussian_ui
  ui['variables']['method'].set('PBE1PBE');ui['variables']['basis_mode'].set('custom')
  ui['custom_text'].insert('1.0','H O Sn 0\nDef2SVP\n****\n\nSn 0\nDef2\n')
  self.assertIn('PBE1PBE/GenECP',ui['generate']());self.assertEqual(ui['gather']()['basis_mode'],'custom')
 def test_text_rendering_and_large_font_action_layout(self):
  self.assertTrue(t.TEXT_RENDERING['configured']);self.assertFalse(t.TEXT_RENDERING['errors'])
  self.assertGreaterEqual(self.app.fonts.named['small'].cget('size'),10)
  before=self.app.settings['font_size'];self.app.settings['font_size']=16;self.app.apply_theme()
  try:
   self.app.gaussian_dialog();win=self.dialog();win.geometry('1180x850');self.root.update()
   for label in ['입력 생성 / 갱신','HPC 경로에 .gjf / .com 저장','닫기']:
    button=self.button(win,label);self.assertGreaterEqual(button.winfo_height(),30)
    self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),win.winfo_rooty()+win.winfo_height())
   self.assertGreaterEqual(int(self.app.style.lookup('Treeview','rowheight')),self.app.fonts.named['ui'].metrics('linespace')+8)
  finally:self.app.settings['font_size']=before;self.app.apply_theme()

if __name__=='__main__':unittest.main()
