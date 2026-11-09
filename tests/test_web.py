"""HTTP, transactional workspace, port and browser-launch regressions (no DISPLAY)."""
import base64, http.client, json, socket, tempfile, threading, time, unittest, subprocess, sys, queue, os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import TinOxoStudio as c
import TinOxoWeb as w

class WorkspaceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.ws=w.Workspace(self.tmp.name,recover=False)
 def tearDown(self):
  if self.ws.job and self.ws.job['status']=='running':self.ws.job['cancel'].set();self.ws.job['thread'].join(5)
  self.tmp.cleanup()
 def edit(self,action,**data):return self.ws.mutate(action,dict(revision=self.ws.revision,**data))
 def wait(self):
  self.ws.job['thread'].join(15);self.assertFalse(self.ws.job['thread'].is_alive());return self.ws.public_job()
 def test_reset_cores_hydroxo_and_undo(self):
  r=self.edit('hydroxo');self.assertEqual(len(r['result']['selection']),6);self.assertEqual(len(self.ws.project['atoms']),32)
  self.edit('undo');self.assertEqual(len(self.ws.project['atoms']),38)
  for n,count in [(3,6),(6,12),(12,38)]:self.edit('reset',n=n);self.assertEqual(len(self.ws.project['atoms']),count)
 def test_invalid_edits_roll_back_and_stale_revision_rejected(self):
  before=self.ws.snapshot()
  with self.assertRaises(ValueError):self.edit('atom',ids=[1],values=dict(element='Sn',x='nan',y=0,z=0))
  self.assertEqual(self.ws.snapshot(),before);self.assertEqual(self.ws.revision,0)
  self.edit('fixed',ids=[1])
  with self.assertRaises(w.Conflict):self.ws.mutate('delete',dict(revision=0,ids=[1]))
 def test_disk_error_does_not_commit_history(self):
  before=self.ws.snapshot()
  with mock.patch.object(self.ws,'persist',side_effect=OSError('disk full')),self.assertRaises(OSError):self.edit('delete',ids=[1])
  self.assertEqual(self.ws.snapshot(),before);self.assertEqual(self.ws.revision,0);self.assertFalse(self.ws.history)
 def test_atom_fixed_color_and_persistent_recovery(self):
  self.edit('atom',ids=[1],values=dict(element='Sn',x=1.1,y=2.2,z=3.3,charge=1,isotope=120));self.edit('fixed',ids=[1]);self.edit('color',ids=[1],color='#123456')
  recovered=w.Workspace(self.tmp.name);atom=c.index_atoms(recovered.project)[1]
  self.assertEqual((atom['x'],atom['charge'],atom['isotope'],atom['color']),(1.1,1,120,'#123456'));self.assertFalse(atom['fixed'])
 def test_undo_redo_and_history_reset_after_new_edit(self):
  self.edit('delete',ids=[1]);self.edit('undo');self.assertEqual(len(self.ws.project['atoms']),38)
  self.edit('redo');self.assertEqual(len(self.ws.project['atoms']),37)
  self.edit('undo');self.edit('color',ids=[1],color='#123456');self.assertFalse(self.ws.future)
 def test_bank_store_copy_rename_delete_restore_load(self):
  self.edit('bank',op='store',name='코어 A');aid=self.ws.bank['activeId'];self.edit('bank',op='copy',name='코어 A')
  self.assertEqual(len(self.ws.bank['entries']),2);self.edit('bank',op='rename',id=aid,name='원본')
  self.edit('bank',op='delete',id=aid);self.edit('bank',op='restore');self.edit('reset',n=3);self.edit('bank',op='load',id=aid)
  self.assertEqual(len(self.ws.project['atoms']),38);self.assertEqual(self.ws.state()['bank']['entries'][-1]['formula'],'H6O20Sn12')
 def test_favorites_settings_and_import_export_roundtrip(self):
  self.edit('favorite',name='아민',smiles='CCN',mode='coordinate');self.edit('settings',settings=dict(theme='light',font_size=14,korean_font='굴림'))
  out=self.ws.query('export',dict(kind='project'))
  self.edit('reset',n=3);self.edit('import',name='saved.tinoxo.json',content=base64.b64encode(out['text'].encode()).decode())
  self.assertEqual(len(self.ws.project['atoms']),38);self.assertEqual(self.ws.settings['favorites'][0]['smiles'],'CCN');self.assertEqual(self.ws.settings['font_size'],14)
 def test_upload_rejects_bad_data_without_change(self):
  for name,data in [('bad.json',b'not json'),('bad.exe',b'code')]:
   with self.assertRaises(ValueError):self.edit('import',name=name,content=base64.b64encode(data).decode())
  self.assertEqual(self.ws.revision,0)
 def test_bad_bundle_does_not_replace_existing_workspace(self):
  before=self.ws.snapshot();data=dict(project=c.template(3),bank={'entries':'not a list'})
  with self.assertRaises(ValueError):self.edit('import',name='bad.json',content=base64.b64encode(json.dumps(data).encode()).decode())
  self.assertEqual(self.ws.snapshot(),before);self.assertEqual(self.ws.revision,0)
 def test_legacy_cp949_import(self):
  p=c.template(3);p['title']='한글 구조';raw=json.dumps(p).replace('\\ud55c\\uae00 \\uad6c\\uc870','한글 구조').encode('cp949')
  self.edit('import',name='legacy.json',content=base64.b64encode(raw).decode());self.assertEqual(self.ws.project['title'],'한글 구조')
 def test_selected_nitrogen_attaches_to_two_hosts(self):
  self.ws.start_job('attach',dict(revision=0,cleanup=False,plans=[dict(parents=[1,2],smiles='CCN',mode='coordinate',attachment_index=2)]))
  self.assertEqual(self.wait()['status'],'done');self.assertEqual(len(self.ws.project['atoms']),58)
  slots=[s for s in self.ws.project['slots'] if s.get('custom')];self.assertEqual(len(slots),2)
  for s in slots:self.assertEqual(c.index_atoms(self.ws.project)[s['anchor']]['element'],'N');self.assertEqual(s['attachmentIndex'],2)
  self.edit('undo');self.assertEqual(len(self.ws.project['atoms']),38)
 def test_invalid_task_does_not_change_project(self):
  self.ws.start_job('attach',dict(revision=0,plans=[dict(parents=[1],smiles='CCN',mode='coordinate',attachment_index=99)]))
  self.assertEqual(self.wait()['status'],'error');self.assertEqual(len(self.ws.project['atoms']),38);self.assertEqual(self.ws.revision,0)
 def test_slot_attachment_snc_length_and_clear(self):
  self.ws.start_job('attach',dict(revision=0,cleanup=False,plans=[dict(slot_id='R1',smiles='CCO',mode='covalent',attachment_index=1)]));self.assertEqual(self.wait()['status'],'done')
  self.edit('snc',length=2.25);s=next(s for s in self.ws.project['slots'] if s['id']=='R1');a=c.index_atoms(self.ws.project)
  self.assertAlmostEqual(float(c.np.linalg.norm(c.xyz(a[s['anchor']])-c.xyz(a[1]))),2.25)
  self.ws.start_job('attach',dict(revision=self.ws.revision,plans=[dict(slot_id='R1',smiles='')]))
  self.assertEqual(self.wait()['status'],'done');self.assertEqual(len(self.ws.project['atoms']),38)
 def test_example_and_optimization_use_original_engine(self):
  self.ws.start_job('example',dict(revision=0,n=3));self.assertEqual(self.wait()['status'],'done')
  self.ws.start_job('optimize',dict(revision=self.ws.revision,scope='ligands'));self.assertEqual(self.wait()['status'],'done')
  self.assertIn('lastOptimization',self.ws.project['metadata'])
 def test_running_job_cancellation_and_edit_guard(self):
  started=threading.Event()
  def slow(*args,**kw):
   started.set();kw['cancel'].wait(3)
   if kw['cancel'].is_set():raise InterruptedError('cancelled')
   return args[0],[]
  with mock.patch.object(c,'optimize_project',side_effect=slow):
   self.ws.start_job('optimize',dict(revision=0));self.assertTrue(started.wait(2))
   with self.assertRaises(w.Conflict):self.edit('delete',ids=[1])
   self.ws.job['cancel'].set();self.assertEqual(self.wait()['status'],'cancelled')
  self.assertEqual(self.ws.revision,0)
 def test_ligand_svg_keeps_original_atom_numbers(self):
  result=self.ws.query('ligand',dict(smiles='CCN',mode='coordinate',selected=2))
  self.assertEqual(result['selected'],2);self.assertIn('data-atom="2"',result['svg']);self.assertEqual(result['candidates'][2]['element'],'N')
  r=self.ws.query('ligand',dict(smiles='COC',mode='covalent'));self.assertNotIn(1,[a['index'] for a in r['candidates']])
 def test_gaussian_custom_and_default_exports(self):
  opts=c.gaussian_defaults(self.ws.project);r=self.ws.query('gaussian',dict(options=opts));self.assertIn('/GenECP',r['text']);self.assertIn('Sn 0\nDef2',r['text'])
  opts.update(method='PBE1PBE',basis_mode='custom',custom_basis='H O Sn 0\nDef2SVP\n****\n\nSn 0\nDef2\n')
  self.assertIn('PBE1PBE/GenECP',self.ws.query('gaussian',dict(options=opts))['text'])
  for kind in ['project','xyz','sdf','pdb','report','csv','html']:self.assertTrue(self.ws.query('export',dict(kind=kind))['text'])
 def test_bonds_contacts_measurements_resonance(self):
  self.edit('contacts',criteria=dict(mode='minimum',vdw=.75,covalent=1.18,minimum=2))
  self.assertIsInstance(self.ws.query('contacts',{}),list);self.assertTrue(self.ws.query('bonds',{}));self.assertTrue(self.ws.query('geometry',{}))
  self.assertGreater(self.ws.query('measure',dict(ids=[1,2]))['value'],0)
  self.assertGreaterEqual(self.ws.query('resonance',dict(smiles='CC(=O)[O-]'))['forms'],2)
  self.edit('bond',ids=[1,2],order=1,kind='coordinate');self.edit('bond',ids=[1,2],remove=True)
  self.assertFalse(any(c.bond_key(b['a'],b['b'])==(1,2) for b in self.ws.project['bonds']))

