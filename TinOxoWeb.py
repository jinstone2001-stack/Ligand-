#!/usr/bin/env python3
"""Local browser UI for Tin Oxo Studio. No Tk, X11, CDN or web framework required."""
from __future__ import annotations
import base64, csv, io, json, math, mimetypes, os, re, secrets, sys, tempfile, threading, time, uuid, webbrowser, gzip, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs
import TinOxoStudio as c

ROOT = Path(__file__).resolve().parent
MAX_BODY = 32 * 1024 * 1024

class Conflict(ValueError): pass

def clean_json(obj):
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, default=lambda x: x.tolist() if hasattr(x, 'tolist') else int(x)).encode('utf-8')

def ligand_diagram(smiles, kind='A', mode='covalent', selected=None):
    from rdkit.Chem.Draw import rdMolDraw2D
    info=c.ligand_attachment_info(smiles,kind,mode);mol=c.Chem.Mol(info['mol'])
    c.AllChem.Compute2DCoords(mol)
    for a in mol.GetAtoms(): a.SetProp('atomNote',str(a.GetIdx()+1))
    selected=selected if selected in info['candidates'] else info['default']
    highlights=[selected]
    if kind in ('L','P'): highlights=next(ds for _,ds in info['groups'] if selected in ds)
    drawer=rdMolDraw2D.MolDraw2DSVG(800,380);drawer.drawOptions().padding=.12
    drawer.DrawMolecule(mol,highlightAtoms=highlights)
    points={i:[drawer.GetDrawCoords(i).x,drawer.GetDrawCoords(i).y] for i in range(mol.GetNumAtoms())}
    drawer.FinishDrawing();svg=drawer.GetDrawingText()
    targets=''.join(f'<circle data-atom="{i}" cx="{points[i][0]:.3f}" cy="{points[i][1]:.3f}" r="18" fill="transparent" style="cursor:pointer"><title>{mol.GetAtomWithIdx(i).GetSymbol()}{i+1}</title></circle>' for i in info['candidates'])
    svg=svg.replace('</svg>',targets+'</svg>')
    return dict(svg=svg,selected=selected,candidates=[dict(index=i,element=mol.GetAtomWithIdx(i).GetSymbol(),charge=mol.GetAtomWithIdx(i).GetFormalCharge()) for i in info['candidates']])

