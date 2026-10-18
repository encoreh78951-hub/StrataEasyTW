"""Read-only checks for the unofficial Strata guidance application.

No GPU choice is made automatically.  Probe failure never blocks the official
installer and does not imply hardware is incompatible.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import socket
import subprocess
import urllib.request


@dataclass(frozen=True)
class GPU:
    index: int
    name: str
    memory_mib: int

    @property
    def caption(self):
        return f'GPU {self.index} · {self.name} · {self.memory_mib/1024:.1f} GiB VRAM'


def parse_nvidia_smi(output: str) -> list[GPU]:
    """Parse only requested CSV fields; identifiers are bounded integers."""
    out = []
    for line in output.splitlines():
        fields = [p.strip().strip('"') for p in line.strip().split(',')]
        if len(fields) != 3:
            continue
        try:
            idx = int(fields[0])
            mem = int(re.search(r'\d+', fields[2]).group(0))
        except (ValueError, AttributeError):
            continue
        if not 0 <= idx <= 32 or not 0 < mem <= 262144 or not fields[1]:
            continue
        out.append(GPU(idx, fields[1][:120], mem))
    return sorted({g.index: g for g in out}.values(), key=lambda g: g.index)


def get_gpus() -> list[GPU]:
    if os.name != 'nt':
        return []
    try:
        p = subprocess.run(['nvidia-smi', '--query-gpu=index,name,memory.total',
                            '--format=csv,noheader,nounits'],
                           capture_output=True, timeout=5, check=False)
        if p.returncode:
            return []
        return parse_nvidia_smi(p.stdout.decode('utf-8-sig', errors='replace'))
    except (OSError, subprocess.TimeoutExpired):
        return []


def gpu_args(choice: str, indices: set[int]) -> list[str]:
    """Whitelist CLI arguments, never passing arbitrary user text into CMD."""
    if choice == 'auto':
        return []
    if choice.startswith('gpu:'):
        idx = int(choice.split(':', 1)[1])
        if idx not in indices:
            raise ValueError('選取的 GPU 已不存在，請重新偵測顯卡。')
        return ['--gpu', str(idx)]
    if choice == 'all':
        if len(indices) < 2:
            raise ValueError('至少需要偵測到兩張 NVIDIA 顯卡才能使用多卡選項。')
        return ['--gpus', ','.join(str(i) for i in sorted(indices))]
    raise ValueError('無效的 GPU 設定；請重新選擇。')


@dataclass(frozen=True)
class InstallInfo:
    level: str  # source / partial / configured
    detail: str


def get_install_info(folder: Path) -> InstallInfo:
    """Heuristics only: never infer from files that an AI is actually running."""
    folder = Path(folder)
    if not (folder / 'START-HERE.bat').is_file():
        return InstallInfo('missing', '這個資料夾找不到 START-HERE.bat。')
    scripts = list(folder.glob('run-*.bat'))
    configs = list(folder.glob('strata-*.json'))
    if scripts or configs:
        return InstallInfo('configured', '偵測到模型啟動檔或設定檔；官方可能直接啟動，跳過首次安裝的問答。')
    if (folder / '.venv').exists() or (folder / 'engine').exists():
        return InstallInfo('partial', '偵測到部分安裝環境，但不確定是否部署完成；請看左側官方輸出。')
    return InstallInfo('source', '目前只看到原始碼資料夾；可能會進入首次安裝流程。')


@dataclass(frozen=True)
class LocalPort:
    occupied: bool
    healthy: bool
    reason: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, hdrs, newurl):
        return None


def probe_port(port: int = 8080) -> LocalPort:
    """Read-only localhost probe. A healthy port does NOT establish process ownership."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(.5)
        try:
            s.connect(('127.0.0.1', port))
        except OSError:
            return LocalPort(False, False, '8080 尚未被占用。')
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        req = urllib.request.Request(f'http://127.0.0.1:{port}/health', headers={'Accept': 'application/json'})
        with opener.open(req, timeout=1.5) as resp:
            raw = resp.read(16 * 1024)
        data = json.loads(raw)
        if isinstance(data, dict) and data.get('status') == 'ok' and data.get('loaded') is True:
            return LocalPort(True, True, '本機已有可用的 Strata 風格服務（僅依 /health 判定，未驗證程序身分）。')
    except Exception:
        pass
    return LocalPort(True, False, '8080 已被占用，但無法確認是 Strata；為避免衝突，請先處理既有服務。')
