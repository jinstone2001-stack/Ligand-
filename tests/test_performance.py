"""Scientific equivalence, immutable history, async save and compact HTTP checks."""
import gzip
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock
from urllib.parse import quote
import numpy as np
import TinOxoStudio as c
import TinOxoWeb as w


class PoseScorerTests(unittest.TestCase):
    def check_scores(self, old_count, new_count, criteria):
        rng=np.random.default_rng(812)
        positions=rng.uniform(-35,35,(old_count+new_count,3))
        atoms=[dict(id=i+1,element=('C','O','H','Sn')[i%4],x=float(r[0]),y=float(r[1]),z=float(r[2]),core=i%13==0) for i,r in enumerate(positions)]
        old,new=atoms[:old_count],atoms[old_count:]
        old_bonds=[dict(a=1,b=2),dict(a=2,b=3)]
        bonds=[dict(a=3,b=old_count+1),dict(a=old_count+1,b=old_count+2)]
        p=dict(atoms=old,bonds=old_bonds,metadata={'contactCriteria':criteria},slots=[])
        scorer=c.PlacementScorer(p,new,bonds)
        for theta in (0,.2,1.1):
            points=positions[old_count:]@c.axis_rotation([1,2,3],theta).T+[.4,-.7,.2]
            for atom,point in zip(new,points):c.set_xyz(atom,point)
            self.assertAlmostEqual(scorer.score(points),c.placement_score(p,new,bonds),places=8)
        return scorer
    def test_dense_radii_matches_original_score(self):
        self.assertTrue(self.check_scores(36,12,c.DEFAULTS['contact']).dense)
    def test_dense_minimum_matches_original_score(self):
        self.check_scores(36,12,dict(mode='minimum',minimum=3.2))
    def test_sparse_radii_matches_original_score(self):
        self.assertFalse(self.check_scores(600,420,c.DEFAULTS['contact']).dense)
    def test_sparse_minimum_matches_original_score(self):
        self.check_scores(600,420,dict(mode='minimum',minimum=3.2))
    def test_complete_pose_search_preserves_selected_geometry(self):
        original=c.PlacementScorer
        class Reference:
            calls=0
            def __init__(self,p,atoms,bonds):self.p=p;self.atoms=c.clone(atoms);self.bonds=bonds
            def score(self,points):
                Reference.calls+=1
                for a,r in zip(self.atoms,points):c.set_xyz(a,r)
                return c.placement_score(self.p,self.atoms,self.bonds)
        fast=c.template(12);slow=c.clone(fast)
        c.attach_fragment(fast,'[*:1]CCCCCC',parent=1,cleanup=True)
        with mock.patch.object(c,'PlacementScorer',Reference):c.attach_fragment(slow,'[*:1]CCCCCC',parent=1,cleanup=True)
        self.assertEqual(Reference.calls,252)
        np.testing.assert_allclose([c.xyz(a) for a in fast['atoms']],[c.xyz(a) for a in slow['atoms']],atol=1e-7)
        self.assertIs(c.PlacementScorer,original)
    def test_geometry_reuses_atom_lookup_and_preserves_measurements(self):
        p=c.template(12)
        with mock.patch.object(c,'index_atoms',wraps=c.index_atoms) as lookup:
            rows=c.geometry_rows(p)
            self.assertEqual(lookup.call_count,1)
        import re
        for row in rows:
            ids=[int(v) for v in re.findall(r'[A-Z][a-z]?(\d+)',row[1])]
            self.assertAlmostEqual(row[2],c.measurement(p,ids)[1])
    def test_batch_fragment_cache_and_invalid_indices(self):
        p=c.template(12);cache={}
        with mock.patch.object(c,'build_fragment',wraps=c.build_fragment) as build:
            for host in (1,2):c.attach_fragment(p,'CCN',parent=host,mode='coordinate',attachment_index=2,cleanup=False,fragment_cache=cache)
            self.assertEqual(build.call_count,1)
        for bad in (True,2.0,'2'):
            with self.assertRaises(ValueError):c.attach_fragment(c.template(12),'CCN',parent=1,mode='coordinate',attachment_index=bad,fragment_cache=cache)


class SnapshotSaveTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.ws=w.Workspace(self.tmp.name,recover=False,async_save=True)
    def tearDown(self):self.ws.close();self.tmp.cleanup()
    def edit(self,action,**data):return self.ws.mutate(action,dict(revision=self.ws.revision,known=self.ws.versions.copy(),**data),compact=True)
    def test_history_is_immutable_across_bank_settings_and_graph_changes(self):
        snapshots=[]
        def remember():snapshots.append((self.ws.snapshot(),w.clean_json(self.ws.snapshot())))
        remember();self.edit('bank',op='store',name='one');aid=self.ws.bank['activeId'];remember()
        self.edit('bank',op='rename',id=aid,name='renamed');remember()
        self.edit('bank',op='delete',id=aid);remember();self.edit('bank',op='restore');remember()
        self.edit('reset',n=3);remember();self.edit('undo');remember();self.edit('redo');remember()
        self.edit('settings',settings={'theme':'light'});remember();self.edit('favorite',name='amine',smiles='CCN');remember()
        self.edit('contacts',criteria=dict(mode='minimum',minimum=2,vdw=.75,covalent=1.18));remember()
        self.edit('fixed',ids=[1])
        for snapshot,encoded in snapshots:self.assertEqual(w.clean_json(snapshot),encoded)
        self.assertEqual(snapshots[1][0][1]['activeId'],aid)
    def test_delta_and_bank_summary_do_not_send_unchanged_graphs(self):
        self.edit('bank',op='store',name='one')
        state=self.ws.view_state();self.assertEqual(state['bank']['entries'][0]['atoms'],38)
        self.assertNotIn('project',state['bank']['entries'][0])
        before=self.ws.project
        delta=self.edit('settings',settings={'font_size':14})
        self.assertIn('settings',delta);self.assertNotIn('project',delta);self.assertNotIn('bank',delta)
        self.assertIs(self.ws.project,before)
        delta=self.edit('color',ids=[1],color='#123456')
        self.assertIn('project',delta);self.assertNotIn('settings',delta);self.assertNotIn('bank',delta)
        idle=self.ws.view_state(self.ws.versions);self.assertNotIn('project',idle)
    def test_slow_disk_never_holds_edit_lock_and_flush_saves_latest(self):
        started=threading.Event();release=threading.Event();finished=threading.Event();real=c.atomic_write
        def blocked(*args,**kwargs):started.set();release.wait(4);return real(*args,**kwargs)
        with mock.patch.object(c,'atomic_write',side_effect=blocked):
            self.edit('color',ids=[1],color='#111111');self.assertTrue(started.wait(2))
            def edit_again():self.edit('color',ids=[1],color='#222222');finished.set()
            thread=threading.Thread(target=edit_again);thread.start()
            try:self.assertTrue(finished.wait(.8),'an edit waited for disk I/O')
            finally:release.set();thread.join(4)
            self.ws.flush()
        saved=json.loads(self.ws.path.read_text());self.assertEqual(saved['project']['atoms'][0]['color'],'#222222')
        self.assertEqual(self.ws.save_status['state'],'saved');self.assertEqual(self.ws.save_status['revision'],2)
    def test_rapid_edits_coalesce_and_shutdown_flushes(self):
        with mock.patch.object(c,'atomic_write',wraps=c.atomic_write) as write:
            for i in range(5):self.edit('color',ids=[1],color=f'#{i:06x}')
            self.ws.close();self.assertEqual(write.call_count,1)
        self.assertEqual(json.loads(self.ws.path.read_text())['project']['atoms'][0]['color'],'#000004')
    def test_shutdown_flushes_then_rejects_new_edits(self):
        self.edit('color',ids=[1],color='#123456');self.ws.close()
        self.assertEqual(self.ws.save_status['state'],'saved')
        with self.assertRaises(w.Conflict):self.edit('color',ids=[1],color='#222222')
        self.assertEqual(json.loads(self.ws.path.read_text())['project']['atoms'][0]['color'],'#123456')
    def test_background_save_error_is_visible_without_losing_work(self):
        with mock.patch.object(c,'atomic_write',side_effect=OSError('disk full')):
            self.edit('fixed',ids=[1]);self.ws.flush()
        self.assertEqual(self.ws.revision,1);self.assertEqual(self.ws.save_status['state'],'error');self.assertIn('disk full',self.ws.save_status['error'])
        self.edit('undo');self.ws.flush();self.assertEqual(self.ws.save_status['state'],'saved')
    def test_expensive_queries_do_not_hold_workspace_lock(self):
        entered=threading.Event();release=threading.Event()
        def slow(_):entered.set();release.wait(3);return []
        with mock.patch.object(c,'geometry_rows',side_effect=slow):
            thread=threading.Thread(target=lambda:self.ws.query('geometry',{}));thread.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertTrue(self.ws.lock.acquire(timeout=.3),'query held workspace lock')
                self.ws.lock.release()
                self.assertEqual(self.ws.view_state()['revision'],0)
            finally:release.set();thread.join(3)


class TransportPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ws=w.Workspace(self.tmp.name,recover=False,async_save=True)
        self.server=w.LocalServer(('127.0.0.1',0),self.ws,'performance-token');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(3);self.tmp.cleanup()
    def conn(self):return http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=4)
    def test_keepalive_gzip_etag_and_token_protection(self):
        conn=self.conn();conn.request('GET','/web/app.js',headers={'Accept-Encoding':'gzip'})
        r=conn.getresponse();raw=r.read();self.assertEqual(r.status,200);self.assertEqual(r.version,11);self.assertEqual(r.getheader('Content-Encoding'),'gzip')
        self.assertIn(b'editQueue',gzip.decompress(raw));etag=r.getheader('ETag');sock=conn.sock
        conn.request('GET','/web/app.js',headers={'If-None-Match':etag});r=conn.getresponse();self.assertEqual(r.status,304);self.assertEqual(r.read(),b'');self.assertIs(conn.sock,sock)
        conn.request('GET','/api/state',headers={'X-Tinoxo-Token':'performance-token','Accept-Encoding':'gzip;q=0'});r=conn.getresponse();self.assertEqual(r.status,200);self.assertIsNone(r.getheader('Content-Encoding'));json.loads(r.read())
        conn.request('POST','/api/edit/reset',body=b'{}',headers={'X-Tinoxo-Token':'bad','Content-Type':'application/json'});r=conn.getresponse();self.assertEqual(r.status,403);self.assertEqual(r.getheader('Connection'),'close');r.read();conn.close()
    def test_compact_wire_format_and_unchanged_state_poll(self):
        conn=self.conn();headers={'X-Tinoxo-Token':'performance-token','Accept-Encoding':'gzip'}
        conn.request('GET','/api/state',headers=headers);r=conn.getresponse();first=json.loads(gzip.decompress(r.read()));known=first['versions']
        conn.request('GET','/api/state?known='+quote(json.dumps(known)),headers=headers);r=conn.getresponse();raw=r.read();data=json.loads(gzip.decompress(raw) if r.getheader('Content-Encoding') else raw)
        self.assertNotIn('project',data);self.assertNotIn('settings',data);self.assertNotIn('bank',data)
        body=json.dumps(dict(revision=0,known=known,settings={'theme':'light'}))
        conn.request('POST','/api/edit/settings',body=body,headers={**headers,'Content-Type':'application/json'});r=conn.getresponse();raw=r.read();data=json.loads(gzip.decompress(raw) if r.getheader('Content-Encoding') else raw)
        self.assertEqual(r.status,200);self.assertIn('settings',data);self.assertNotIn('project',data);conn.close()
    def test_ssh_does_not_open_remote_browser_unless_explicit(self):
        args=SimpleNamespace(port=0,host='127.0.0.1',config_dir=self.tmp.name,project=None,fresh=True,no_browser=False)
        def timer(delay,fn):return SimpleNamespace(start=fn,cancel=lambda:None)
        with mock.patch.dict(os.environ,{'SSH_CONNECTION':'client 123 server 22'}),mock.patch.object(w.webbrowser,'open') as opener,mock.patch.object(w.threading,'Timer',side_effect=timer),mock.patch.object(w.LocalServer,'serve_forever',side_effect=KeyboardInterrupt):
            self.assertEqual(w.run(args),0);opener.assert_not_called()
            args.open_browser=True;self.assertEqual(w.run(args),0);opener.assert_called_once()


if __name__=='__main__':unittest.main()