class Workspace:
    def __init__(self,config_dir=None,initial=None,recover=True,async_save=False):
        self.directory=Path(config_dir or os.environ.get('TINOXO_CONFIG_DIR',Path.home()/'.config/tinoxo-studio')).expanduser()
        self.path=self.directory/'web-workspace.json';self.lock=threading.RLock()
        self.project=c.template(12);self.settings=c.clone(c.DEFAULTS);self.bank={'version':2,'entries':[],'trash':[],'activeId':None,'revision':0}
        self.history=[];self.future=[];self.revision=0;self.job=None;self.logs=[]
        self.versions=dict(project=0,bank=0,settings=0);self._bank_summary=None;self._bank_source=None
        self.async_save=async_save;self.save_status=dict(state='saved',revision=0,error=None)
        self._save_condition=threading.Condition();self._pending_save=None;self._writing=False;self._closing=False;self._save_thread=None
        try:
            old=self.directory/'settings.json'
            if old.exists():self.settings.update(json.loads(c.read_unicode_text(old)))
            if recover and self.path.exists():self.load_data(json.loads(c.read_unicode_text(self.path)))
        except Exception as exc:self.log('복구 파일 확인 필요: '+str(exc))
        if initial:
            p,b,s=c.read_structure(initial);self.load_data(dict(project=p,bank=b,settings=s))
        try:self.validate_bundle(self.project,self.bank,self.settings)
        except ValueError as exc:self.settings=c.clone(c.DEFAULTS);self.log('설정 기본값 사용: '+str(exc))
        c.normalize_font_preferences(self.settings)
    def load_data(self,data):
        project=c.validate_project(data.get('project',data));bank=c.clone(data['bank']) if data.get('bank') else self.bank
        settings={**self.settings,**(data.get('settings') or {})}
        self.validate_bundle(project,bank,settings)
        self.project,self.bank,self.settings=project,bank,settings
    @staticmethod
    def validate_bundle(project,bank,settings,validate_graphs=True,validate_current=True):
        if validate_current:c.validate_project(project)
        if not isinstance(bank,dict) or not isinstance(bank.get('entries'),list):raise ValueError('구조 보관함 형식 오류')
        if len(bank['entries'])>100:raise ValueError('보관함은 100개까지 지원합니다.')
        if not isinstance(bank.get('trash',[]),list):raise ValueError('삭제 보관함 형식 오류')
        seen=set()
        for entry in bank['entries']:
            if not isinstance(entry,dict) or not isinstance(entry.get('id'),str) or entry['id'] in seen or not isinstance(entry.get('name'),str):raise ValueError('보관함 항목의 ID/이름 오류')
            seen.add(entry['id'])
            if validate_graphs:c.validate_project(entry['project'])
        if not isinstance(settings,dict) or not isinstance(settings.get('favorites',[]),list):raise ValueError('사용자 설정/SMILES 목록 형식 오류')
        for key in ('text_colors','element_colors'):
            if key in settings and not isinstance(settings[key],dict):raise ValueError('글꼴/원소 색상 설정 형식 오류')
        if validate_graphs:c.normalize_font_preferences(settings)
    def log(self,message):
        self.logs.append(time.strftime('%H:%M:%S')+'  '+str(message));self.logs=self.logs[-250:]
    def snapshot(self):return (self.project,self.bank,self.settings)
    def workspace_data(self):return dict(format='TinOxoStudio Python',version=3,appVersion=c.VERSION,project=self.project,bank=self.bank,settings=self.settings)
    def persist(self):c.atomic_write(self.path,clean_json(self.workspace_data()).decode())
    def _queue_save(self):
        # Published objects are immutable; background serialization needs no copy.
        with self._save_condition:
            self._pending_save=(self.revision,self.workspace_data());self._save_condition.notify_all()
            if self._save_thread is None:
                self._save_thread=threading.Thread(target=self._save_loop,name='tinoxo-autosave',daemon=True);self._save_thread.start()
        self.save_status=dict(state='pending',revision=self.revision,error=None)
    def _save_loop(self):
        while True:
            with self._save_condition:
                self._save_condition.wait_for(lambda:self._pending_save is not None or self._closing)
                if self._pending_save is None and self._closing:return
                # Coalesce rapid edits, but shutdown flushes immediately.
                deadline=time.monotonic()+.25
                while not self._closing:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:break
                    self._save_condition.wait(timeout=remaining)
                revision,data=self._pending_save;self._pending_save=None;self._writing=True
            error=None
            try:c.atomic_write(self.path,clean_json(data).decode())
            except Exception as exc:error=str(exc)
            with self.lock:
                if revision>=self.save_status['revision']:
                    self.save_status=dict(state='error' if error else 'saved',revision=revision,error=error)
                    if error:self.log('자동 저장 실패: '+error)
            with self._save_condition:self._writing=False;self._save_condition.notify_all()
    def flush(self):
        with self._save_condition:
            self._save_condition.notify_all()
            if not self._save_condition.wait_for(lambda:self._pending_save is None and not self._writing,timeout=15):raise TimeoutError('자동 저장이 아직 진행 중입니다.')
    def close(self):
        with self.lock:
            with self._save_condition:self._closing=True;self._save_condition.notify_all()
        if self._save_thread:self._save_thread.join()
    def _bank_view(self):
        if self._bank_source is not self.bank:
            self._bank_summary=dict(version=2,activeId=self.bank.get('activeId'),revision=self.bank.get('revision',0),trashCount=len(self.bank.get('trash',[])),entries=[dict(id=e['id'],name=e['name'],atoms=len(e['project']['atoms']),formula=c.formula(e['project'])) for e in self.bank['entries']])
            self._bank_source=self.bank
        return self._bank_summary
    def view_state(self,known=None):
        with self.lock:
            known=known or {}
            out=dict(version=c.VERSION,revision=self.revision,versions=self.versions.copy(),logs=self.logs.copy(),job=self.public_job(),undo=len(self.history),redo=len(self.future),save=self.save_status.copy())
            if known.get('project')!=self.versions['project']:out.update(project=self.project,formula=c.formula(self.project))
            if known.get('settings')!=self.versions['settings']:out['settings']=self.settings
            if known.get('bank')!=self.versions['bank']:out['bank']=self._bank_view()
            return out
    def state(self):
        # Full in-process snapshot remains available to the native/tests API.
        with self.lock:
            result=c.clone(dict(version=c.VERSION,revision=self.revision,project=self.project,bank=self.bank,settings=self.settings,formula=c.formula(self.project),logs=self.logs,job=self.public_job(),undo=len(self.history),redo=len(self.future),versions=self.versions,save=self.save_status))
            for entry in result['bank']['entries']:entry['formula']=c.formula(entry['project'])
            return result
    def public_job(self):return {k:v for k,v in self.job.items() if k not in ('cancel','thread')} if self.job else None
    def ready(self,data):
        if self._closing:raise Conflict('서버가 종료 중입니다. 다시 실행한 뒤 접속하세요.')
        if self.job and self.job['status']=='running':raise Conflict('계산이 진행 중입니다. 완료하거나 취소하세요.')
        if data.get('revision')!=self.revision:raise Conflict('다른 탭에서 작업이 변경되었습니다. 최신 상태를 불러온 뒤 다시 적용하세요.')
    def _changed(self,before):
        for key,old,new in zip(('project','bank','settings'),before,self.snapshot()):
            if old is not new:self.versions[key]+=1
    def commit(self,before,message,validate_current=True):
        self.validate_bundle(self.project,self.bank,self.settings,validate_graphs=False,validate_current=validate_current and before[0] is not self.project)
        if not self.async_save:self.persist()
        self.history.append(before);self.history=self.history[-50:];self.future=[]
        self.revision+=1;self._changed(before);self.log(message)
        if self.async_save:self._queue_save()
    def _prepare_change(self,action,data):
        if action in ('settings','favorite','contacts'):self.settings=c.clone(self.settings)
        if action in ('atom','fixed','color'):
            ids=set(int(i) for i in data.get('ids',[]))
            self.project={**self.project,'atoms':[dict(a) if a['id'] in ids else a for a in self.project['atoms']]}
            if action=='atom':self.project['metadata']=c.clone(self.project['metadata'])
        elif action in ('bond','accept_bonds'):self.project={**self.project,'bonds':[dict(b) for b in self.project['bonds']]}
        elif action=='contacts':self.project={**self.project,'metadata':c.clone(self.project['metadata'])}
        elif action not in ('settings','favorite','undo','redo','bank','import','reset'):self.project=c.clone(self.project)
        if action=='reset':self.bank={**self.bank,'activeId':None}
        if action=='bank':
            self.bank={**self.bank,'entries':[dict(e) for e in self.bank['entries']],'trash':[dict(e) for e in self.bank.get('trash',[])]}
            op=data['op']
            if op in ('store','copy'):self.project=dict(self.project)
            if op=='rename':
                for e in self.bank['entries']:
                    if e['id']==data.get('id'):e['project']=dict(e['project'])
            if op=='restore' and self.bank['trash']:self.bank['trash'][-1]['project']=dict(self.bank['trash'][-1]['project'])
    def mutate(self,action,data,compact=False):
        with self.lock:
            self.ready(data);before=self.snapshot();old_history=self.history.copy();old_future=self.future.copy();old_revision=self.revision;old_versions=self.versions.copy()
            try:
                self._prepare_change(action,data);result=self.change(action,data)
                if action not in ('undo','redo'):self.commit(before,action,validate_current=action not in ('settings','favorite','atom','fixed','color','contacts','bank'))
                else:
                    if not self.async_save:self.persist()
                    self.revision+=1;self._changed(before);self.log(action)
                    if self.async_save:self._queue_save()
                state=self.view_state(data.get('known')) if compact else self.state()
                return state if result is None else dict(state=state,result=result)
            except Exception:
                self.project,self.bank,self.settings=before
                self.history=old_history;self.future=old_future;self.revision=old_revision;self.versions=old_versions
                raise
    def change(self,action,d):
        p=self.project;ids=list(dict.fromkeys(int(i) for i in d.get('ids',[])));a=c.index_atoms(p) if ids else {}
        if not set(ids)<=set(a):raise ValueError('선택 원자가 현재 구조에 없습니다.')
        if action=='reset':self.project=c.template(int(d['n']))
        elif action=='hydroxo':
            oxy,removed=c.prepare_hydroxo(p);return dict(selection=oxy,removed=removed)
        elif action in ('undo','redo'):
            source,target=(self.history,self.future) if action=='undo' else (self.future,self.history)
            if not source:raise ValueError('되돌릴 작업이 없습니다.')
            target.append(self.snapshot());self.project,self.bank,self.settings=source.pop()
        elif action=='delete':c.delete_atoms(p,ids)
        elif action=='fixed':
            if not ids:raise ValueError('원자를 선택하세요.')
            value=not all(a[i].get('fixed') for i in ids)
            for i in ids:a[i]['fixed']=value
        elif action=='atom':
            if len(ids)!=1:raise ValueError('원자 하나를 선택하세요.')
            vals=d['values'];element=vals['element']
            if element not in c.SYMBOLS:raise ValueError('원소기호를 확인하세요.')
            update={k:float(vals[k]) for k in ('x','y','z')};update.update(element=element,charge=int(vals.get('charge',0)),isotope=int(vals.get('isotope',0)))
            if update['isotope']<0 or not all(math.isfinite(update[k]) for k in ('x','y','z')):raise ValueError('좌표/동위원소 입력 오류')
            a[ids[0]].update(update);p['metadata']['requiresChargeReview']=True
        elif action=='color':
            if not ids:raise ValueError('색상을 바꿀 원자를 선택하세요.')
            color=d['color']
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('RGB 색상 오류')
            for i in ids:a[i]['color']=color
        elif action=='settings':
            allowed=set(c.DEFAULTS)|{'favorites'}
            for k,v in d['settings'].items():
                if k in allowed:self.settings[k]=v
            c.normalize_font_preferences(self.settings)
        elif action=='contacts':
            criteria=d['criteria']
            if criteria['mode'] not in ('radii','minimum'):raise ValueError('접촉 방식 오류')
            for k,lo,hi in [('vdw',.1,2),('covalent',.5,2),('minimum',.5,6)]:
                criteria[k]=float(criteria[k])
                if not lo<=criteria[k]<=hi:raise ValueError('접촉 기준 범위 오류')
            p['metadata']['contactCriteria']=criteria;self.settings['contact']=criteria
        elif action=='bond':
            if len(ids)!=2 or ids[0]==ids[1]:raise ValueError('서로 다른 원자 ID 2개를 지정하세요.')
            if d.get('remove'):p['bonds']=[b for b in p['bonds'] if c.bond_key(b['a'],b['b'])!=c.bond_key(*ids)]
            else:
                order=float(d.get('order',1));kind=d.get('kind','covalent')
                if order not in (1.,1.5,2.,3.) or kind not in ('covalent','coordinate'):raise ValueError('결합 차수/방식 오류')
                c.add_bond(p,*ids,order,kind,'user verified')
        elif action=='accept_bonds':
            rows=c.bond_audit(p,float(d.get('scale',1.25)),float(d.get('metal_max',2.85)))
            choices={c.bond_key(*pair) for pair in d['pairs']}
            for row in rows:
                if row['status'].startswith('검토') and c.bond_key(row['a'],row['b']) in choices:c.add_bond(p,row['a'],row['b'],row['order'],row['kind'],'user accepted ASE candidate')
        elif action=='snc':
            # Reuse the native editor's pure geometry operation with a small adapter.
            from types import SimpleNamespace
            adapter=SimpleNamespace(project=p,snc_var=SimpleNamespace(get=lambda:d['length']),snapshot=lambda:None,changed=lambda:None,log=lambda s:None)
            c.NativeApp.change_sn_c(adapter)
        elif action=='favorite':
            name=d['name'].strip();smiles=d['smiles'].strip()
            if not name or c.Chem.MolFromSmiles(smiles) is None:raise ValueError('이름/SMILES를 확인하세요.')
            records=self.settings.setdefault('favorites',[])
            if d.get('remove'):records[:]=[v for v in records if v['name']!=name]
            else:
                record=dict(id=uuid.uuid4().hex,name=name,smiles=smiles,mode=d.get('mode','covalent'))
                old=next((v for v in records if v['name']==name),None)
                if old:old.update(record)
                else:records.append(record)
        elif action=='bank':
            entries=self.bank['entries'];op=d['op'];entry=next((v for v in entries if v['id']==d.get('id')),None);name=d.get('name',p['title']).strip()
            if op in ('store','copy','rename') and not 1<=len(name)<=80:raise ValueError('이름은 1–80자로 지정하세요.')
            if op in ('store','copy'):
                if op=='copy':
                    name+=' (복사)'
                    while any(v['name']==name for v in entries):name+=' 2'
                old=next((v for v in entries if v['name']==name),None)
                if len(entries)>=100 and not old:raise ValueError('보관함은 100개까지 지원합니다.')
                p['title']=name;record=dict(id=old['id'] if old else uuid.uuid4().hex,name=name,project=p)
                if old:old.update(record)
                else:entries.append(record)
                self.bank['activeId']=record['id']
            elif op=='restore':
                if not self.bank.get('trash'):raise ValueError('복원할 구조가 없습니다.')
                entry=self.bank['trash'].pop()
                while any(v['name']==entry['name'] for v in entries):entry['name']+=' (복원)'
                entry['project']['title']=entry['name'];entries.append(entry)
            elif not entry:raise ValueError('보관한 구조를 선택하세요.')
            elif op=='load':self.project=entry['project'];self.bank['activeId']=entry['id']
            elif op=='rename':
                if any(v['name']==name and v['id']!=entry['id'] for v in entries):raise ValueError('중복된 이름입니다.')
                entry['name']=name;entry['project']['title']=name
            elif op=='delete':self.bank.setdefault('trash',[]).append(entry);self.bank['trash']=self.bank['trash'][-20:];entries.remove(entry)
            else:raise ValueError('보관함 명령 오류')
            self.bank['revision']=self.bank.get('revision',0)+1
        elif action=='import':
            name=Path(d['name']).name
            if Path(name).suffix.lower() not in ('.json','.tinoxo','.html','.htm','.xyz','.mol','.sdf','.mol2','.pdb','.cif','.pqr','.gro'):raise ValueError('지원하지 않는 구조 파일 형식입니다.')
            raw=base64.b64decode(d['content'],validate=True)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/name;path.write_bytes(raw);project,bank,settings=c.read_structure(path)
            self.load_data(dict(project=project,bank=bank,settings=settings))
        else:raise ValueError('알 수 없는 편집 명령: '+action)
    def start_job(self,action,d):
        with self.lock:
            self.ready(d);base=c.clone(self.project);before=self.snapshot();rev=self.revision;cancel=threading.Event()
            self.job=dict(id=uuid.uuid4().hex,name=action,status='running',progress='계산 준비',error=None,cancel=cancel)
            job=self.job
            def progress(s):
                with self.lock:job['progress']=str(s)
            def worker():
                nonlocal base
                try:
                    ff=d.get('ff','MMFF94');fragment_cache={}
                    if action=='attach':
                        rows=d.get('plans',[])
                        if not rows:raise ValueError('리간드 계획을 추가하세요.')
                        for row in rows:
                            targets=row.get('parents',d.get('ids',[]));sid=row.get('slot_id')
                            for host in ([None] if sid else targets):
                                progress(f"{sid or host} 리간드 부착")
                                c.attach_fragment(base,row['smiles'],parent=host,slot_id=sid,mode=row.get('mode','covalent'),length=float(row['length']) if row.get('length') else None,direction=row.get('direction'),replace_h=d.get('replace_h',True),ff_choice=ff,cleanup=d.get('cleanup',True),cancel=cancel,attachment_index=row.get('attachment_index'),fragment_cache=fragment_cache)
                    elif action=='optimize':base,results=c.optimize_project(base,ff,d.get('scope','ligands'),steps=int(d.get('steps',500)),cancel=cancel,progress=progress)
                    elif action=='cleanup':c.cleanup_project(base,cancel)
                    elif action=='example':
                        base=c.template(int(d['n']))
                        for s in list(base['slots']):
                            progress(s['id']);smiles='[*:1]CCCC' if int(d['n'])==12 else '[*:1]C'
                            if s['kind']=='L':smiles='CC(=O)[O-]'
                            elif s['kind']=='P':smiles='CP(C)(=O)[O-]'
                            c.attach_fragment(base,smiles,slot_id=s['id'],ff_choice=ff,cancel=cancel,fragment_cache=fragment_cache)
                    else:raise ValueError('계산 명령 오류')
                    with self.lock:
                        if cancel.is_set():raise InterruptedError('계산을 취소했습니다.')
                        if rev!=self.revision:raise Conflict('작업 상태가 변경되어 결과를 적용하지 않았습니다.')
                        self.project=base
                        try:self.commit(before,action+' 완료')
                        except Exception:self.project,self.bank,self.settings=before;raise
                        job['status']='done';job['progress']='완료'
                except Exception as exc:
                    with self.lock:job['status']='cancelled' if cancel.is_set() else 'error';job['error']=str(exc);self.log(str(exc))
            thread=threading.Thread(target=worker,daemon=True);job['thread']=thread;thread.start()
            return self.public_job()
    def query(self,action,d):
        with self.lock:p=self.project
        if action=='ligand':return ligand_diagram(d['smiles'],d.get('kind','A'),d.get('mode','covalent'),d.get('selected'))
        if action=='gaussian':
            text,report=c.build_gaussian(p,d['options']);return dict(text=text,report=report)
        if action=='contacts':return c.clashes(p)
        if action=='bonds':return c.bond_audit(p,float(d.get('scale',1.25)),float(d.get('metal_max',2.85)))
        if action=='geometry':return c.geometry_rows(p)
        if action=='measure':
            name,value,unit=c.measurement(p,[int(i) for i in d['ids']]);return dict(name=name,value=value,unit=unit)
        if action=='resonance':
            mol=c.Chem.MolFromSmiles(d['smiles'])
            if mol is None:raise ValueError('SMILES 해석 실패')
            result=c.resonance_info(mol);result['aromatic']=sum(a.GetIsAromatic() for a in mol.GetAtoms());return result
        if action=='validate':
            messages=[]
            for s in p['slots']:
                if not s.get('ligandIds'):continue
                try:
                    mol,_,_=c.project_to_rdkit(p,s['ligandIds'],metal_dative=False,sanitize=True,cap_boundary=True)
                    messages.append(s['id']+': RDKit 원자가 검사 통과')
                except Exception as exc:messages.append(s['id']+': '+str(exc))
            return messages
        if action=='export':return self.export(d)
        raise ValueError('알 수 없는 조회 명령')
    def export(self,d,snapshot=None):
        with self.lock:p,bank,settings=snapshot or self.snapshot()
        kind=d['kind'];mime='text/plain; charset=utf-8';ext=kind
        if kind=='project':text=clean_json(dict(format='TinOxoStudio Python',version=3,appVersion=c.VERSION,project=p,bank=bank,settings=settings)).decode();ext='tinoxo.json';mime='application/json'
        elif kind=='xyz':text=c.export_xyz(p)
        elif kind=='sdf':text=c.export_sdf(p)
        elif kind=='pdb':text=c.export_pdb(p)
        elif kind=='html':text=c.portable_html(p,bank,settings)
        elif kind=='report':
            a=c.index_atoms(p);g=c.adjacency(p);text=clean_json(dict(program='TinOxoStudio '+c.VERSION,metadata=p['metadata'],clashes=c.clashes(p),metalCoordination={i:len(g[i]) for i in g if a[i]['element'] in c.METALS},sources=c.SOURCES)).decode();ext='report.json'
        elif kind=='csv':
            buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['type','atom_order','value','unit','source']);writer.writerows(c.geometry_rows(p));text=buf.getvalue()
        elif kind=='gaussian':text,_=c.build_gaussian(p,d['options']);ext='gjf'
        else:raise ValueError('내보내기 형식 오류')
        return dict(text=text,mime=mime,filename='tinoxo.'+ext)

