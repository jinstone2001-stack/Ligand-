"""Run the full suite on a temporary, authenticated Xorg dummy display.

Developer-only: requires Xorg, xserver-xorg-video-dummy and xauth.
Ordinary users should use their existing SSH DISPLAY, not this runner.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
CONFIG='''Section "ServerFlags"
 Option "AutoAddDevices" "false"
 Option "AutoEnableDevices" "false"
EndSection
Section "Device"
 Identifier "Dummy"
 Driver "dummy"
 VideoRam 256000
EndSection
Section "Monitor"
 Identifier "Monitor"
 HorizSync 5.0-1000.0
 VertRefresh 5.0-200.0
 Modeline "1600x1000" 132.00 1600 1696 1856 2112 1000 1003 1009 1042
EndSection
Section "Screen"
 Identifier "Screen"
 Device "Dummy"
 Monitor "Monitor"
 DefaultDepth 24
 SubSection "Display"
  Depth 24
  Modes "1600x1000"
 EndSubSection
EndSection
'''

with tempfile.TemporaryDirectory(prefix='tinoxo-x11-') as directory:
    root=Path(directory);config=root/'xorg.conf';config.write_text(CONFIG)
    auth=root/'auth';auth.touch(mode=0o600)
    for display in range(96,196):
        try:
            with socket.socket() as probe:probe.bind(('127.0.0.1',6000+display))
            break
        except OSError:continue
    else:raise RuntimeError('No free X11 test display')
    name=f'127.0.0.1:{display}'
    subprocess.run(['xauth','-f',str(auth),'add',name,'.',os.urandom(16).hex()],check=True)
    log=(root/'output.log').open('w')
    server=subprocess.Popen(['Xorg',f':{display}','-config',str(config),'-logfile',str(root/'xorg.log'),
        '-nolisten','unix','-listen','tcp','-noreset','-auth',str(auth)],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if server.poll() is not None:raise RuntimeError((root/'output.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1',6000+display),timeout=.2):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('X11 test server startup timeout')
        env={**os.environ,'DISPLAY':name,'XAUTHORITY':str(auth)}
        command=sys.argv[1:] or [sys.executable,'-m','unittest','discover','-s','tests','-v']
        result=subprocess.run(command,cwd=ROOT,env=env)
    finally:
        server.terminate();server.wait(timeout=10);log.close()
    raise SystemExit(result.returncode)
