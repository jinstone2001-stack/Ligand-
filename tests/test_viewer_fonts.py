"""Regressions for Unicode fonts, orthographic camera and retained rendering."""
import importlib.util,json,tempfile,unittest,os
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('tinoxo_viewer',Path(__file__).parents[1]/'TinOxoStudio.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

class FontEncodingTests(unittest.TestCase):
 def test_requested_font_choices_are_closed(self):
  self.assertEqual(t.KOREAN_FONT_CHOICES,('맑은고딕','굴림'));self.assertEqual(t.ENGLISH_FONT_CHOICES,('Arial','Calibri'))
 def test_resolve_exact_requested_families(self):
  settings={'korean_font':'굴림','english_font':'Calibri'}
  r=t.resolve_font_choices(settings,['Malgun Gothic','Gulim','Arial','Calibri','Unrelated Symbol Font'])
  self.assertEqual((r['korean'],r['english']),('Gulim','Calibri'));self.assertEqual(r['notes'],[])
 def test_missing_ms_fonts_use_explicit_hangul_fallback(self):
  r=t.resolve_font_choices({'korean_font':'맑은고딕','english_font':'Arial'},['NanumGothic','Carlito','Symbol'])
  self.assertEqual(r['korean'],'NanumGothic');self.assertEqual(r['english'],'Carlito');self.assertEqual(len(r['notes']),2)
 def test_legacy_unknown_font_migration(self):
  s={'font_family':'Some CJK Symbol Font','font_size':'bad'};t.normalize_font_preferences(s)
  self.assertEqual((s['korean_font'],s['english_font'],s['font_size']),('맑은고딕','Arial',11))
 def test_utf8_bom_and_cp949_load_losslessly(self):
  raw=json.dumps({'name':'주석 옥소 구조','korean_font':'굴림'},ensure_ascii=False)
  with tempfile.TemporaryDirectory() as d:
   for encoding in ('utf-8','utf-8-sig','cp949'):
    path=Path(d)/'settings.json';path.write_bytes(raw.encode(encoding))
    self.assertEqual(json.loads(t.read_unicode_text(path))['name'],'주석 옥소 구조')
    t.atomic_write(path,t.read_unicode_text(path));self.assertEqual(path.read_bytes().decode('utf-8'),raw)
 def test_invalid_binary_text_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'bad.json';path.write_bytes(b'\xff\xff\xff')
   with self.assertRaises(ValueError):t.read_unicode_text(path)
 def test_bundled_korean_font_has_hangul_glyphs(self):
  font_path=Path(__file__).parents[1]/'fonts/NanumGothic-Regular.ttf'
  font=t.ImageFont.truetype(str(font_path),28)
  mask=font.getmask('한글');missing=font.getmask('\uffff\uffff')
  self.assertTrue(mask.getbbox());self.assertNotEqual((mask.size,bytes(mask)),(missing.size,bytes(missing)))
 def test_fontconfig_export_face_and_png(self):
  t.register_local_fonts();path=t.font_file_for_family('Carlito')
  if not path:self.skipTest('fontconfig is unavailable')
  self.assertTrue(Path(path).is_file())
  p=t.template(3);prims,_=t.scene_primitives(p,[1],t.clone(t.DEFAULTS),400,300)
  image=t.scene_png(prims,400,300,'#111111',font_family='Carlito');self.assertEqual(image.size,(800,600))

class CameraTests(unittest.TestCase):
 def setUp(self):
  self.p=t.template(12);self.settings=t.clone(t.DEFAULTS)
  # Deliberately anisotropic to detect the old orientation-dependent fit bug.
  for a in self.p['atoms']:a['x']*=3.
 def test_rotating_preserves_pixel_scale_and_atom_size(self):
  _,base=t.scene_primitives(self.p,[],self.settings,800,600)
  for angle in np.linspace(0,2*np.pi,23):
   rot=t.axis_rotation((.2,1,.5),angle);prims,projected=t.scene_primitives(self.p,[],self.settings,800,600,rotation=rot)
   for aid in base:self.assertAlmostEqual(base[aid][3],projected[aid][3],places=9)
 def test_pair_projection_uses_same_scale_each_orientation(self):
  center,scale=t.camera_frame(self.p,800,600);aid=1;bid=2;atoms=t.index_atoms(self.p)
  for angle in (0,.4,1.7):
   rot=t.axis_rotation((1,1,0),angle);_,q=t.scene_primitives(self.p,[],self.settings,800,600,rotation=rot)
   delta=(t.xyz(atoms[aid])-t.xyz(atoms[bid]))@rot.T
   np.testing.assert_allclose(np.array(q[aid][:2])-q[bid][:2],delta[:2]*[scale,-scale],atol=1e-9)
 def test_zoom_is_explicit_linear_multiplier(self):
  _,a=t.scene_primitives(self.p,[],self.settings,800,600,zoom=1)
  _,b=t.scene_primitives(self.p,[],self.settings,800,600,zoom=2)
  for aid in a:self.assertAlmostEqual(b[aid][3],a[aid][3]*2,places=8)
 def test_visibility_does_not_refit_or_recenter(self):
  _,a=t.scene_primitives(self.p,[],self.settings,800,600,show_h=True)
  _,b=t.scene_primitives(self.p,[],self.settings,800,600,show_h=False)
  for aid in b:np.testing.assert_allclose(a[aid],b[aid],atol=1e-9)
 def test_fast_scene_preserves_all_positions_and_selection(self):
  center,scale=t.camera_frame(self.p,800,600);scene=t.PreparedScene(self.p,[1,2],self.settings,labels=True)
  normal,a=scene.project_frame(800,600,np.eye(3),center,scale)
  fast,b=scene.project_frame(800,600,np.eye(3),center,scale,interactive=True)
  self.assertEqual(a,b);self.assertLess(len(fast),len(normal))
  self.assertEqual(sum(p['key'][-1]=='selection' for p in fast),2)
  self.assertFalse(any(p['key'][-1]=='highlight' for p in fast))
 def test_no_coordinate_or_bond_mutation_during_render(self):
  before=json.dumps(self.p,sort_keys=True);scene=t.PreparedScene(self.p,[],self.settings)
  center,scale=t.camera_frame(self.p,800,600)
  for angle in (0,.5,1.5):scene.project_frame(800,600,t.axis_rotation((1,1,1),angle),center,scale)
  self.assertEqual(before,json.dumps(self.p,sort_keys=True))

@unittest.skipUnless(os.environ.get('DISPLAY'),'requires X11 DISPLAY')
class ViewerGuiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  t.import_tk();cls.root=t.tk.Tk();cls.tmp=tempfile.TemporaryDirectory();cls.app=t.NativeApp(cls.root,config_dir=cls.tmp.name,recover_prompt=False);cls.root.update()
 @classmethod
 def tearDownClass(cls):cls.root.destroy();cls.tmp.cleanup()
 def setUp(self):
  self.app.project=t.template(12);self.app.selection=[];self.app.view.draw();self.app.view.fit();self.root.update();self.app.view.render_now()
 def tearDown(self):
  for w in self.root.winfo_children():
   if isinstance(w,t.tk.Toplevel):w.destroy()
 def test_retained_items_are_not_recreated_on_camera_rotation(self):
  v=self.app.view;v.dragging=True;v.render_now();v._render_frame();created=v.renderer.created;scene=v.scene
  for a in np.linspace(0,2,30):v.rotation=t.axis_rotation((1,1,0),a);v._render_frame()
  self.assertIs(v.scene,scene);self.assertEqual(v.renderer.created,created)
  v.dragging=False;v.render_now()
 def test_motion_requests_coalesce_and_release_restores_quality(self):
  from types import SimpleNamespace
  v=self.app.view;v.press(SimpleNamespace(x=100,y=100,state=0));start=v.render_stats['frames']
  for i in range(80):v.drag(SimpleNamespace(x=110+i,y=100+i,state=0))
  self.assertEqual(v.render_stats['frames'],start);self.assertIsNotNone(v.pending)
  v._render_frame();fast=len(v.primitives);v.release(SimpleNamespace(x=189,y=179,state=0));self.root.update()
  self.assertFalse(v.dragging);self.assertGreater(len(v.primitives),fast)
 def test_camera_scale_survives_resize_visibility_and_pan(self):
  v=self.app.view;base=v.pixels_per_angstrom;v.rotation=t.axis_rotation((0,1,0),1.2);v.pan[:]=[15,30];v._render_frame()
  self.app.show_h.set(False);v.draw();self.root.geometry('1300x760');self.root.update();v.render_now()
  self.assertEqual(v.pixels_per_angstrom,base)
  zoom=v.zoom;v.wheel(1.12);v.render_now();self.assertAlmostEqual(v.zoom,zoom*1.12)
  v.fit();self.root.update();self.assertEqual(v.zoom,1.)
 def test_font_menu_only_requested_fonts_and_preview_cancel(self):
  self.app.appearance_dialog();self.root.update()
  win=next(w for w in self.root.winfo_children() if isinstance(w,t.tk.Toplevel))
  def children(w):
   for c in w.winfo_children():yield c;yield from children(c)
  combos=[w for w in children(win) if isinstance(w,t.ttk.Combobox)]
  self.assertTrue(any(tuple(w.cget('values'))==t.KOREAN_FONT_CHOICES and str(w.cget('state'))=='readonly' for w in combos))
  self.assertTrue(any(tuple(w.cget('values'))==t.ENGLISH_FONT_CHOICES for w in combos))
 def test_bilingual_text_tags_and_english_viewer_labels(self):
  box=self.app.log_text;box.insert('end','한글 English 한글\n');self.root.update();self.app.fonts.style_text(box)
  self.assertTrue(box.tag_ranges('tinoxo_hangul'))
  self.assertEqual(box.cget('font'),str(self.app.fonts.named['english']))
  resolved=self.app.fonts.resolved;self.assertIn(resolved['korean'],t.tkfont.families(self.root))

if __name__=='__main__':unittest.main()
