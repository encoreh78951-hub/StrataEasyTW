"""Collect installed distribution metadata and license files into a build.
Also ship pyte's complete original sdist and replaceable .py sources.
"""
from importlib import metadata
from pathlib import Path
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
PACKAGES=('pywinpty','Pillow','pyte','wcwidth','PyInstaller','pyinstaller-hooks-contrib',
          'altgraph','packaging','setuptools','pefile','pywin32-ctypes')

def collect():
    dest=ROOT/'build'/'third-party-licenses';dest.mkdir(parents=True,exist_ok=True)
    inventory=[]
    for name in PACKAGES:
        try:dist=metadata.distribution(name)
        except metadata.PackageNotFoundError:
            if name in ('pywinpty','Pillow','pyte','wcwidth'):raise
            continue
        files=[]
        for item in dist.files or []:
            if any(word in item.name.lower() for word in ('license','licence','copying','notice','authors')) and not str(item).endswith('.py'):
                src=Path(dist.locate_file(item))
                if src.is_file():
                    target=dest/name/Path(str(item));target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(src,target);files.append(str(target.relative_to(dest)))
        if not files:raise RuntimeError('缺少套件授權原文：'+name)
        inventory.append({'name':name,'version':dist.version,'license_files':files})
    # CPython embeds additional libraries. Include the license supplied by this interpreter.
    pylicense=Path(sys.base_prefix)/'LICENSE.txt'
    if not pylicense.is_file():raise RuntimeError('找不到 Windows Python LICENSE.txt')
    shutil.copy2(pylicense,dest/'PYTHON-LICENSE.txt')
    tcl=Path(sys.base_prefix)/'tcl'
    copied=0
    for p in tcl.rglob('*'):
        if p.is_file() and p.name.lower() in ('license.terms','license','license.txt'):
            target=dest/'tcl-tk'/p.relative_to(tcl);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target);copied+=1
    # The source release carries Tcl/Tk license. Fail if neither source exists.
    if not copied and not (ROOT/'licenses'/'TCL-TK.txt').is_file():raise RuntimeError('缺少 Tcl/Tk 授權原文')
    (dest/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    return dest
if __name__=='__main__':print(collect())
