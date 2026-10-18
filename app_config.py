"""Release metadata and resource paths shared by the UI and build tools."""
from pathlib import Path
import os
import sys
VERSION = '1.3.0-rc1'
APP_NAME = 'Strata Easy TW'
REPO = 'https://github.com/Niko1221/Strata'
CHAT_URL = 'http://127.0.0.1:8080'

def prepare_frozen_runtime():
    """Load native dependencies, then restore system DLL lookup for Strata.

    See PyInstaller 6.16 common-issues-and-pitfalls, launching external programs.
    This app has no bundled helper executable requiring the frozen DLL path.
    """
    if os.name != 'nt' or not getattr(sys, 'frozen', False):
        return
    import winpty
    import PIL._imagingtk
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
    kernel.SetDllDirectoryW.restype = ctypes.c_int
    if not kernel.SetDllDirectoryW(None):
        raise ctypes.WinError(ctypes.get_last_error())
    bundle = Path(sys._MEIPASS).resolve()
    def bundled(value):
        try: return Path(value).resolve().is_relative_to(bundle)
        except (OSError, ValueError): return False
    os.environ['PATH'] = os.pathsep.join(p for p in os.environ.get('PATH','').split(os.pathsep)
                                       if p and not bundled(p))

def resource(*parts):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)).joinpath(*parts)

# Keep LGPL pyte as replaceable Python source in frozen distributions.
if getattr(sys, 'frozen', False):
    sys.path.insert(0, str(resource('third_party')))
