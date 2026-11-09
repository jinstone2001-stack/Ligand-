"""Run DOM integration in a fresh workspace (requires Node and jsdom 26)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import TinOxoWeb as w

with tempfile.TemporaryDirectory(prefix='tinoxo-dom-') as directory:
    workspace=w.Workspace(directory,async_save=True)
    server=w.LocalServer(('127.0.0.1',0),workspace,'isolated-dom-test')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        result=subprocess.run(['node',str(ROOT/'tests/test_frontend.mjs')],cwd=ROOT,
            env={**os.environ,'TINOXO_TEST_URL':f'http://127.0.0.1:{server.server_port}',
                 'TINOXO_TEST_TOKEN':'isolated-dom-test'})
    finally:
        server.shutdown();server.server_close();thread.join(5);workspace.close()
    raise SystemExit(result.returncode)