class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,workspace,token=None):
        self.workspace=workspace;self.token=token or secrets.token_urlsafe(32)
        self.assets={};self.asset_lock=threading.Lock()
        super().__init__(address,Handler)
    def handle_error(self,request,client_address):
        if not isinstance(sys.exc_info()[1],(BrokenPipeError,ConnectionResetError)):super().handle_error(request,client_address)
    def server_close(self):
        with self.workspace.lock:
            if self.workspace.job and self.workspace.job['status']=='running':self.workspace.job['cancel'].set()
        self.workspace.close()
        super().server_close()

class Handler(BaseHTTPRequestHandler):
    server_version='TinOxo/'+c.VERSION
    protocol_version='HTTP/1.1'
    timeout=30
    def log_message(self,fmt,*args):pass # do not log tokens, molecular inputs or file paths
    def accepts_gzip(self):
        for item in self.headers.get('Accept-Encoding','').split(','):
            parts=item.strip().split(';')
            if parts[0]!='gzip':continue
            try:return all(float(v.strip()[2:])>0 for v in parts[1:] if v.strip().startswith('q='))
            except ValueError:return False
        return False
    def send(self,data,status=200,mime='application/json; charset=utf-8',etag=None,compressed=None):
        raw=data if isinstance(data,bytes) else clean_json(data)
        encoded=False
        if status!=304 and len(raw)>1024 and self.accepts_gzip() and (mime.startswith('text/') or any(t in mime for t in ('json','javascript','svg'))):
            raw=compressed if compressed is not None else gzip.compress(raw,compresslevel=1,mtime=0);encoded=True
        self.send_response(status);self.send_header('Content-Type',mime)
        if status!=304:self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-cache' if etag else 'no-store')
        if etag:self.send_header('ETag',etag)
        self.send_header('Vary','Accept-Encoding')
        if encoded:self.send_header('Content-Encoding','gzip')
        if self.close_connection:self.send_header('Connection','close')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        if status!=304:self.wfile.write(raw)
    def authorized(self):
        origin=self.headers.get('Origin')
        if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return False
        return secrets.compare_digest(self.headers.get('X-Tinoxo-Token',''),self.server.token)
    def do_GET(self):
        try:
            path=unquote(urlsplit(self.path).path)
            if path.startswith('/api/'):
                if not self.authorized():return self.send(dict(error='접속 토큰이 없습니다. 터미널에 출력된 전체 주소로 접속하세요.'),403)
                if path=='/api/state':
                    query=parse_qs(urlsplit(self.path).query)
                    known=json.loads(query.get('known',['{}'])[0])
                    if not isinstance(known,dict):raise ValueError('known must be an object')
                    return self.send(self.server.workspace.view_state(known))
                if path=='/api/job':
                    w=self.server.workspace
                    with w.lock:result=dict(job=w.public_job(),revision=w.revision,save=w.save_status.copy())
                    return self.send(result)
                if path=='/api/config':
                    w=self.server.workspace
                    return self.send(dict(version=c.VERSION,ligands=c.BUILTIN_LIGANDS,methods=c.METHODS,bases=c.BASIS_SETS,jobs=list(c.GAUSSIAN_JOBS),defaults=c.gaussian_defaults(w.project),elements=c.SYMBOLS,metals=sorted(c.METALS),colors=c.DEFAULT_ELEMENT_COLORS,radii={s:c.radius(s) for s in c.SYMBOLS},sources=c.SOURCES,exchange=c.EXCHANGE,correlation=c.CORRELATION,valid_xc=sorted(c.VALID_XC)))
                return self.send(dict(error='없는 API'),404)
            # Serve only the shipped UI/font files; never the working directory.
            if path=='/':file=ROOT/'web/index.html'
            elif path.startswith('/web/'):file=ROOT/path.lstrip('/')
            elif path.startswith('/fonts/'):file=ROOT/path.lstrip('/')
            else:return self.send(dict(error='Not found'),404)
            file=file.resolve()
            if not any(file.is_relative_to((ROOT/name).resolve()) for name in ('web','fonts')) or not file.is_file():return self.send(dict(error='Not found'),404)
            stat=file.stat();key=(stat.st_mtime_ns,stat.st_size)
            with self.server.asset_lock:
                cached=self.server.assets.get(file)
                if not cached or cached[0]!=key:
                    raw=file.read_bytes();etag='W/"'+hashlib.sha256(raw).hexdigest()+'"'
                    cached=(key,raw,gzip.compress(raw,compresslevel=1,mtime=0),etag)
                    self.server.assets[file]=cached
            _,raw,compressed,etag=cached
            if self.headers.get('If-None-Match')==etag:return self.send(b'',304,etag=etag)
            return self.send(raw,mime=mimetypes.guess_type(str(file))[0] or 'application/octet-stream',etag=etag,compressed=compressed)
        except Exception as exc:self.send(dict(error=str(exc)),400)
    def do_POST(self):
        try:
            if not self.authorized():
                self.close_connection=True;return self.send(dict(error='접속 토큰 또는 Origin 오류'),403)
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=MAX_BODY:
                self.close_connection=True;return self.send(dict(error='요청은 32 MB 이하 JSON이어야 합니다.'),413)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                self.close_connection=True;return self.send(dict(error='JSON 요청이 필요합니다.'),415)
            data=json.loads(self.rfile.read(n));path=urlsplit(self.path).path;w=self.server.workspace
            if not isinstance(data,dict) or not isinstance(data.get('known',{}),dict):raise ValueError('JSON object expected')
            if path.startswith('/api/edit/'):result=w.mutate(path.rsplit('/',1)[1],data,compact=True)
            elif path.startswith('/api/query/'):result=w.query(path.rsplit('/',1)[1],data)
            elif path.startswith('/api/task/'):result=w.start_job(path.rsplit('/',1)[1],data)
            elif path=='/api/cancel':
                with w.lock:
                    if w.job and w.job['status']=='running':w.job['cancel'].set()
                result=dict(ok=True)
            elif path=='/api/save':
                with w.lock:w.ready(data);snapshot=w.snapshot()
                out=w.export(data,snapshot);path_=Path(data['path']).expanduser()
                if path_.is_dir():raise ValueError('파일 이름을 포함한 경로를 지정하세요.')
                c.atomic_write(path_,out['text'])
                with w.lock:w.log('서버 경로에 저장: '+str(path_))
                result=dict(ok=True,path=str(path_))
            else:return self.send(dict(error='없는 API'),404)
            return self.send(result)
        except Conflict as exc:self.send(dict(error=str(exc)),409)
        except Exception as exc:self.send(dict(error=str(exc)),400)

