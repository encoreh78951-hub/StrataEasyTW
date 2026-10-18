# PyInstaller onedir build. pyte remains editable source for LGPL replacement.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
datas = [(str(root / name), name) for name in ('assets', 'demo_logs', 'licenses', 'docs')]
datas += [(str(root / name), '.') for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'README_從這裡開始.md')]
datas += [(str(root / 'build' / 'third-party-licenses'), 'third-party-licenses'),
          (str(root / 'build' / 'third_party'), 'third_party'),
          (str(root / 'third_party_sources'), 'third_party_sources')]
win_data, win_bins, win_hidden = collect_all('winpty')
a = Analysis(['app.py'], pathex=[str(root)], binaries=win_bins,
             datas=datas+win_data, hiddenimports=win_hidden+['PIL.ImageTk'],
             excludes=['pyte', 'wcwidth'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StrataEasyTW',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StrataEasyTW')
