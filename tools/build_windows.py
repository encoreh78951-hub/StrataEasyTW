"""Build on Windows x64. Never label a Linux binary as a Windows executable."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_config import VERSION

def run(args):subprocess.run([str(x) for x in args],cwd=ROOT,check=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--portable-only',action='store_true');args=parser.parse_args()
    if os.name!='nt':raise SystemExit('無法建置 Windows EXE：目前不是 Windows。請使用 Windows x64 或附帶的 GitHub Actions 工作流程。')
    if sys.maxsize<2**32:raise SystemExit('請使用 64 位元 Python。')
    from collect_licenses import collect
    run([sys.executable,'-m','unittest','discover','-s','tests','-v'])
    collect()
    # LGPL component stays external and replaceable in the onedir bundle.
    third=ROOT/'build'/'third_party';third.mkdir(parents=True,exist_ok=True)
    import pyte,wcwidth
    for module in (pyte,wcwidth):
        shutil.copytree(Path(module.__file__).parent,third/module.__name__,dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    run([sys.executable,'-m','PyInstaller','--clean','--noconfirm','StrataEasyTW.spec'])
    dist=ROOT/'dist'/'StrataEasyTW';exe=dist/'StrataEasyTW.exe'
    if not exe.is_file():raise RuntimeError('PyInstaller 沒有產生 EXE。')
    run([exe,'--self-test',ROOT/'build'/'packaged-self-test.json'])
    run([exe,'--smoke-test',ROOT/'build'/'packaged-ui-test.json'])
    for name in ('packaged-self-test.json','packaged-ui-test.json'):
        if not json.loads((ROOT/'build'/name).read_text(encoding='utf-8'))['ok']:raise RuntimeError(name+' failed')
    output=ROOT/'release';output.mkdir(exist_ok=True)
    # A portable ZIP is not an installation wizard; both artifacts are distinct.
    zipfile=shutil.make_archive(str(output/f'StrataEasyTW-{VERSION}-Windows-Portable'),'zip',ROOT/'dist','StrataEasyTW')
    artifacts=[Path(zipfile)]
    if not args.portable_only:
        candidates=[shutil.which('ISCC.exe'),r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',r'C:\Program Files\Inno Setup 6\ISCC.exe']
        iscc=next((Path(p) for p in candidates if p and Path(p).is_file()),None)
        if not iscc:raise RuntimeError('可攜版已建置；缺少 Inno Setup 6.5 以上，安裝程式尚未產生。請安裝後重跑，或用 --portable-only。')
        run([iscc,ROOT/'installer'/'StrataEasyTW.iss'])
        setup=output/f'StrataEasyTW-{VERSION}-Setup.exe'
        if not setup.is_file():raise RuntimeError('沒有找到安裝程式。')
        artifacts.append(setup)
    (output/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in artifacts),encoding='utf-8')
    print('建置完成；仍需乾淨 Windows 實機端到端驗收。產物未簽章。')
if __name__=='__main__':main()
