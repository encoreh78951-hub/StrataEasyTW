"""Unmodified START-HERE.bat inside a real Windows ConPTY.
No installer answers are generated. Each backend owns one process lifetime.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

class TerminalError(RuntimeError): pass

def build_official_command(args=None):
    args = list(args or [])
    rest = args[1:] if args and args[0] == '--setup' else args
    if rest:
        if len(rest) != 2 or rest[0] not in ('--gpu', '--gpus') or not isinstance(rest[1], str):
            raise TerminalError('不支援的 Strata 啟動參數。')
        if not re.fullmatch(r'[0-9]+(?:,[0-9]+)*', rest[1]):
            raise TerminalError('不合法的 GPU 編號。')
        values = rest[1].split(',')
        if any(int(v)>32 for v in values) or len(set(values)) != len(values):
            raise TerminalError('GPU 編號重複或超出範圍。')
        if (rest[0] == '--gpu' and len(values) != 1) or (rest[0] == '--gpus' and len(values)<2):
            raise TerminalError('GPU 編號數量與選項不符。')
    return 'cmd.exe /d /q /c call START-HERE.bat' + ''.join(' '+x for x in args)

def validate_line(value):
    if len(value)>1023 or any(ord(c)<32 or ord(c)==127 for c in value):
        raise TerminalError('請一次輸入一行（最多 1023 字元），不要貼上多行或控制字元。')
    return value + '\r'

class ConPtyBackend:
    def __init__(self, emit):
        self.emit, self.proc = emit, None
        self.thread = None
        self._lock = threading.RLock()
        self._stopping = threading.Event()
        self.dimensions = (30, 100)

    def start(self, folder, args=None):
        if os.name != 'nt':
            raise TerminalError('實際安裝需要 Windows 10 1809 以上／Windows 11；此系統可使用離線展示。')
        if sys.getwindowsversion().build < 17763:
            raise TerminalError('Windows 版本沒有 ConPTY，請更新至 Windows 10 1809 以上。')
        if self.proc is not None:
            raise TerminalError('此終端機已使用過，請建立新的安裝工作。')
        command = build_official_command(args)
        folder = Path(folder).resolve()
        if not (folder/'START-HERE.bat').is_file():
            raise TerminalError('找不到 START-HERE.bat。')
        try:
            from winpty import PtyProcess
            from winpty.enums import Backend
            # Keep user paths out of CMD text; cwd is a separate API parameter.
            # Force ConPTY rather than silently falling back to legacy WinPTY.
            executable = str(Path(os.environ['SystemRoot'])/'System32'/'cmd.exe')
            self.proc = PtyProcess.spawn([executable]+command.split()[1:], cwd=str(folder),
                dimensions=self.dimensions, backend=str(Backend.ConPTY))
        except Exception as exc:
            raise TerminalError(f'無法建立 ConPTY：{exc}。請檢查 pywinpty、Windows 版本及相依 DLL。') from exc
        self.thread = threading.Thread(target=self._reader, args=(self.proc,), daemon=True)
        self.thread.start()

    def _reader(self, proc):
        error = None
        try:
            while True:
                try: chunk = proc.read(8192)
                except EOFError: break
                if chunk: self.emit('output', chunk)
                elif not proc.isalive(): break
        except (OSError, ValueError) as exc:
            if not self._stopping.is_set(): error = str(exc)
        except Exception as exc:
            error = str(exc)
        finally:
            try: code = proc.exitstatus
            except Exception: code = None
            if error: self.emit('status', '終端機讀取異常：'+error)
            self.emit('stopped', {'code': code, 'cancelled': self._stopping.is_set(), 'error': error})
            if not proc.isalive(): self._close_handles(proc)

    def write(self, value):
        if len(value)>1024: raise TerminalError('單次輸入不能超過 1024 字元。')
        with self._lock:
            if not self.is_alive(): raise TerminalError('目前沒有可接收輸入的官方程序。')
            self.proc.write(value)

    def resize(self, rows, columns):
        self.dimensions = (max(8,min(100,rows)),max(40,min(240,columns)))
        with self._lock:
            if self.is_alive(): self.proc.setwinsize(*self.dimensions)

    def is_alive(self):
        try: return self.proc is not None and self.proc.isalive()
        except (OSError, ValueError): return False

    @staticmethod
    def _close_handles(proc):
        try: proc.close(force=True)
        except (OSError, ValueError): pass
        # pywinpty 2.0.15 marks dead children 'closed' before close() can release
        # its loopback reader sockets. Close these pinned-version handles too.
        for handle in (getattr(proc, 'fileobj', None), getattr(proc, '_server', None)):
            if handle is not None:
                try: handle.shutdown(2)
                except OSError: pass
                try: handle.close()
                except OSError: pass

    def stop(self):
        self._stopping.set()
        proc = self.proc
        if proc is None: return
        if self.is_alive():
            # Terminate only the tree rooted at this still-live owned process.
            # A single confirmed stop covers forced termination; no name-wide kill.
            try:
                taskkill = str(Path(os.environ['SystemRoot'])/'System32'/'taskkill.exe')
                result = subprocess.run([taskkill, '/PID', str(proc.pid), '/T', '/F'],
                    capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode and self.is_alive():
                    raise TerminalError('Windows 未能停止此程序樹，請查看工作管理員。')
            except Exception as exc:
                self.emit('status', '停止程序時發生問題：'+str(exc))
                raise TerminalError(str(exc)) from exc
        self._close_handles(proc)
        if self.thread and self.thread is not threading.current_thread(): self.thread.join(timeout=2)

class DemoBackend:
    """Synthetic trace replay; does not run commands, download, or probe ports."""
    def __init__(self, emit, demo_file=None, delay=.7):
        self.emit, self.demo_file, self.delay = emit, Path(demo_file) if demo_file else None, delay
        self.cancel = threading.Event()
        self.thread = None
        self.running = False

    def start(self, folder=None, args=None):
        if not self.demo_file or not self.demo_file.is_file(): raise TerminalError('缺少展示日誌。')
        self.running = True
        self.cancel.clear()
        def replay():
            try:
                self.emit('output','[離線展示 / 以下皆為模擬記錄，未啟動 Strata]\r\n')
                for part in self.demo_file.read_text(encoding='utf-8').splitlines():
                    if self.cancel.wait(self.delay): return
                    self.emit('output',part+'\r\n')
                if self.demo_file.stem != 'failure': self.emit('demo_ready', None)
            finally:
                self.running = False
                self.emit('stopped',{'code':None,'cancelled':self.cancel.is_set(),'demo':True})
        self.thread = threading.Thread(target=replay, daemon=True)
        self.thread.start()

    def write(self, value):
        if not self.running: raise TerminalError('展示已結束。')
        self.emit('system', '模擬輸入 '+repr(value)+'（未傳給任何程序）')
    def is_alive(self): return self.running
    def resize(self, rows, columns): pass
    def stop(self): self.cancel.set()
