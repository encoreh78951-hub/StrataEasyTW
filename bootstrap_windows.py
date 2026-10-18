"""Isolated source launcher; no changes to system Python or existing Strata venv."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

SUPPORTED_PYTHON={(3,10),(3,11),(3,12),(3,13)}

def interpreter_supported(version,bitness,implementation='cpython'):
    """Return whether a Python interpreter can run this source launcher."""
    return tuple(version[:2]) in SUPPORTED_PYTHON and bitness==64 and implementation=='cpython'

def main():
    if os.name!='nt':raise SystemExit('此啟動器僅支援 Windows；其他系統請使用 python app.py --demo。')
    if not interpreter_supported(sys.version_info,64 if sys.maxsize>2**32 else 32,sys.implementation.name):
        raise SystemExit('此原始碼啟動器需要 64 位元 CPython 3.10／3.11／3.12／3.13。')
    print(f'[Strata Easy TW] 使用 Python {sys.version.split()[0]} ({64 if sys.maxsize>2**32 else 32} 位元)。',flush=True)
    root=Path(__file__).resolve().parent
    build='--build' in sys.argv
    env=root/'.guide-venv'
    python=env/'Scripts'/'python.exe'
    if python.exists():
        # An old .guide-venv may point to a different/uninstalled Python.
        # Do not reuse an incompatible environment or touch Strata's .venv.
        try:
            old=subprocess.run([str(python),'-c',
                'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
                capture_output=True,text=True,timeout=15)
            valid=old.returncode==0 and old.stdout.strip()==f'{sys.version_info.major}.{sys.version_info.minor}'
        except (OSError,subprocess.TimeoutExpired):
            valid=False
        if not valid:
            raise SystemExit('導覽器的 .guide-venv 與目前 Python 版本不相容。請先關閉程式，將本專案資料夾內的 .guide-venv 改名成 .guide-venv-old，再重新開啟 RUN_WINDOWS.bat。請勿更動 Strata 或 ComfyUI 的虛擬環境。')
    else:
        venv.create(env,with_pip=True)
    req=root/('requirements-build.txt' if build else 'requirements.txt')
    digest=hashlib.sha256(req.read_bytes()+(root/'requirements.txt').read_bytes()).hexdigest()
    marker=env/('build-deps.sha256' if build else 'runtime-deps.sha256')
    if not marker.exists() or marker.read_text()!=digest:
        print('正在為導覽器安裝固定版本套件；不會修改 Strata 的環境。',flush=True)
        subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(req)],cwd=root,check=True)
        marker.write_text(digest)
    command=[str(python),str(root/('tools/build_windows.py' if build else 'app.py'))]
    if not build and '--demo' in sys.argv:command.append('--demo')
    return subprocess.call(command,cwd=root)

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,subprocess.CalledProcessError) as exc:
        print('啟動／建置失敗：',exc,file=sys.stderr);sys.exit(1)
