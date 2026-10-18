"""Thread-safe work lifecycle. Workers never touch Tk or answer installer prompts."""
from __future__ import annotations
from collections import deque
from pathlib import Path
import queue
import threading
from app_config import resource
from diagnostics import probe_port, get_install_info
from source_manager import download_official, validate_existing, SourceCancelled, check_cancel
from terminal_backend import ConPtyBackend, DemoBackend, TerminalError
from model_variants import download_sc117, install_parent, sc117_official_args, validate_tier

class SessionLog:
    def __init__(self, limit=4*1024*1024):
        self.limit, self.size, self.parts, self.truncated = limit, 0, deque(), False
    def append(self, text):
        if len(text)>self.limit: text=text[-self.limit:]; self.truncated=True
        self.parts.append(text); self.size+=len(text)
        while self.size>self.limit:
            self.size-=len(self.parts.popleft()); self.truncated=True
    def text(self):
        return ('[較早日誌已超出保留上限]\n' if self.truncated else '') + ''.join(self.parts)

class Session:
    def __init__(self, backend_factory=ConPtyBackend, downloader=download_official, probe=probe_port, model_downloader=download_sc117):
        self.backend_factory, self.downloader, self.probe = backend_factory, downloader, probe
        self.model_downloader = model_downloader
        self.events = queue.Queue(maxsize=512)
        self.generation = 0
        self.cancel = threading.Event()
        self.backend = None
        self.working = False
        self.closed = False
        self.demo = False
        self.active_dir = None
        self.source_record = None
        self._lock = threading.RLock()
        self._probing = False
        self._open_after = False

    def active(self):
        b = self.backend
        return self.working or bool(b and (b.is_alive() or (getattr(b,'thread',None) and b.thread.is_alive())))

    def emit(self, generation, kind, payload):
        while not self.closed and generation == self.generation:
            try: self.events.put((generation,kind,payload),timeout=.1); return
            except queue.Full: pass

    def drain(self, limit=40):
        events = []
        for _ in range(limit):
            try: generation,kind,payload = self.events.get_nowait()
            except queue.Empty: break
            if generation == self.generation: events.append((kind,payload))
        return events

    def _begin(self, demo=False):
        with self._lock:
            if self.active(): raise TerminalError('工作仍在執行；請先停止並等待結束。')
            self.generation += 1
            self.cancel = threading.Event()
            self.backend = None
            self.active_dir = None
            self.source_record = None
            self.demo = demo
            self.working = True
            self._probing = False
            self._open_after = False
            return self.generation

    def start(self, mode, folder, args=None, variant='standard', tier='IQ2_XS'):
        if variant not in ('standard','sc117'):
            raise TerminalError('不支援的模型版本。')
        if variant == 'sc117':
            validate_tier(tier)
            if mode != 'download':
                raise TerminalError('第三方模型僅支援新增獨立安裝；請選「從官方 GitHub 下載」。')
        generation = self._begin()
        cancel = self.cancel
        emit = lambda kind,payload: self.emit(generation,kind,payload)
        def worker():
            try:
                launch_args = list(args or [])
                if mode == 'download':
                    emit('stage','source')
                    parent = install_parent(folder) if variant == 'sc117' else Path(folder)
                    previous = parent / 'Strata-Official'
                    if variant == 'sc117' and previous.exists():
                        folder2 = validate_existing(previous)
                        if not (folder2/'.strata-easy-tw-source.json').is_file():
                            raise TerminalError('此位置已有不是本工具下載的 Strata，為安全起見不覆蓋。')
                        emit('system','沿用上次未完成的 SC117 專用官方程式資料夾。')
                    else:
                        folder2,sha,digest = self.downloader(parent,lambda text:emit('system',text),cancel)
                        self.source_record = {'commit':sha,'sha256':digest}
                elif mode == 'existing': folder2=validate_existing(Path(folder))
                else: raise TerminalError('未知的安裝來源。')
                check_cancel(cancel)
                if variant == 'sc117':
                    preflight=self.probe()
                    check_cancel(cancel)
                    if preflight.occupied:
                        emit('stage','already_running' if preflight.healthy else 'port_busy')
                        emit('status',preflight.reason)
                        return
                    emit('stage','sc117_download')
                    emit('system',f'第三方 SC117 {tier}：僅從 Hugging Face 原作者倉庫下載並驗證 GGUF，不會使用官方模型的既有 Pack。')
                    self.model_downloader(tier,folder,lambda msg:emit('system',msg),cancel)
                    check_cancel(cancel)
                    emit('stage','sc117_prepare')
                    launch_args = sc117_official_args(tier,launch_args)
                    emit('system','使用獨立的 Strata-data 與 SC117-GGUF；官方 START-HERE.bat 將依 --gguf-dir 重建 Pack。')
                self.active_dir=folder2
                info=get_install_info(folder2)
                emit('install_info',info.detail)
                port=self.probe()
                check_cancel(cancel)
                if port.occupied:
                    emit('stage','already_running' if port.healthy else 'port_busy')
                    emit('status',port.reason)
                    return
                emit('stage','sc117_prepare' if variant == 'sc117' else ('existing' if info.level=='configured' else 'startup'))
                emit('system','啟動未修改的 START-HERE.bat：'+str(folder2))
                # Cancellation and process handoff share a lock. No process may
                # start after stop() has acquired it and set this event.
                with self._lock:
                    check_cancel(cancel)
                    self.backend=self.backend_factory(emit)
                    self.backend.start(folder2,args=launch_args)
                emit('running',None)
            except SourceCancelled as exc:
                emit('stage','cancelled'); emit('status',str(exc))
            except Exception as exc:
                if cancel.is_set():
                    emit('stage','cancelled'); emit('status','工作已取消。')
                else: emit('error',str(exc))
            finally:
                with self._lock: self.working=False
                emit('idle',None)
        threading.Thread(target=worker,daemon=True).start()

    def start_demo(self, kind='first', delay=.7):
        if kind not in ('first','existing','failure'): raise TerminalError('未知的展示流程。')
        generation=self._begin(demo=True)
        try:
            self.backend=DemoBackend(lambda k,p:self.emit(generation,k,p),resource('demo_logs',kind+'.txt'),delay)
            self.backend.start()
        finally: self.working=False

    def write(self, value):
        if not self.backend: raise TerminalError('目前沒有可接收輸入的程序。')
        self.backend.write(value)

    def stop(self):
        # Fast caller; long process termination is handled in a worker.
        generation=self.generation
        self.cancel.set()
        def worker():
            try:
                with self._lock:
                    self.cancel.set()
                    backend=self.backend
                if backend: backend.stop()
            except Exception as exc: self.emit(generation,'error',str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def resize(self, rows, columns):
        if self.backend:
            try: self.backend.resize(rows,columns)
            except (OSError,ValueError): pass

    def probe_async(self, open_after=False):
        if self.demo: return
        with self._lock:
            self._open_after=self._open_after or open_after
            if self._probing: return
            self._probing=True
            generation=self.generation
        def worker():
            try: result=self.probe()
            except Exception as exc:
                from diagnostics import LocalPort
                result=LocalPort(False,False,'健康檢查失敗：'+str(exc))
            with self._lock:
                if generation!=self.generation: return
                requested=self._open_after
                self._open_after=False; self._probing=False
            self.emit(generation,'health',{'result':result,'open_after':requested})
        threading.Thread(target=worker,daemon=True).start()
