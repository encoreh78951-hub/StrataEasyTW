"""Package verified source without caches, environments, or speculative binaries."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app_config import VERSION
EXCLUDED={'.git','.pytest_cache','.mypy_cache','.ruff_cache','.tox','__pycache__','.guide-venv','.venv','build','dist','release','deliverables'}

def main():
    proof=ROOT/'docs'/'test-results'/'source-verification.json'
    if not proof.is_file() or not json.loads(proof.read_text(encoding='utf-8'))['ok']:
        raise SystemExit('請先執行 tools/verify_source.py 並修正失敗項目。')
    files=[]
    for path in sorted(ROOT.rglob('*')):
        rel=path.relative_to(ROOT)
        if any(x in EXCLUDED for x in rel.parts) or path.suffix in ('.pyc','.pyo'):continue
        if path.is_symlink():raise RuntimeError('拒絕打包連結：'+str(rel))
        if path.is_file() and rel.as_posix()!='SOURCE_SHA256SUMS.txt':files.append(path)
    manifest=ROOT/'SOURCE_SHA256SUMS.txt'
    manifest.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files),encoding='utf-8')
    files.append(manifest)
    dest=ROOT/'deliverables';dest.mkdir(exist_ok=True)
    archive=dest/f'Strata_Easy_TW_{VERSION}_Source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,ROOT.name+'/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('封裝 CRC 驗證失敗')
        if len(z.namelist())!=len(files):raise RuntimeError('封裝檔案數不符')
        if any('.pytest_cache' in Path(name).parts for name in z.namelist()):
            raise RuntimeError('封裝夾帶測試快取')
    (dest/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,
                      'crc_verified':True,'windows_executable_included':False},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
