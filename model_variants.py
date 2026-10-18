"""Explicit third-party model acquisition. No files bundled or silent model substitution.

Only SC117's published, named two-shard GSQ-RCO quantisations are supported.
The model is stored beside (not inside) a dedicated official Strata checkout.
The official setup builds its own native Pack from those GGUFs via --gguf-dir.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request

REPO_ID = 'SC117/Qwen3.8-Flash-Next-GSQ-RCO-abliterated-GGUF'
CARD = 'https://huggingface.co/' + REPO_ID
TIERS = ('Q2_0', 'IQ2_XS', 'IQ3_XXS', 'IQ3_S')
# Disk figures include room for the Strata native pack and temporary files;
# approximate planning values, NOT declared weights or guaranteed limits.
DISK_GIB = {'Q2_0': 115, 'IQ2_XS': 120, 'IQ3_XXS': 130, 'IQ3_S': 145}

class ModelDownloadError(RuntimeError): pass
class ModelDownloadCancelled(ModelDownloadError): pass

def validate_tier(tier):
    if tier not in TIERS: raise ModelDownloadError('不支援的 SC117 量化類型。')
    return tier

def shard_names(tier):
    validate_tier(tier)
    return tuple(f'Qwen3.8-Flash-Next-GSQ-RCO-abliterated-{tier}-{n:05d}-of-00002.gguf'
                 for n in (1, 2))

def install_parent(base):
    """Do not share official native packs or Strata-data with stock installation."""
    return Path(base).expanduser().resolve() / 'Strata-Easy-TW-SC117'

def sc117_official_args(tier, gpu_args=()):
    validate_tier(tier)
    # Relative paths sidestep CMD percent expansion and path-quoting hazards.
    # cwd is the dedicated Strata-Official directory and both folders are its siblings.
    return ['--setup', '--family', 'qwen', '--model', tier,
            '--gguf-dir', '..\\SC117-GGUF\\' + tier,
            '--data-dir', r'..\Strata-data', *gpu_args]

def _request_json(url, *, opener=urllib.request.urlopen):
    req = urllib.request.Request(url, headers={'User-Agent': 'StrataEasyTW/1.3 (non-official)',
                                                'Accept': 'application/json'})
    with opener(req, timeout=45) as resp:
        data = resp.read(3_000_001)
    if len(data) > 3_000_000: raise ModelDownloadError('Hugging Face API 回應異常過大。')
    try: return json.loads(data)
    except (ValueError, UnicodeError) as exc: raise ModelDownloadError('Hugging Face API 回應不是有效 JSON。') from exc

def parse_tree(entries, tier):
    """Require published LFS SHA256+size for BOTH exact model shards."""
    expected = shard_names(tier)
    found = {}
    if not isinstance(entries, list): raise ModelDownloadError('模型清單格式錯誤。')
    for entry in entries:
        if not isinstance(entry, dict): continue
        name = entry.get('path')
        if name not in (f'{tier}/{n}' for n in expected): continue
        lfs = entry.get('lfs') or {}
        size = entry.get('size')
        digest = lfs.get('oid') if isinstance(lfs, dict) else None
        if not isinstance(size, int) or size < 20_000_000_000 or size > 100_000_000_000:
            raise ModelDownloadError('第三方模型檔案大小不合理，已停止下載。')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ModelDownloadError('模型來源沒有提供 LFS SHA-256，無法安全自動下載。')
        found[name] = (size, digest)
    if len(found) != 2: raise ModelDownloadError('缺少 SC117 GGUF 分片，請檢查上游是否改名。')
    return [(name, *found[name]) for name in (f'{tier}/{n}' for n in expected)]

def model_manifest(tier, *, fetch=_request_json):
    validate_tier(tier)
    info = fetch('https://huggingface.co/api/models/' + REPO_ID)
    sha = info.get('sha') if isinstance(info, dict) else None
    if not isinstance(sha,str) or not re.fullmatch(r'[0-9a-f]{40}',sha):
        raise ModelDownloadError('無法取得第三方模型的固定版本識別碼。')
    encoded = urllib.parse.quote(tier, safe='')
    tree = fetch('https://huggingface.co/api/models/' + REPO_ID + '/tree/' + sha + '/' + encoded)
    return sha, parse_tree(tree, tier)

def _cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise ModelDownloadCancelled('已取消 SC117 下載；未完成的 .part 檔保留供下次續傳。')

def _sha256(path, cancel):
    digest = hashlib.sha256()
    with Path(path).open('rb') as inp:
        while block := inp.read(4 * 1024 * 1024):
            _cancel(cancel)
            digest.update(block)
    return digest.hexdigest()

def download_one(dest, url, size, sha256, log, cancel, *, opener=urllib.request.urlopen):
    """HTTPS streaming + verified Range resume + checked LFS content hash.

    A running download writes only a .part file; never treats partial content as GGUF.
    """
    _cancel(cancel)
    dest = Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    partial = dest.with_name(dest.name + '.part')
    if dest.exists():
        if dest.stat().st_size == size and _sha256(dest,cancel) == sha256:
            log('已驗證現有檔案：' + dest.name)
            return
        raise ModelDownloadError('現有 GGUF 檔案驗證失敗；為避免覆蓋，請先檢查：' + str(dest))
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > size: raise ModelDownloadError('未完成的分片大小超過預期，請先檢查：' + str(partial))
    if offset < size:
        headers = {'User-Agent':'StrataEasyTW/1.3 (non-official)', 'Accept-Encoding':'identity'}
        if offset: headers['Range'] = f'bytes={offset}-'
        req = urllib.request.Request(url,headers=headers)
        try:
            response = opener(req, timeout=90)
        except (OSError,urllib.error.URLError) as exc:
            raise ModelDownloadError('SC117 下載連線失敗：'+str(exc)) from exc
        with response as inp:
            result = urllib.parse.urlsplit(inp.geturl())
            if result.scheme != 'https': raise ModelDownloadError('下載來源重新導向至非 HTTPS，已拒絕。')
            status = getattr(inp,'status',200)
            if offset:
                rng = inp.headers.get('Content-Range','')
                if status != 206 or not rng.startswith(f'bytes {offset}-'):
                    raise ModelDownloadError('來源不支援此分片的安全續傳；已保留 .part，請稍後重試。')
            elif status not in (200,206):
                raise ModelDownloadError(f'第三方模型來源回傳 HTTP {status}。')
            elif status == 206 and not inp.headers.get('Content-Range','').startswith('bytes 0-'):
                raise ModelDownloadError('來源回傳的起始位置不符；已停止。')
            written = offset
            last_report = offset
            with partial.open('ab' if offset else 'wb') as out:
                while True:
                    _cancel(cancel)
                    try: block = inp.read(1024 * 1024)
                    except (OSError,TimeoutError) as exc:
                        raise ModelDownloadError('下載中斷；可重新執行以續傳：'+str(exc)) from exc
                    if not block: break
                    written += len(block)
                    if written > size: raise ModelDownloadError('回應資料超過模型檔案宣告大小。')
                    out.write(block)
                    if written - last_report >= 512*1024*1024:
                        log(f'{dest.name}：{written/1e9:.1f} / {size/1e9:.1f} GB')
                        last_report = written
    if partial.stat().st_size != size:
        raise ModelDownloadError('第三方分片尚未下載完成；下次可續傳：'+ dest.name)
    log('正在核對完整 SHA-256：' + dest.name)
    if _sha256(partial,cancel) != sha256:
        raise ModelDownloadError('SC117 GGUF 的 SHA-256 不符，已保留 .part 供檢查；請勿啟動模型。')
    partial.replace(dest)
    log('驗證成功：'+dest.name)

def download_sc117(tier, base, log, cancel, *, manifest=model_manifest, downloader=download_one):
    """Return a dedicated folder containing both completely verified original shards."""
    validate_tier(tier)
    parent = install_parent(base)
    folder = parent/'SC117-GGUF'/tier
    _cancel(cancel)
    if parent.is_symlink() or folder.is_symlink():
        raise ModelDownloadError('目標不能是符號連結。')
    parent.mkdir(parents=True,exist_ok=True)
    # Disk check is advisory if an existing .part already occupies the needed room.
    required = DISK_GIB[tier]
    free = shutil.disk_usage(parent).free / (1024 ** 3)
    if free < 10:
        raise ModelDownloadError('磁碟剩餘不足 10 GiB，不適合下載大型模型。')
    log(f'SC117 {tier}：建議總預留約 {required} GiB（包含 Pack）。目前剩餘約 {free:.0f} GiB。')
    sha, entries = manifest(tier)
    folder.mkdir(parents=True,exist_ok=True)
    for name, size, digest in entries:
        _cancel(cancel)
        filename=Path(name).name
        url=f'{CARD}/resolve/{sha}/{urllib.parse.quote(name,safe="/")}'
        downloader(folder/filename,url,size,digest,log,cancel)
    record = {'repository':REPO_ID,'revision':sha,'quantization':tier,
              'files':[{'path':name,'size':size,'sha256':digest} for name,size,digest in entries],
              'license_url':CARD,'note':'third-party model; independent from original Strata weights'}
    (folder/'SC117_DOWNLOAD_RECORD.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return folder
