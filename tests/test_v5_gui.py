"""Native v5 launch, clipboard and computation flows on a real X11 display."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import numpy as np
import TinOxoStudio as c
import TinOxoWeb as w


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class LauncherTests(unittest.TestCase):
    def test_default_without_display_reports_x11_error_without_browser(self):
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,str(Path(c.__file__).resolve()),'--fresh','--config-dir',d],
                env={**os.environ,'DISPLAY':''},capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,2);self.assertIn('X11 GUI를 열 수 없습니다',p.stderr)
        self.assertNotIn('http://',p.stdout);self.assertNotIn('접속 포트',p.stdout)
    def test_web_flags_require_explicit_opt_in(self):
        with mock.patch.object(w,'run') as web:
            with self.assertRaises(SystemExit) as error:c.main(['--port','8765'])
        self.assertEqual(error.exception.code,2);web.assert_not_called()


@unittest.skipUnless(os.environ.get('DISPLAY'),'requires X11 DISPLAY')
class NativeV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        c.import_tk();cls.root=c.tk.Tk();cls.tmp=tempfile.TemporaryDirectory()
        cls.app=c.NativeApp(cls.root,config_dir=cls.tmp.name,recover_prompt=False);cls.root.update()
    @classmethod
    def tearDownClass(cls):cls.root.destroy();cls.tmp.cleanup()
    def setUp(self):
        self.errors=[];self.root.report_callback_exception=lambda ty,value,tb:self.errors.append(str(value))
        self.error_patch=mock.patch.object(c.messagebox,'showerror',side_effect=lambda *args,**kw:self.errors.append(str(args)));self.error_patch.start()
        self.app.project=c.template(12);self.app.selection=[];self.app.history=[];self.app.future=[];self.app.busy=False
        self.app.respect_fixed_var.set(False);self.app.scope_var.set(c.SCOPES['core_fixed']);self.app.steps_var.set('20');self.app.refresh();self.root.update()
    def tearDown(self):
        for widget in self.root.winfo_children():
            if isinstance(widget,c.tk.Toplevel):widget.destroy()
        self.error_patch.stop();self.assertFalse(self.errors,self.errors)
    def finish(self):
        deadline=time.monotonic()+20
        while self.app.busy and time.monotonic()<deadline:self.root.update();time.sleep(.01)
        self.root.update();self.assertFalse(self.app.busy)
    def test_default_launcher_uses_native_and_fresh_suppresses_recovery(self):
        with (mock.patch.object(c.tk,'Tk',return_value=self.root),mock.patch.object(c,'NativeApp') as native,
              mock.patch.object(self.root,'mainloop') as loop,mock.patch.object(w,'run') as web):
            self.assertEqual(c.main(['--fresh','--config-dir',self.tmp.name]),0)
        web.assert_not_called();loop.assert_called_once()
        self.assertFalse(native.call_args.kwargs['recover_prompt'])
        self.assertIn(c.VERSION,self.root.title())
    def test_hover_help_opens_closes_and_describes_current_slot_locations(self):
        tip=next(t for t in self.app.help_tips if callable(t.text) and 'R: Sn' in t.text())
        notebook=tip.widget
        while not isinstance(notebook,c.ttk.Notebook):notebook=notebook.master
        notebook.select(0);self.root.update()
        text=tip.text();self.assertIn('R1: Sn1',text);self.assertIn('L 현재 위치: 이 코어에는 없음',text)
        tip.widget.event_generate('<Motion>',warp=True,x=tip.widget.winfo_width()//2,y=tip.widget.winfo_height()//2)
        deadline=time.monotonic()+2
        while tip.window is None and time.monotonic()<deadline:self.root.update();time.sleep(.01)
        self.assertIsNotNone(tip.window);self.assertTrue(tip.window.winfo_viewable())
        self.root.event_generate('<Motion>',warp=True,x=self.root.winfo_width()//2,y=self.root.winfo_height()//2);self.root.update();self.assertIsNone(tip.window)
        tip.widget.focus_force();self.root.update();tip.widget.event_generate('<Return>');self.root.update();self.assertIsNotNone(tip.window)
        tip.widget.event_generate('<Escape>');self.root.update();self.assertIsNone(tip.window)
    def test_calculation_controls_fit_and_progress_is_above_viewer(self):
        notebook=self.app.calculation_panel.master.master.master
        # Find the containing notebook without depending on Tk widget path IDs.
        while not isinstance(notebook,c.ttk.Notebook):notebook=notebook.master
        notebook.select(1);self.root.update()
        panel=self.app.calculation_panel;canvas=panel.master
        self.assertLessEqual(panel.winfo_reqheight(),canvas.winfo_height())
        self.assertLessEqual(self.app.gaussian_calc_button.winfo_rooty()+self.app.gaussian_calc_button.winfo_height(),canvas.winfo_rooty()+canvas.winfo_height())
        self.assertLessEqual(self.app.job_banner.winfo_rooty()+self.app.job_banner.winfo_height(),self.app.middle.winfo_rooty())
    def test_slot_selection_highlights_its_host_atoms(self):
        self.app.project=c.template(6);self.app.refresh();self.app.slots_dialog();self.root.update()
        win=next(w for w in self.root.winfo_children() if isinstance(w,c.tk.Toplevel))
        tree=next(w for w in descendants(win) if isinstance(w,c.ttk.Treeview))
        tree.selection_set('L1');self.root.update()
        slot=next(s for s in self.app.project['slots'] if s['id']=='L1')
        self.assertEqual(self.app.selection,slot['sn'])
        self.assertIn('L1: '+', '.join('Sn'+str(i) for i in slot['sn']),self.app.slot_help())
    def test_primary_sn_forcefield_action_reports_uff_fallback_and_undo(self):
        c.attach_fragment(self.app.project,'[*:1]CCC',slot_id='R1',cleanup=False)
        before=c.clone(self.app.project);self.app.ff_var.set('MMFF94');self.app.uff_fallback_var.set(True)
        with c.rdBase.BlockLogs():self.app.optimize();self.finish()
        self.assertIn('요청 MMFF94 → 적용 UFF',self.app.calculation_summary.get())
        self.assertEqual(self.app.project['bonds'],before['bonds'])
        a,b=c.index_atoms(self.app.project),c.index_atoms(before)
        for i in a:
            if a[i].get('core'):np.testing.assert_array_equal(c.xyz(a[i]),c.xyz(b[i]))
        self.assertEqual(self.app.job_percent.get(),100);self.app.undo();self.assertEqual(self.app.project,before)
    def test_four_scope_controls_select_expected_atoms(self):
        s=c.attach_fragment(self.app.project,'[*:1]CCC',slot_id='R1',cleanup=False);self.app.refresh()
        for scope in c.SCOPES:
            self.app.scope_var.set(c.SCOPES[scope]);self.root.update()
            plan=c.scope_plan(self.app.project,scope,False)
            self.assertIn(f"이동 {plan['movingCount']}",self.app.scope_summary.get())
            self.app.select_scope('movingIds');self.assertEqual(self.app.selection,plan['movingIds'])
            self.app.select_scope('fixedIds');self.assertEqual(self.app.selection,plan['fixedIds'])
        self.app.scope_var.set(c.SCOPES['all']);self.app.respect_fixed_var.set(True)
        self.assertIn('고정 38',self.app.scope_summary.get())
    def test_contact_dialog_only_displays_relevant_fields(self):
        self.app.contact_dialog();self.root.update()
        win=next(w for w in self.root.winfo_children() if isinstance(w,c.tk.Toplevel))
        mode=next(w for w in descendants(win) if isinstance(w,c.ttk.Combobox))
        labels={w.cget('text'):w for w in descendants(win) if isinstance(w,c.ttk.Label)}
        self.assertTrue(labels['vdW 계수'].winfo_ismapped());self.assertFalse(labels['공통 최소 거리 Å'].winfo_ismapped())
        mode.set('minimum');self.root.update()
        self.assertFalse(labels['vdW 계수'].winfo_ismapped());self.assertTrue(labels['공통 최소 거리 Å'].winfo_ismapped())
        minimum=next(w for w in labels['공통 최소 거리 Å'].master.winfo_children() if isinstance(w,c.ttk.Entry))
        minimum.delete(0,'end');minimum.insert(0,'2.3')
        next(w for w in descendants(win) if isinstance(w,c.ttk.Button) and w.cget('text')=='적용').invoke()
        self.assertEqual(self.app.project['metadata']['contactCriteria']['minimum'],2.3)
    def read_external_clipboard(self):
        child=subprocess.Popen([sys.executable,'-c',"import tkinter as t,sys;r=t.Tk();r.withdraw();sys.stdout.write(r.clipboard_get(type='UTF8_STRING'));r.destroy()"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        deadline=time.monotonic()+8
        try:
            while child.poll() is None and time.monotonic()<deadline:self.root.update();time.sleep(.01)
            out,err=child.communicate(timeout=2);self.assertEqual(child.returncode,0,err);return out
        finally:
            if child.poll() is None:child.kill();child.communicate()
    def test_xyz_clipboard_updates_for_separate_x11_client(self):
        self.app.copy_xyz();old=self.read_external_clipboard();self.assertEqual(old,c.export_xyz(self.app.project))
        self.app.project['atoms'][0]['x']+=1.25;self.app.refresh();self.app.copy_xyz()
        new=self.read_external_clipboard();self.assertNotEqual(old,new);self.assertEqual(new,c.export_xyz(self.app.project))
    def test_paste_refreshes_clipboard_and_replaces_selection(self):
        win=self.app.dialog('test');entry=c.ttk.Entry(win);entry.pack();text=c.tk.Text(win);text.pack();self.app.apply_theme();self.root.update()
        for widget in (entry,text):
            self.assertFalse(bool(int(widget.cget('exportselection'))))
            for value in ('CC(=O)O','한글 새 클립보드'):
                self.root.clipboard_clear();self.root.clipboard_append(value)
                if isinstance(widget,c.tk.Text):
                    widget.delete('1.0','end');widget.insert('1.0','stale');widget.tag_add('sel','1.0','end-1c')
                else:widget.delete(0,'end');widget.insert(0,'stale');widget.selection_range(0,'end')
                widget.event_generate('<<Paste>>');self.root.update()
                self.assertEqual(widget.get('1.0','end-1c') if isinstance(widget,c.tk.Text) else widget.get(),value)
    def test_example_creation_uses_exterior_ligands_and_one_step_undo(self):
        before=c.clone(self.app.project);self.app.core_var.set('12');self.app.ff_var.set('MMFF94')
        self.app.example();self.finish()
        for slot in self.app.project['slots']:
            atoms=c.index_atoms(self.app.project);new=[atoms[i] for i in slot['ligandIds']]
            guard=c.CorePlacement(self.app.project,slot['sn'],new,self.app.project['bonds'])
            self.assertTrue(guard.safe([c.xyz(a) for a in new]))
            self.assertEqual(slot['placement']['policy'],'core-outward-5.2')
        self.assertEqual(self.app.job_percent.get(),100);self.app.undo();self.assertEqual(self.app.project,before)
    def test_native_cleanup_scope_progress_rigidity_and_undo(self):
        c.attach_fragment(self.app.project,'[*:1]CCC',slot_id='R1',cleanup=False)
        before=c.clone(self.app.project);self.app.scope_var.set(c.SCOPES['rigid']);self.app.cleanup();self.finish()
        self.assertEqual(self.app.job_percent.get(),100);self.assertIn('임의 단위',self.app.calculation_summary.get())
        self.assertEqual(self.app.project['metadata']['lastCleanup']['scope'],'rigid')
        self.assertEqual(len(self.app.history),1);self.app.undo();self.assertEqual(self.app.project,before)
    def test_native_partial_progress_cancel_preserves_history(self):
        before=c.clone(self.app.project);reached=threading.Event()
        def work(cancel,progress):
            progress(dict(message='1/2 완료',percent=50));reached.set();cancel.wait(5);raise InterruptedError('취소')
        self.app.run_task('test',work);self.assertTrue(reached.wait(3))
        deadline=time.monotonic()+3
        while self.app.job_percent.get()!=50 and time.monotonic()<deadline:self.root.update();time.sleep(.01)
        self.assertEqual(self.app.job_percent.get(),50);self.assertEqual(str(self.app.calc_buttons[0].cget('state')),'disabled')
        self.app.cancel_button.invoke();self.finish()
        self.assertEqual(self.app.project,before);self.assertEqual(self.app.history,[]);self.assertLess(self.app.job_percent.get(),100)
        self.assertIn('취소',self.app.busy_var.get())


if __name__=='__main__':unittest.main()
