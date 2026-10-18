"""Capture source-test evidence. Does not install Strata or download a model."""
from datetime import datetime, timezone
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'docs'/'test-results';out.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    report={'time_utc':datetime.now(timezone.utc).isoformat(),
            'platform':platform.platform(),'python':sys.version,'checks':{},
            'windows_verified':False,'exe_built':False}
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,
                     capture_output=True,text=True,encoding='utf-8',errors='replace')
    (out/'unit-tests.txt').write_text(p.stdout+p.stderr,encoding='utf-8')
    report['checks']['unit_tests']={'ok':p.returncode==0,'exit_code':p.returncode}
    scripts=list(ROOT.rglob('*.py'))
    scripts=[p for p in scripts if not any(x in p.parts for x in ('.guide-venv','build','dist','__pycache__'))]
    for script in scripts:compile(script.read_text(encoding='utf-8'),str(script),'exec')
    report['checks']['python_syntax']={'ok':True,'files':len(scripts)}
    # Product wording check, excluding verbatim third-party legal materials.
    forbidden=''.join(chr(n) for n in (0x5c0f,0x767d))
    hits=[]
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.suffix not in ('.py','.md','.bat','.txt','.iss','.yml','.spec'):continue
        if any(part in path.parts for part in ('licenses','third_party_sources','__pycache__','build','dist','.guide-venv')):continue
        if forbidden in path.read_text(encoding='utf-8-sig'):hits.append(str(path.relative_to(ROOT)))
    report['checks']['traditional_chinese_wording']={'ok':not hits,'hits':hits}
    sys.path.insert(0,str(ROOT))
    from smoke import run_self_test
    selftest=run_self_test()
    (out/'source-self-test.json').write_text(json.dumps(selftest,ensure_ascii=False,indent=2),encoding='utf-8')
    report['checks']['source_self_test']={'ok':selftest['ok']}
    versions={}
    for name in ('Pillow','pyte','wcwidth','pywinpty'):
        try:versions[name]=metadata.version(name)
        except metadata.PackageNotFoundError:versions[name]='not installed on this platform'
    report['dependencies']=versions
    if os.name!='nt':
        build=subprocess.run([sys.executable,'tools/build_windows.py'],cwd=ROOT,capture_output=True,
                             text=True,encoding='utf-8',errors='replace')
        (out/'windows-build-attempt.txt').write_text(build.stdout+build.stderr,encoding='utf-8')
        report['windows_build']={'supported':False,'exit_code':build.returncode,
                                'reason':'Windows is required; no executable produced'}
    else:
        report['windows_build']={'supported':True,'run_separately':'BUILD_WINDOWS_EXE.bat'}
    report['duration_seconds']=round(time.monotonic()-started,3)
    report['ok']=all(c['ok'] for c in report['checks'].values())
    (out/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['ok'] else 1

if __name__=='__main__':sys.exit(main())
