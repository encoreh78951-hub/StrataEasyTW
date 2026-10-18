"""Read-only resource hints; never claims guaranteed compatibility."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os, shutil, ctypes, re

@dataclass(frozen=True)
class Resources:
    ram_gib: float | None
    disk_free_gib: float | None
    suggested: str
    warning: str


def system_ram_gib() -> float | None:
    if os.name=='nt':
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
        s=MEMORYSTATUSEX();s.dwLength=ctypes.sizeof(s)
        return round(s.ullTotalPhys/(1024**3),1) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)) else None
    try:
        with open('/proc/meminfo',encoding='ascii') as f:
            match=re.search(r'^MemTotal:\s*(\d+)\s+kB',f.read(),re.M)
        return round(int(match.group(1))*1024/(1024**3),1) if match else None
    except (OSError,ValueError):return None


def get_resources(folder: Path) -> Resources:
    ram=system_ram_gib()
    try:
        ancestor=folder.expanduser()
        while not ancestor.exists() and ancestor!=ancestor.parent:
            ancestor=ancestor.parent
        free=round(shutil.disk_usage(ancestor).free/(1024**3),1)
    except (OSError,ValueError):free=None
    if ram is None:
        suggested='請以 Strata 官方硬體判斷為準'
        warn='無法讀取 RAM 容量。'
    elif ram<48:
        suggested='資源較緊：先閱讀官方最低需求'
        warn='這類 125B 模型可能需要大量 RAM／VRAM，請勿強行選高精度量化。'
    elif ram<64:
        suggested='優先比較 Q2_0 / IQ2_XS'
        warn='仍需考慮 GPU、Context 及其他程式的記憶體。'
    elif ram<96:
        suggested='先比較 IQ2_XS / IQ3_XXS'
        warn='IQ3_S 可能壓縮你的剩餘 RAM，尤其同時跑圖片生成時。'
    else:
        suggested='可評估 IQ3_S，仍須遵循官方提示'
        warn='量化越高仍不代表速度越快；GPU 和磁碟也會影響體驗。'
    if free is not None and free<100:
        warn+=' 當前磁碟剩餘空間偏少，官方模型、Pack、暫存檔可能需要超過 100GiB。'
    return Resources(ram,free,suggested,warn)