class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.ws=w.Workspace(self.tmp.name);self.server=w.LocalServer(('127.0.0.1',0),self.ws,'token-for-test');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(3);self.tmp.cleanup()
 def request(self,path,data=None,token='token-for-test',origin=None,raw=None):
  conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10);headers={'X-Tinoxo-Token':token}
  if origin:headers['Origin']=origin
  body=json.dumps(data).encode() if data is not None else raw
  if body is not None:headers['Content-Type']='application/json'
  conn.request('POST' if body is not None else 'GET',path,body=body,headers=headers);r=conn.getresponse();payload=r.read();conn.close();return r.status,payload,r.headers
 def test_static_files_and_no_directory_exposure(self):
  for path in ['/','/web/app.js','/web/viewer.js','/web/style.css','/fonts/NanumGothic-Regular.ttf']:
   status,raw,headers=self.request(path,token='');self.assertEqual(status,200,path);self.assertTrue(raw);self.assertIn('nosniff',headers['X-Content-Type-Options'])
  for path in ['/TinOxoStudio.py','/web/../TinOxoStudio.py','/web/%2e%2e/TinOxoWeb.py']:
   self.assertEqual(self.request(path)[0],404,path)
 def test_api_auth_origin_and_request_validation(self):
  self.assertEqual(self.request('/api/state',token='')[0],403)
  self.assertEqual(self.request('/api/edit/delete',dict(revision=0,ids=[1]),origin='https://evil.invalid')[0],403)
  self.assertEqual(self.request('/api/edit/delete',raw=b'{')[0],400)
  self.assertEqual(self.ws.revision,0)
 def test_http_reset_and_revision_conflict(self):
  code,raw,_=self.request('/api/edit/reset',dict(revision=0,n=3));self.assertEqual(code,200);self.assertEqual(len(json.loads(raw)['project']['atoms']),6)
  self.assertEqual(self.request('/api/edit/reset',dict(revision=0,n=6))[0],409)
 def test_config_and_save_to_explicit_server_path(self):
  code,raw,_=self.request('/api/config');self.assertEqual(code,200);self.assertEqual(len(json.loads(raw)['ligands']),43)
  path=Path(self.tmp.name)/'input.gjf';opts=c.gaussian_defaults(self.ws.project)
  code,raw,_=self.request('/api/save',dict(revision=0,kind='gaussian',options=opts,path=str(path)));self.assertEqual(code,200,raw);self.assertIn('GenECP',path.read_text())
 def test_http_async_attachment_and_download(self):
  code,raw,_=self.request('/api/task/attach',dict(revision=0,cleanup=False,plans=[dict(parents=[1],smiles='CCN',mode='coordinate',attachment_index=2)]));self.assertEqual(code,200,raw)
  self.ws.job['thread'].join(10);code,raw,_=self.request('/api/job');self.assertEqual(json.loads(raw)['job']['status'],'done')
  code,raw,_=self.request('/api/query/export',dict(kind='project'));self.assertEqual(code,200);saved=json.loads(json.loads(raw)['text']);self.assertEqual(saved['appVersion'],c.VERSION)

