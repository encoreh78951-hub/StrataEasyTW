"""Download an official immutable commit, validate ZIP, never overwrite a deployment."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from app_config import REPO, VERSION
API_COMMIT = 'https://api.github.com/repos/Niko1221/Strata/commits/main'
ARCHIVE_BASE = 'https://codeload.github.com/Niko1221/Strata/zip/'
MAX_ZIP_BYTES = 650*1024*1024
MAX_EXTRACT_BYTES = 2*1024**3
REQUIRED = ('START-HERE.bat', 'SETUP.bat', 'LICENSE', 'setup.py')
class SourceError(RuntimeError): pass
class SourceCancelled(SourceError): pass

def check_cancel(cancel):
    if cancel and cancel.is_set(): raise SourceCancelled('已取消；尚未執行官方安裝。')

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = urllib.parse.urlparse(req.full_url), urllib.parse.urlparse(newurl)
        if new.scheme != 'https' or new.hostname != old.hostname or new.port not in (None,443):
            raise SourceError('下載被重新導向至非預期網站，已停止。')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def request(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com','codeload.github.com'):
        raise SourceError('來源網址不在官方下載白名單。')
    try:
        opener = urllib.request.build_opener(SafeRedirect())
        return opener.open(urllib.request.Request(url, headers={
            'User-Agent':f'Strata-Easy-TW/{VERSION} (Unofficial)',
            'Accept':'application/vnd.github+json'}), timeout=15)
    except urllib.error.HTTPError as exc:
        if exc.code in (403,429):
            raise SourceError('GitHub 拒絕請求或達到流量限制。請稍後重試，或從官方 GitHub 下載 ZIP、解壓後選「使用既有資料夾」。') from exc
        raise SourceError(f'官方來源回傳 HTTP {exc.code}，請稍後重試。') from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SourceError(f'無法連線至 GitHub：{exc}。請檢查網路／Proxy，勿關閉 TLS 驗證。') from exc

def get_head_sha():
    with request(API_COMMIT) as response:
        raw = response.read(3_000_001)
    if len(raw)>3_000_000: raise SourceError('GitHub 回應異常過大。')
    try: data = json.loads(raw)
    except (ValueError, UnicodeError) as exc: raise SourceError('GitHub 回應不是有效 JSON。') from exc
    sha = data.get('sha','') if isinstance(data, dict) else ''
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{40}',sha):
        raise SourceError('GitHub 回應缺少有效 commit ID。')
    return sha

def validate_zip_name(name):
    if not isinstance(name,str) or not name or '\\' in name or name.startswith('/'):
        raise SourceError('不安全的 ZIP 路徑：'+repr(name))
    parts = name.rstrip('/').split('/')
    for p in parts:
        if not p or p in ('.','..') or p.rstrip(' .')!=p or any(ord(c)<32 for c in p) or re.search(r'[<>:"|?*]',p):
            raise SourceError('不安全的 Windows 檔名：'+repr(name))
        if re.fullmatch(r'(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?',p,re.I):
            raise SourceError('Windows 保留檔名：'+repr(name))
    return parts

def safe_extract(archive, stage, cancel=None, expected_root=None):
    dest = Path(stage)/'content'
    if dest.exists(): raise SourceError('暫存解壓位置已存在，拒絕覆蓋。')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if not infos or len(infos)>20000: raise SourceError('ZIP 項目數量異常。')
        names, roots, total = {}, set(), 0
        for info in infos:
            check_cancel(cancel)
            parts = validate_zip_name(info.filename)
            roots.add(parts[0])
            key = '/'.join(parts).casefold()
            if key in names: raise SourceError('ZIP 有重複／大小寫衝突的路徑。')
            names[key] = info.is_dir()
            mode = (info.external_attr>>16) & 0o170000
            if mode not in (0,0o100000,0o040000): raise SourceError('ZIP 包含連結或特殊檔案。')
            if info.flag_bits & 1: raise SourceError('不接受加密 ZIP。')
            total += info.file_size
            if total>MAX_EXTRACT_BYTES: raise SourceError('解壓縮大小超過安全上限。')
        if len(roots)!=1 or (expected_root and roots != {expected_root}):
            raise SourceError('官方 ZIP 的根目錄格式不符。')
        for key in names:
            pieces = key.split('/')
            if any(names.get('/'.join(pieces[:i])) is False for i in range(1,len(pieces))):
                raise SourceError('ZIP 檔案與資料夾路徑衝突。')
        Path(stage).mkdir(parents=True,exist_ok=True)
        if shutil.disk_usage(stage).free < total + 16*1024*1024:
            raise SourceError('磁碟不足以解壓官方程式，請釋放空間或換磁碟。')
        dest.mkdir()
        for info in infos:
            check_cancel(cancel)
            parts = validate_zip_name(info.filename)
            if len(parts)==1: continue
            out = dest.joinpath(*parts[1:])
            if info.is_dir(): out.mkdir(parents=True,exist_ok=True); continue
            out.parent.mkdir(parents=True,exist_ok=True)
            count = 0
            with z.open(info) as src, out.open('xb') as dst:
                while block := src.read(65536):
                    check_cancel(cancel)
                    count += len(block)
                    if count>info.file_size: raise SourceError('ZIP 實際大小超過宣告值。')
                    dst.write(block)
    for name in REQUIRED:
        if not (dest/name).is_file(): raise SourceError('官方原始碼缺少：'+name)
    return dest

def validate_existing(folder):
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir(): raise SourceError('請選擇解壓後的 Strata 根目錄。')
    for name in REQUIRED:
        if not (folder/name).is_file(): raise SourceError('不是完整的 Strata 根目錄，缺少 '+name)
    return folder

def download_official(parent, log, cancel):
    parent = Path(parent).expanduser().resolve()
    parent.mkdir(parents=True,exist_ok=True)
    dest = parent/'Strata-Official'
    if os.path.lexists(dest): raise SourceError('Strata-Official 已存在；請選「使用既有資料夾」或換新位置。')
    check_cancel(cancel)
    log('正在查詢官方 main 的 commit ID…')
    sha = get_head_sha()
    check_cancel(cancel)
    log('官方來源：'+REPO+'\n固定 commit：'+sha)
    with tempfile.TemporaryDirectory(prefix='.strata-tw-',dir=parent) as td:
        tmp = Path(td); archive = tmp/'source.zip'
        digest = hashlib.sha256(); count = 0; last_report = 0
        with request(ARCHIVE_BASE+sha) as response, archive.open('xb') as out:
            if urllib.parse.urlparse(response.geturl()).hostname != 'codeload.github.com':
                raise SourceError('來源主機不符。')
            while True:
                check_cancel(cancel)
                block = response.read(65536)
                if not block: break
                count += len(block)
                if count>MAX_ZIP_BYTES: raise SourceError('官方 ZIP 超過安全容量限制。')
                out.write(block); digest.update(block)
                if count-last_report>=8*1024*1024:
                    log(f'已下載官方程式 {count/1024**2:.1f} MiB'); last_report=count
        check_cancel(cancel)
        log('正在驗證路徑與解壓縮…')
        content = safe_extract(archive,tmp,cancel,expected_root='Strata-'+sha)
        record = {'upstream':REPO, 'commit':sha, 'archive_sha256':digest.hexdigest(),
                  'notice':'下載紀錄；不是作者數位簽章', 'guide_version':VERSION}
        (content/'.strata-easy-tw-source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        check_cancel(cancel)
        # Reserve the target exclusively on Windows AND POSIX. Never rename
        # over an existing empty directory. A failed commit is left for inspection.
        try: dest.mkdir()
        except FileExistsError as exc: raise SourceError('目標資料夾剛被建立，已停止以避免覆蓋。') from exc
        try:
            for item in content.iterdir(): item.rename(dest/item.name)
        except OSError as exc:
            raise SourceError(f'移入資料夾失敗，請檢查 {dest} 的部分檔案；未覆蓋其他部署：{exc}') from exc
    return dest, sha, digest.hexdigest()
