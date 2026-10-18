"""Strict candidate release checks; no Strata model download is attempted."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_config import VERSION

class ReleaseGateError(RuntimeError):
    pass


def verify_text_launchers():
    expected = ('RUN_WINDOWS.bat','RUN_DEMO_WINDOWS.bat',
                'RUN_DIAGNOSTIC.bat','BUILD_WINDOWS_EXE.bat','LAUNCH_WINDOWS.bat')
    for name in expected:
        b = (ROOT/name).read_bytes()
        if any(ch > 127 for ch in b):
            raise ReleaseGateError(f'{name} 不是純 ASCII，可能造成 CMD 亂碼執行')
        if b'\n' in b.replace(b'\r\n',b''):
            raise ReleaseGateError(f'{name} 的換行不是 CRLF')
        if not b'\r\n' in b:
            raise ReleaseGateError(f'{name} 缺少 Windows CRLF 換行')
    for name in expected[:4]:
        if b'LAUNCH_WINDOWS.bat' not in (ROOT/name).read_bytes():
            raise ReleaseGateError(f'{name} 沒有使用共用啟動器')
    for name in ('README_發布方式.md','README_從這裡開始.md','THIRD_PARTY_NOTICES.md',
                 'LEGAL_AND_RELEASE_CHECKLIST.md','LICENSE','installer/release-notice.txt'):
        if not (ROOT/name).is_file():raise ReleaseGateError(f'必要文件不存在：{name}')
    metadata = (ROOT/'installer/StrataEasyTW.iss').read_text(encoding='utf-8-sig')
    if f'#define AppVersion "{VERSION}"' not in metadata:
        raise ReleaseGateError('Inno Setup 版本與程式版本不一致')
    ref = os.environ.get('GITHUB_REF','')
    if ref.startswith('refs/tags/v') and ref != f'refs/tags/v{VERSION}':
        raise ReleaseGateError(f'版本 {VERSION} 與目前標籤 {ref} 不一致')
    if any(ROOT.rglob('*.gguf')):
        raise ReleaseGateError('原始碼套件不應包含 GGUF 模型權重')
    return {'ok':True,'launchers':list(expected),'version':VERSION,
            'note':'Windows BAT 靜態檢查，並非 Windows 實際執行證據'}


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def verify_binaries():
    first = verify_text_launchers()
    dist = ROOT/'release'
    setup = dist/f'StrataEasyTW-{VERSION}-Setup.exe'
    portable = dist/f'StrataEasyTW-{VERSION}-Windows-Portable.zip'
    manifest = dist/'SHA256SUMS.txt'
    source = ROOT/'deliverables'/f'Strata_Easy_TW_{VERSION}_Source.zip'
    for p in (setup,portable,manifest,source):
        if not p.is_file() or p.stat().st_size<100:
            raise ReleaseGateError('找不到發佈產物或檔案異常：'+str(p))
    hashes={}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        if not match:raise ReleaseGateError('SHA256SUMS 格式錯誤')
        hashes[match[2]]=match[1]
    for p in (setup,portable):
        sha=sha256(p)
        if hashes.get(p.name)!=sha:
            raise ReleaseGateError(f'SHA256 驗證失敗：{p.name}')
    with zipfile.ZipFile(portable) as z:
        if z.testzip() is not None:raise ReleaseGateError('可攜版 ZIP CRC 驗證失敗')
        names=z.namelist()
        if 'StrataEasyTW/StrataEasyTW.exe' not in names:
            raise ReleaseGateError('可攜版缺少 Windows EXE')
        if any(n.lower().endswith(('.gguf','.safetensors')) for n in names):
            raise ReleaseGateError('可攜版不應包含大型模型權重')
        if not any(n.endswith('THIRD_PARTY_NOTICES.md') for n in names):
            raise ReleaseGateError('可攜版缺少第三方授權說明')
    checks={}
    for name in ('packaged-self-test.json','packaged-ui-test.json'):
        p=ROOT/'build'/name
        if not p.is_file():raise ReleaseGateError('缺少 Windows EXE 測試報告：'+name)
        data=json.loads(p.read_text(encoding='utf-8'))
        if not data.get('ok'):raise ReleaseGateError(name+' 尚未通過')
        checks[name]=data
    if checks['packaged-self-test.json'].get('checks',{}).get('conpty',{}).get('ok') is not True:
        raise ReleaseGateError('真實 Windows ConPTY 測試未通過')
    if not (ROOT/'build/third-party-licenses/inventory.json').is_file():
        raise ReleaseGateError('缺少第三方授權清單')
    if not (ROOT/'docs/test-results/source-verification.json').is_file():
        raise ReleaseGateError('缺少原始碼驗證報告')
    report={**first, 'windows_ci_candidate_verified':True,
            'full_strata_model_install_verified':False,
            'tests':checks, 'artifacts':{p.name:sha256(p)
                                         for p in (setup,portable,source)},
            'notices':['未執行大型模型首次安裝','Windows 安裝程式未簽章',
                       '未驗證 SmartScreen/防毒及所有使用者硬體配置',
                       '不支援自動安裝 SC117 低拒答模型']}
    out=ROOT/'build/windows-release-check.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser()
    scope=parser.add_mutually_exclusive_group(required=True)
    scope.add_argument('--source-check', action='store_true')
    scope.add_argument('--binary-check', action='store_true')
    args=parser.parse_args()
    try:result=verify_binaries() if args.binary_check else verify_text_launchers()
    except (ReleaseGateError,OSError,zipfile.BadZipFile,ValueError) as exc:
        # Runner stderr may be cp1252; keep diagnostics printable without
        # weakening the actual release verification.
        detail = ('發佈閘門不通過：' + str(exc)).encode('ascii', 'backslashreplace').decode('ascii')
        print(detail, file=sys.stderr)
        return 1
    # Console JSON must remain encodable even if Windows uses cp1252.
    # Machine-readable reports written to files are still real UTF-8.
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
