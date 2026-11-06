"""Optional X11 GUI integration checks. These tests skip when DISPLAY is unset."""
import importlib.util,os,tempfile,time,unittest
from pathlib import Path
from unittest import mock
spec=importlib.util.spec_from_file_location('tinoxo_gui',Path(__file__).parents[1]/'TinOxoStudio.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

def descendants(w):
 for child in w.winfo_children():
  yield child
  yield from descendants(child)

@unittest.skipUnless(os.environ.get('DISPLAY'),'requires a working X11 DISPLAY')
class GuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  t.import_tk();cls.root=t.tk.Tk();cls.tmp=tempfile.TemporaryDirectory();cls.app=t.NativeApp(cls.root,config_dir=cls.tmp.name,recover_prompt=False);cls.root.update()
 @classmethod
 def tearDownClass(cls):
  cls.root.destroy();cls.tmp.cleanup()
 def setUp(self):
  self.app.project=t.template(12);self.app.selection=[];self.app.path=None;self.app.history=[];self.app.future=[];self.app.refresh();self.root.update();self.errors=[]
  self.root.report_callback_exception=lambda ty,v,tb:self.errors.append(str(v))
  self.error_patch=mock.patch.object(t.messagebox,'showerror',side_effect=lambda *a,**kw:self.errors.append(str(a)))
  self.error_patch.start()
 def tearDown(self):
  for w in self.root.winfo_children():
   if isinstance(w,t.tk.Toplevel):w.destroy()
  self.error_patch.stop();self.assertFalse(self.errors,self.errors)
 def test_all_dialogs(self):
  self.app.select([1,2,3])
  for method in ['library_dialog','attach_dialog','slots_dialog','measure_dialog','bond_dialog','resonance_dialog','contact_dialog','gaussian_dialog','appearance_dialog','bank_dialog','export_dialog','help_dialog']:
   old=set(self.root.winfo_children());getattr(self.app,method)();self.root.update()
   wins=[w for w in self.root.winfo_children() if w not in old and isinstance(w,t.tk.Toplevel)];self.assertEqual(len(wins),1,method)
   for w in wins:w.destroy()
 def test_common_attachment_worker_undo_and_save(self):
  self.app.select([1,2]);self.app.attach_dialog();self.root.update();win=[w for w in self.root.winfo_children() if isinstance(w,t.tk.Toplevel)][-1]
  entry=next(w for w in descendants(win) if isinstance(w,t.ttk.Entry) and not isinstance(w,t.ttk.Combobox) and w.grid_info().get('row')==1 and w.grid_info().get('column')==1)
  entry.insert(0,'[*:1]C');button=next(w for w in descendants(win) if isinstance(w,t.ttk.Button) and w.cget('text')=='모두 적용');button.invoke()
  self.root.update();picker=next(w.atom_picker for w in self.root.winfo_children() if hasattr(w,'atom_picker'));picker.confirm()
  deadline=time.monotonic()+20
  while self.app.busy and time.monotonic()<deadline:self.root.update();time.sleep(.01)
  self.root.update();self.assertFalse(self.app.busy);self.assertEqual(len(self.app.project['atoms']),46)
  self.app.undo();self.assertEqual(len(self.app.project['atoms']),38);self.app.redo();self.assertEqual(len(self.app.project['atoms']),46)
  self.app.path=str(Path(self.tmp.name)/'saved.tinoxo.json');self.app.save();p,b,s=t.read_structure(self.app.path);self.assertEqual(len(p['atoms']),46)
 def test_gaussian_ui_preview(self):
  self.app.gaussian_dialog();self.root.update();win=[w for w in self.root.winfo_children() if isinstance(w,t.tk.Toplevel)][-1]
  button=next(w for w in descendants(win) if isinstance(w,t.ttk.Button) and w.cget('text')=='입력 생성 / 갱신');button.invoke();self.root.update()
  texts=[w.get('1.0','end') for w in descendants(win) if isinstance(w,t.tk.Text)];self.assertTrue(any('Sn 0\nDef2\n' in s and '%NProcShared=8' in s for s in texts))
 def test_custom_smiles_saved(self):
  self.app.library_dialog();self.root.update();win=[w for w in self.root.winfo_children() if isinstance(w,t.tk.Toplevel)][-1]
  entries=[w for w in descendants(win) if isinstance(w,t.ttk.Entry) and not isinstance(w,t.ttk.Combobox)]
  entries[1].insert(0,'testethyl');entries[2].insert(0,'[*:1]CC')
  next(w for w in descendants(win) if isinstance(w,t.ttk.Button) and w.cget('text')=='내 SMILES로 추가 / 갱신').invoke();self.root.update()
  self.assertTrue(any(v['name']=='testethyl' for v in self.app.settings['favorites']));self.assertTrue(self.app.config_path.exists())
 def test_global_sn_c_length(self):
  p=t.template(12);t.attach_fragment(p,'[*:1]C',slot_id='R1',cleanup=False);self.app.project=p;self.app.refresh();self.app.snc_var.set('2.25');self.app.change_sn_c()
  s=next(s for s in self.app.project['slots'] if s['id']=='R1');a=t.index_atoms(self.app.project);self.assertAlmostEqual(float(t.np.linalg.norm(t.xyz(a[s['anchor']])-t.xyz(a[1]))),2.25,places=7)

if __name__=='__main__':unittest.main()
