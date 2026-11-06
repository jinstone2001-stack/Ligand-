#!/usr/bin/env python3
"""Compare checked-out 4.1 with this release. Use isolated temporary workspaces.

python benchmarks/benchmark_web.py /path/to/4.1 --output benchmarks/web_20261106.json --viewer-input /tmp/tinoxo-viewer.json
"""
import argparse
import gc
import gzip
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import TinOxoStudio as current_c
import TinOxoWeb as current_w


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod


def copies(c,project,count):
    out=c.clone(project);out['atoms']=[];out['bonds']=[];out['slots']=[]
    for k in range(count):
        offset=k*10000
        for a in project['atoms']:out['atoms'].append({**a,'id':a['id']+offset,'x':a['x']+(k%4)*15,'y':a['y']+(k//4)*15})
        for b in project['bonds']:out['bonds'].append({**b,'a':b['a']+offset,'b':b['b']+offset})
    return out


def measure(c,w,project,version):
    result={'version':version,'engine':[],'edits':[]};last=None
    # Warm SciPy/RDKit once; all compared cases use deterministic RDKit seeds.
    c.attach_fragment(c.template(12),'[*:1]C',parent=1,cleanup=False)
    for smiles in ('[*:1]CCCCCC','c1ccccc1'):
        gc.collect();samples=[];cpu=[]
        for _ in range(5):
            p=c.template(12);start=time.perf_counter();cpu_start=time.process_time();c.attach_fragment(p,smiles,parent=1,cleanup=True);samples.append((time.perf_counter()-start)*1000);cpu.append((time.process_time()-cpu_start)*1000)
        result['engine'].append({'action':'attach','smiles':smiles,'median_cpu_ms':round(statistics.median(cpu),3),'median_ms':round(statistics.median(samples),3),'samples_ms':[round(t,3) for t in samples]})
        if smiles=='[*:1]CCCCCC':last=np.array([c.xyz(a) for a in p['atoms']])
    p=c.clone(project);samples=[];cpu=[]
    for _ in range(5):
        pp=c.clone(p);start=time.perf_counter();cpu_start=time.process_time();c.cleanup_project(pp);samples.append((time.perf_counter()-start)*1000);cpu.append((time.process_time()-cpu_start)*1000)
    result['engine'].append({'action':'cleanup_86_atoms','median_cpu_ms':round(statistics.median(cpu),3),'median_ms':round(statistics.median(samples),3),'samples_ms':[round(t,3) for t in samples]})
    pp=copies(c,project,8);samples=[];cpu=[]
    for _ in range(5):
        start=time.perf_counter();cpu_start=time.process_time();rows=c.geometry_rows(pp);samples.append((time.perf_counter()-start)*1000);cpu.append((time.process_time()-cpu_start)*1000)
    result['engine'].append({'action':'geometry_688_atoms','rows':len(rows),'median_cpu_ms':round(statistics.median(cpu),3),'median_ms':round(statistics.median(samples),3),'samples_ms':[round(t,3) for t in samples]})
    for n,bank_count in ((1,0),(1,20),(1,100),(8,20)):
        with tempfile.TemporaryDirectory() as directory:
            kwargs={'async_save':True} if version=='after' else {}
            ws=w.Workspace(directory,recover=False,**kwargs);ws.project=copies(c,project,n)
            ws.bank['entries']=[{'id':str(k),'name':f'Structure {k}','project':c.clone(ws.project)} for k in range(bank_count)]
            if version=='after':ws.view_state() # build initial summaries, as at first connection
            gc.collect();samples=[];sizes=[];cpu=[]
            for i in range(5):
                data={'revision':ws.revision,'ids':[1],'color':f'#{i:06x}'}
                if version=='after':data['known']=ws.versions.copy()
                start=time.perf_counter();cpu_start=time.process_time()
                out=ws.mutate('color',data,compact=True) if version=='after' else ws.mutate('color',data)
                raw=w.clean_json(out);samples.append((time.perf_counter()-start)*1000);cpu.append((time.process_time()-cpu_start)*1000);sizes.append(len(raw))
            result['edits'].append({'atoms':len(ws.project['atoms']),'bank_entries':bank_count,'median_cpu_ms':round(statistics.median(cpu),3),'median_ms':round(statistics.median(samples),3),'samples_ms':[round(t,3) for t in samples],'response_bytes':sizes[-1],'gzip_bytes':len(gzip.compress(raw,compresslevel=1,mtime=0))})
            if version=='after':ws.close()
    return result,last


def main():
    ap=argparse.ArgumentParser();ap.add_argument('baseline',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--viewer-input',type=Path);args=ap.parse_args()
    bc=module('baseline_studio',args.baseline/'TinOxoStudio.py');bw=module('baseline_web',args.baseline/'TinOxoWeb.py');bw.c=bc
    project=json.loads((ROOT/'examples/Sn12_Methyl.tinoxo.json').read_text())['project']
    before,ba=measure(bc,bw,project,'before');after,aa=measure(current_c,current_w,project,'after')
    report={'baseline_commit':'2b73badafbf938be0dcc5f8d236531c084ba3405','version':current_c.VERSION,'python':sys.version.split()[0],'note':'Local wall-clock CPU/API work. Edit timing includes serialization, old synchronous persistence and new queued background save. Not browser or network timing. 5 samples per case after warmup.','max_attachment_coordinate_difference_A':float(np.max(np.abs(ba-aa))),'results':[before,after]}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.viewer_input:args.viewer_input.write_text(json.dumps({'project':project,'settings':current_c.DEFAULTS,'colors':current_c.DEFAULT_ELEMENT_COLORS,'radii':{s:current_c.radius(s) for s in current_c.SYMBOLS}}))
    for r in (before,after):print(json.dumps(r))
    print('Max attachment coordinate difference (A):',report['max_attachment_coordinate_difference_A'])


if __name__=='__main__':main()