def choose_port(value,input_fn=input,is_interactive=None):
    if value is None:
        if bool(sys.stdin and sys.stdin.isatty()) if is_interactive is None else is_interactive:
            raw=input_fn('접속 포트 [8765]: ').strip();value=int(raw) if raw else 8765
        else:value=8765
    value=int(value)
    if not 0<=value<=65535:raise ValueError('포트는 1–65535 또는 자동 선택 0을 지정하세요.')
    return value

def run(args):
    try:
        port=choose_port(args.port);w=Workspace(args.config_dir,args.project,recover=not args.fresh,async_save=True)
        server=LocalServer((args.host,port),w)
    except (ValueError,OSError) as exc:
        print('웹 서버를 시작할 수 없습니다: '+str(exc),file=sys.stderr)
        print('다른 포트 지정 예: python TinOxoStudio.py --port 8766',file=sys.stderr);return 2
    host='127.0.0.1' if args.host in ('0.0.0.0','') else args.host
    url=f'http://{host}:{server.server_port}/#token={server.token}'
    print(f'Tin Oxo Studio {c.VERSION} · Browser workspace\n{url}\n종료: Ctrl+C',flush=True)
    opener=None
    remote=bool(os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'))
    if remote:
        print(f'SSH 접속 감지: PC에서 ssh -L {server.server_port}:127.0.0.1:{server.server_port} user@server 로 포트를 전달한 뒤 PC 브라우저에서 위 주소를 여세요. X11 브라우저 전달은 사용하지 않습니다.',flush=True)
    if not args.no_browser and (not remote or getattr(args,'open_browser',False)):
        def open_browser():
            try:
                if not webbrowser.open(url,new=2):print('브라우저 자동 실행이 지원되지 않습니다. 위 주소를 브라우저에 붙여 넣으세요.',flush=True)
            except webbrowser.Error:print('위 주소를 브라우저에서 직접 열어 주세요.',flush=True)
        opener=threading.Timer(.25,open_browser);opener.daemon=True;opener.start()
    try:server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:print('\n서버를 종료합니다.')
    finally:
        if opener:opener.cancel()
        server.server_close()
        if w.save_status['state']=='error':print('자동 저장 실패: '+str(w.save_status['error']),file=sys.stderr)
    return 0

if __name__=='__main__':raise SystemExit(c.main())