class LauncherTests(unittest.TestCase):
 def test_prompt_and_explicit_port_selection(self):
  self.assertEqual(w.choose_port(None,lambda prompt:'8890',True),8890);self.assertEqual(w.choose_port(None,lambda p:'',True),8765)
  self.assertEqual(w.choose_port(None,is_interactive=False),8765);self.assertEqual(w.choose_port(0),0)
  for invalid in [-1,65536,'abc']:
   with self.assertRaises(ValueError):w.choose_port(invalid)
 def test_cli_defaults_to_web_without_tk(self):
  with mock.patch.object(w,'run',return_value=0) as run: self.assertEqual(c.main(['--port','8877','--no-browser']),0)
  args=run.call_args.args[0];self.assertEqual(args.port,8877);self.assertTrue(args.no_browser);self.assertFalse(args.native)
 def test_occupied_port_fails_without_browser_open(self):
  with tempfile.TemporaryDirectory() as d,socket.socket() as sock:
   sock.bind(('127.0.0.1',0));sock.listen()
   args=SimpleNamespace(port=sock.getsockname()[1],host='127.0.0.1',config_dir=d,project=None,fresh=True,no_browser=False)
   with mock.patch.object(w.webbrowser,'open') as opener:self.assertEqual(w.run(args),2);opener.assert_not_called()
 def test_browser_opens_actual_selected_port_url(self):
  with tempfile.TemporaryDirectory() as d:
   args=SimpleNamespace(port=0,host='127.0.0.1',config_dir=d,project=None,fresh=True,no_browser=False)
   def timer(delay,fn):return SimpleNamespace(start=fn,cancel=lambda:None)
   with mock.patch.object(w.webbrowser,'open') as opener,mock.patch.object(w.threading,'Timer',side_effect=timer),mock.patch.object(w.LocalServer,'serve_forever',side_effect=KeyboardInterrupt):
    self.assertEqual(w.run(args),0)
   url=opener.call_args.args[0];self.assertRegex(url,r'^http://127\.0\.0\.1:[1-9][0-9]*/#token=[A-Za-z0-9_-]+$')
 def test_browser_unavailable_prints_full_url_without_failing_launch(self):
  import contextlib,io
  with tempfile.TemporaryDirectory() as d:
   args=SimpleNamespace(port=0,host='127.0.0.1',config_dir=d,project=None,fresh=True,no_browser=False)
   output=io.StringIO()
   def timer(delay,fn):return SimpleNamespace(start=fn,cancel=lambda:None)
   with mock.patch.object(w.webbrowser,'open',return_value=False) as opener,mock.patch.object(w.threading,'Timer',side_effect=timer),mock.patch.object(w.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),contextlib.redirect_stdout(output):
    self.assertEqual(w.run(args),0)
   self.assertIn('브라우저 자동 열기를 완료하지 못했습니다.',output.getvalue())
   self.assertGreaterEqual(output.getvalue().count(opener.call_args.args[0]),2)
 def test_browser_os_error_prints_full_url_without_failing_launch(self):
  import contextlib,io
  with tempfile.TemporaryDirectory() as d:
   args=SimpleNamespace(port=0,host='127.0.0.1',config_dir=d,project=None,fresh=True,no_browser=False)
   output=io.StringIO()
   def timer(delay,fn):return SimpleNamespace(start=fn,cancel=lambda:None)
   with mock.patch.object(w.webbrowser,'open',side_effect=OSError('desktop opener unavailable')) as opener,mock.patch.object(w.threading,'Timer',side_effect=timer),mock.patch.object(w.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),contextlib.redirect_stdout(output):
    self.assertEqual(w.run(args),0)
   self.assertIn('브라우저 자동 열기 실패: desktop opener unavailable',output.getvalue())
   self.assertGreaterEqual(output.getvalue().count(opener.call_args.args[0]),2)
 def test_real_cli_with_ssh_opens_actual_server_url_by_default(self):
  from urllib.parse import urlsplit,parse_qs
  child='''from pathlib import Path
import json,runpy,sys,webbrowser
marker=Path(sys.argv[1]);app=sys.argv[2];workspace=sys.argv[3]
def opener(url,new=0,autoraise=True):
    marker.write_text(json.dumps(dict(url=url,new=new)),encoding="utf-8")
    return True
webbrowser.open=opener
sys.argv=[app,"--port","0","--fresh","--config-dir",workspace]
sys.path.insert(0,str(Path(app).parent))
runpy.run_path(app,run_name="__main__")
'''
  for remote in ('SSH_CONNECTION','SSH_CLIENT'):
   with self.subTest(variable=remote),tempfile.TemporaryDirectory() as d:
    marker=Path(d)/'browser.json'
    env={**os.environ,'DISPLAY':'','SSH_CONNECTION':'','SSH_CLIENT':'','PYTHONIOENCODING':'utf-8',remote:'client 123 server 22'}
    process=subprocess.Popen([sys.executable,'-c',child,str(marker),str(Path(c.__file__).resolve()),d],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',env=env)
    try:
     deadline=time.monotonic()+12
     while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
     self.assertTrue(marker.exists(),'default launch never requested a browser')
     # The real Timer wrote the browser request. Retry while its small file finishes.
     while True:
      try:opened=json.loads(marker.read_text(encoding='utf-8'));break
      except json.JSONDecodeError:
       if time.monotonic()>=deadline:raise
       time.sleep(.01)
     parsed=urlsplit(opened['url']);token=parse_qs(parsed.fragment)['token'][0]
     self.assertEqual(opened['new'],2)
     conn=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=5)
     try:
      conn.request('GET','/api/state',headers={'X-Tinoxo-Token':token})
      response=conn.getresponse();self.assertEqual(response.status,200)
      self.assertEqual(json.loads(response.read())['version'],c.VERSION)
     finally:conn.close()
    finally:process.terminate();process.communicate(timeout=5)
 def test_real_cli_serves_selected_port_without_display(self):
  from urllib.parse import urlsplit,parse_qs
  with tempfile.TemporaryDirectory() as d:
   process=subprocess.Popen([sys.executable,str(Path(c.__file__).resolve()),'--port','0','--no-browser','--fresh','--config-dir',d],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'DISPLAY':''})
   lines=queue.Queue()
   def read():
    for line in process.stdout:lines.put(line.strip())
   threading.Thread(target=read,daemon=True).start()
   try:
    banner=lines.get(timeout=12);url=lines.get(timeout=12);self.assertIn(c.VERSION,banner)
    parsed=urlsplit(url);token=parse_qs(parsed.fragment)['token'][0]
    conn=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=5);conn.request('GET','/api/state',headers={'X-Tinoxo-Token':token})
    response=conn.getresponse();self.assertEqual(response.status,200);self.assertEqual(json.loads(response.read())['version'],c.VERSION);conn.close()
   finally:process.terminate();process.communicate(timeout=5)

if __name__=='__main__':unittest.main()
