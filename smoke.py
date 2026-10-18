"""Offline package verification, including an actual ConPTY fixture on Windows.
Never installs Strata or downloads a model. The fixture is clearly synthetic.
"""
import json
import os
from pathlib import Path
import queue
import tempfile
import time
from app_config import VERSION, resource
from guide_rules import GUIDES
from mascot import STAGE_POSES
from terminal_backend import ConPtyBackend
from terminal_screen import TerminalScreen

def conpty_fixture(timeout=20):
    events=queue.Queue();backend=ConPtyBackend(lambda k,p:events.put((k,p)))
    with tempfile.TemporaryDirectory(prefix='strata-測試 with spaces-') as td:
        folder=Path(td)
        (folder/'START-HERE.bat').write_bytes(b'@echo off\r\necho STRATA_EASY_FIXTURE_READY\r\nset /p answer=Choice: \r\necho FIXTURE_ECHO=%answer%\r\nexit /b 0\r\n')
        chunks=[];sent=False;ended=None;deadline=time.monotonic()+timeout
        try:
            backend.start(folder)
            backend.resize(28,96)
            while time.monotonic()<deadline:
                try:kind,p=events.get(timeout=.2)
                except queue.Empty:continue
                if kind=='output':
                    chunks.append(p)
                    if not sent and 'Choice:' in ''.join(chunks):backend.write('2\r');sent=True
                elif kind=='stopped':ended=p;break
            raw=''.join(chunks)
            if not sent or 'FIXTURE_ECHO=2' not in raw or ended is None or ended['code']!=0:
                raise AssertionError('ConPTY fixture 未完成互動往返：'+repr(raw[-1500:]))
            return {'ok':True,'input_roundtrip':True,'unicode_space_cwd':True,'resize':True,'exit_code':ended['code']}
        finally:
            if backend.is_alive():backend.stop()

def run_self_test():
    report={'version':VERSION,'checks':{},'ok':False}
    try:
        from PIL import Image
        with Image.open(resource('assets','xiaoxue-atlas.png')) as im:
            assert im.size==(1536,1024) and im.mode=='RGBA'
            im.verify()
        assert set(STAGE_POSES)==set(GUIDES)
        for name in ('first','existing','failure'):assert resource('demo_logs',name+'.txt').is_file()
        for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):assert resource(name).is_file()
        s=TerminalScreen();s.feed('hello\r\x1b[2Kworld');assert s.text()=='world'
        report['checks']['resources']='passed'
        report['checks']['vt']='passed'
        report['checks']['conpty']=conpty_fixture() if os.name=='nt' else {'skipped':'requires Windows'}
        report['ok']=True
    except Exception as exc:report['error']=repr(exc)
    return report
