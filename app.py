"""Strata Easy TW — unofficial Traditional Chinese Windows installation guide."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback
import webbrowser
from app_config import VERSION, APP_NAME, CHAT_URL, REPO, resource, prepare_frozen_runtime
from beginner_help import HINTS, GLOSSARY, explain_excerpt
from diagnostics import get_gpus, gpu_args
from guide_rules import GUIDES, StageTracker
from hardware_advice import get_resources
from mascot import Mascot, TIPS
from session import Session, SessionLog
from terminal_backend import TerminalError, validate_line
from terminal_screen import TerminalScreen
from ui_widgets import C, label, button, ScrollPanel, TerminalView

class App:
    def __init__(self,root,demo=False,autoplay=True,session=None):
        self.root,self.demo=root,demo
        self.session=session or Session()
        self.screen=TerminalScreen(reply=self._terminal_reply)
        self.guide=StageTracker(); self.log=SessionLog()
        self.stage='welcome'; self.dirty=True; self.closing=False;self.resize_job=None
        self.health_at=0; self.last_output=0; self.gpus=[]; self.gpu_keys={}
        self.mode=tk.StringVar(value='download')
        self.path=tk.StringVar(value=str(Path.home()/'Strata-AI'))
        self.accept=tk.BooleanVar();self.setup_again=tk.BooleanVar();self.reduced=tk.BooleanVar()
        self.choice=tk.StringVar();self.entry=tk.StringVar();self.demo_kind=tk.StringVar(value='first')
        self.settings_open=True
        root.title(f'{APP_NAME} · {VERSION} · 非官方繁體中文導覽')
        root.configure(bg=C['bg'])
        sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
        root.geometry(f'{min(1420,sw-50)}x{min(940,sh-70)}')
        root.minsize(1100,680)
        root.protocol('WM_DELETE_WINDOW',self._close)
        self._draw()
        self._stage('welcome')
        self._status('離線展示 · 不下載、不啟動官方程序' if demo else '選擇安裝來源，準備開始。')
        if not demo:self._refresh_gpus()
        self.poll_job=root.after(70,self._poll)
        if demo and autoplay:root.after(300,self._demo_start)

    def _draw(self):
        style=ttk.Style(self.root); style.theme_use('clam')
        style.configure('TCombobox',fieldbackground=C['panel'],background=C['panel'],foreground=C['text'],arrowcolor=C['cyan'])
        style.map('TCombobox',fieldbackground=[('readonly',C['panel'])],foreground=[('readonly',C['text'])])
        header=tk.Frame(self.root,bg=C['bg'],padx=22,pady=14);header.pack(fill='x')
        brand=tk.Frame(header,bg=C['bg']);brand.pack(side='left')
        label(brand,'STRATA / EASY TW',color='cyan',size=10,bold=True).pack(anchor='w')
        label(brand,'讓本地 AI，從第一步就看得懂。',size=22,bold=True).pack(anchor='w',pady=(3,0))
        label(brand,'保留官方安裝流程  ·  繁體中文即時解說  ·  小雪陪你完成',color='muted',size=10).pack(anchor='w',pady=(4,0))
        nav=tk.Frame(header,bg=C['bg']);nav.pack(side='right')
        label(nav,f'v{VERSION}  /  非官方',color='pink',size=10,bold=True).pack(anchor='e',pady=(0,8))
        links=tk.Frame(nav,bg=C['bg']);links.pack()
        button(links,'快速上手',self._show_quickstart).pack(side='left',padx=3)
        button(links,'說明與授權',self._about).pack(side='left',padx=3)
        self.settings_btn=button(links,'收合設定',self._toggle_settings);self.settings_btn.pack(side='left',padx=3)
        neon=tk.Frame(self.root,height=2,bg=C['purple']);neon.pack(fill='x',padx=22)
        tk.Frame(neon,bg=C['cyan']).place(relwidth=.48,relheight=1)
        tk.Frame(neon,bg=C['pink']).place(relx=.8,relwidth=.2,relheight=1)
        steps=tk.Frame(self.root,bg=C['bg'],padx=22,pady=10);steps.pack(fill='x')
        self.step_chips=[]
        for i,text in enumerate(('01  取得官方程式','02  選擇與設定','03  下載與部署','04  開啟聊天')):
            w=label(steps,text,color='muted',size=10,bold=True,padx=12,pady=5)
            w.pack(side='left',padx=(0,7));self.step_chips.append(w)
        label(steps,'離線展示' if self.demo else 'Windows 安裝導覽',color='green',bold=True).pack(side='right')
        self.setup_frame=tk.Frame(self.root,bg=C['surface'],padx=16,pady=12,
            highlightbackground=C['border'],highlightthickness=1)
        self.setup_frame.pack(fill='x',padx=22,pady=(0,12))
        f=self.setup_frame
        source=tk.Frame(f,bg=C['surface']);source.pack(fill='x')
        label(source,'安裝來源',bold=True).pack(side='left',padx=(0,15))
        for key,title in [('download','從官方 GitHub 下載'),('existing','使用既有資料夾')]:
            tk.Radiobutton(source,text=title,variable=self.mode,value=key,bg=C['surface'],
                fg=C['text'],selectcolor=C['panel'],activebackground=C['surface'],activeforeground=C['cyan'],
                font=('Microsoft JhengHei UI',10)).pack(side='left',padx=(0,14))
        button(source,'官方專案 ↗',lambda:webbrowser.open(REPO)).pack(side='right')
        row=tk.Frame(f,bg=C['surface']);row.pack(fill='x',pady=8)
        label(row,'安裝位置',bold=True).pack(side='left',padx=(0,15))
        tk.Entry(row,textvariable=self.path,bg=C['bg'],fg=C['text'],insertbackground=C['cyan'],relief='flat',font=('Microsoft JhengHei UI',10)).pack(side='left',fill='x',expand=True,ipady=8)
        button(row,'瀏覽…',self._browse).pack(side='left',padx=(8,0))
        button(row,'硬體資訊',self._show_hardware).pack(side='left',padx=(8,0))
        gpu=tk.Frame(f,bg=C['surface']);gpu.pack(fill='x')
        label(gpu,'顯卡設定',bold=True).pack(side='left',padx=(0,15))
        self.gpu_box=ttk.Combobox(gpu,state='readonly',textvariable=self.choice,width=47,font=('Microsoft JhengHei UI',10))
        self.gpu_box.pack(side='left');self._gpu_choices()
        button(gpu,'重新偵測',self._refresh_gpus).pack(side='left',padx=8)
        self._check(gpu,'重新設定既有模型（--setup）',self.setup_again).pack(side='left')
        bottom=tk.Frame(f,bg=C['surface']);bottom.pack(fill='x',pady=(8,0))
        self._check(bottom,'我已了解非官方身分，並閱讀原始專案與模型授權。',self.accept).pack(side='left')
        button(bottom,'查看授權',self._about).pack(side='left',padx=8)
        self.start_btn=button(bottom,'開始官方安裝  →',self._start,primary=True);self.start_btn.pack(side='right')
        if self.demo:
            for w in (self.start_btn,):w.configure(text='重播展示',command=self._demo_start)
            self.accept.set(True)
        # Footer first, so controls stay visible at smaller heights.
        foot=tk.Frame(self.root,bg=C['bg'],padx=22,pady=9);foot.pack(side='bottom',fill='x')
        self.status_label=label(foot,'',color='muted',anchor='w',wraplength=570);self.status_label.pack(side='left',fill='x',expand=True)
        self.stop_btn=button(foot,'停止工作',self._stop);self.stop_btn.pack(side='right',padx=(8,0))
        button(foot,'檢查並開啟聊天 ↗',self._open_chat,primary=True).pack(side='right',padx=8)
        button(foot,'匯出日誌',self._export_log).pack(side='right')
        self.body=tk.PanedWindow(self.root,bg=C['bg'],sashwidth=10,bd=0,orient='horizontal')
        self.body.pack(fill='both',expand=True,padx=22,pady=(0,4))
        left=tk.Frame(self.body,bg=C['surface'],highlightthickness=1,highlightbackground=C['border'])
        right=tk.Frame(self.body,bg=C['surface'],highlightthickness=1,highlightbackground=C['border'])
        self.body.add(left,minsize=580,stretch='always');self.body.add(right,minsize=430,stretch='never')
        self.root.after(150,lambda:self.body.sash_place(0,int(self.body.winfo_width()*.59),0))
        lh=tk.Frame(left,bg=C['panel'],padx=14,pady=10);lh.pack(fill='x')
        label(lh,'01 / 官方終端機',size=12,bold=True).pack(side='left')
        self.live_label=label(lh,'●  尚未啟動',color='muted',size=9);self.live_label.pack(side='right')
        self.terminal=TerminalView(left,self._terminal_key,self._schedule_resize)
        self.terminal.pack(fill='both',expand=True,padx=10,pady=(10,0))
        self.term=self.terminal.text
        controls=tk.Frame(left,bg=C['surface'],padx=13,pady=10);controls.pack(fill='x')
        label(controls,'依官方問題輸入選項；只有官方顯示預設值時，才用 Enter 接受。',color='muted',size=9).pack(anchor='w',pady=(0,7))
        line=tk.Frame(controls,bg=C['surface']);line.pack(fill='x')
        label(line,'›',color='cyan',size=16).pack(side='left',padx=(0,9))
        self.input=tk.Entry(line,textvariable=self.entry,bg=C['bg'],fg=C['text'],
            insertbackground=C['cyan'],font=('Microsoft JhengHei UI',11),relief='flat')
        self.input.pack(side='left',fill='x',expand=True,ipady=8)
        self.input.bind('<Return>',lambda _:self._send_line())
        button(line,'送出 ↵',self._send_line,primary=True).pack(side='left',padx=8)
        button(line,'按 Enter',lambda:self._write('\r')).pack(side='left')
        toolsrow=tk.Frame(controls,bg=C['surface']);toolsrow.pack(fill='x',pady=(7,0))
        button(toolsrow,'複製畫面',self._copy).pack(side='right')
        button(toolsrow,'傳送 Ctrl+C',self._interrupt).pack(side='right',padx=7)
        if self.demo:
            self.demo_box=ttk.Combobox(toolsrow,state='readonly',values=['首次安裝','既有部署','下載失敗'],width=12)
            self.demo_box.current(0);self.demo_box.pack(side='left')
            self.demo_box.bind('<<ComboboxSelected>>',self._demo_change)
        rh=tk.Frame(right,bg=C['panel'],padx=17,pady=10);rh.pack(fill='x')
        label(rh,'02 / 小雪即時導覽',size=12,bold=True).pack(side='left')
        self._check(rh,'減少動態',self.reduced,self._motion).pack(side='right')
        self.rail=ScrollPanel(right);self.rail.pack(fill='both',expand=True)
        r=self.rail.body
        card=tk.Frame(r,bg=C['panel']);card.pack(fill='x',pady=(0,15))
        self.mascot=Mascot(card,C['panel'],156);self.mascot.pack(side='left')
        bubble=tk.Frame(card,bg=C['panel'],padx=10,pady=14);bubble.pack(side='left',fill='both',expand=True)
        label(bubble,'小雪',color='pink',size=17,bold=True).pack(anchor='w')
        label(bubble,'你的安裝嚮導',color='muted',size=9).pack(anchor='w',pady=(1,7))
        self.mascot_hint=label(bubble,'',size=10,justify='left',wraplength=220);self.mascot_hint.pack(fill='x')
        self.rail.wraps.append((self.mascot_hint,232))
        self.stage_badge=self.rail.text('等待開始',color='cyan',size=9,bold=True)
        self.title_label=self.rail.text('',size=18,bold=True,gap=10)
        self.body_label=self.rail.text('',color='muted',gap=15)
        tk.Frame(r,height=1,bg=C['border']).pack(fill='x',pady=(0,12))
        self.rail.text('現在該做什麼',color='green',size=11,bold=True)
        self.action_label=self.rail.text('',gap=14)
        self.rail.text('預期等待',color='purple',bold=True)
        self.wait_label=self.rail.text('',color='muted',gap=14)
        self.rail.text('這一步的意思',color='purple',bold=True)
        self.detail_label=self.rail.text('',color='muted',gap=14)
        self.rail.text('初次使用者提醒',color='warning',bold=True)
        self.caution_label=self.rail.text('',color='warning',gap=16)
        tk.Frame(r,height=1,bg=C['border']).pack(fill='x',pady=(0,12))
        self.rail.text('最新原文與對照說明',color='cyan',size=11,bold=True)
        self.raw_label=self.rail.text('等待官方輸出…',color='muted',size=9)
        self.excerpt_label=self.rail.text('右側為階段解說；未辨識的內容以官方原文為準。',gap=14)
        self.install_label=self.rail.text('',color='muted',size=9)
        button(r,'模型量化怎麼選？',self._show_models).pack(fill='x',pady=4)
        button(r,'英文名詞與常見問題',self._show_faq).pack(fill='x',pady=4)

    def _check(self,parent,text,var,command=None):
        return tk.Checkbutton(parent,text=text,variable=var,command=command,bg=parent.cget('bg'),fg=C['muted'],
            selectcolor=C['panel'],activebackground=parent.cget('bg'),activeforeground=C['text'],font=('Microsoft JhengHei UI',9))
    def _motion(self):self.mascot.motion=not self.reduced.get()
    def _toggle_settings(self):
        self.settings_open=not self.settings_open
        if self.settings_open:self.setup_frame.pack(fill='x',padx=22,pady=(0,12),before=self.body)
        else:self.setup_frame.pack_forget()
        self.settings_btn.configure(text='收合設定' if self.settings_open else '安裝設定')
    def _browse(self):
        p=filedialog.askdirectory(parent=self.root,title='選擇安裝位置或 Strata 根目錄')
        if p:self.path.set(p)
    def _gpu_choices(self):
        self.gpu_keys={'官方自動選擇／沿用舊設定（建議）':'auto'}
        self.gpu_keys.update({g.caption:f'gpu:{g.index}' for g in self.gpus})
        if len(self.gpus)>1:self.gpu_keys['使用所有 NVIDIA 顯卡（進階）']='all'
        self.gpu_box.configure(values=list(self.gpu_keys));self.choice.set(next(iter(self.gpu_keys)))
    def _refresh_gpus(self):
        if self.demo:self._status('離線展示不偵測顯卡。');return
        generation=self.session.generation
        threading.Thread(target=lambda:self.session.emit(generation,'gpus',get_gpus()),daemon=True).start()
    def _reset(self):
        self.screen=TerminalScreen(reply=self._terminal_reply);self.guide=StageTracker();self.log=SessionLog()
        self.dirty=True;self.entry.set('');self.health_at=0;self._stage('welcome')
    def _start(self):
        if self.session.active():self._status('工作仍在執行，請先停止並等待。');return
        if os.name!='nt':messagebox.showinfo('需要 Windows','實際安裝需要 Windows 10 1809 以上／Windows 11。此系統可用 --demo。',parent=self.root);return
        if not self.accept.get():messagebox.showinfo('確認來源','請閱讀原始專案與模型授權，並勾選非官方聲明。',parent=self.root);return
        path=self.path.get().strip()
        if not path:self._status('請先選擇安裝位置。');return
        try:args=gpu_args(self.gpu_keys[self.choice.get()],{g.index for g in self.gpus})
        except (ValueError,KeyError) as exc:self._error(str(exc));return
        if self.setup_again.get():args.insert(0,'--setup')
        if self.mode.get()=='existing' and args:
            if not messagebox.askyesno('將更改既有設定','指定 GPU 或 --setup 可能更動既有部署。確定繼續？',parent=self.root):return
        self._reset();self._status('正在準備安裝工作…')
        try:self.session.start(self.mode.get(),path,args)
        except Exception as exc:self._error(str(exc))
    def _demo_start(self):
        if self.session.active():self._status('請先停止目前展示，再重播。');return
        self._reset();self._stage('startup')
        self.session.start_demo(self.demo_kind.get());self._status('離線展示：所有輸出皆為模擬，不會安裝。')
    def _demo_change(self,e=None):
        self.demo_kind.set(('first','existing','failure')[self.demo_box.current()])
        self.session.stop()
        def wait_end():
            if self.session.active():self.root.after(70,wait_end)
            else:self._demo_start()
        self.root.after(70,wait_end)
    def _stage(self,code):
        g=GUIDES[code];h=HINTS[code];self.stage=code;self.guide.set(code)
        self.stage_badge.configure(text='離線展示 · 模擬階段' if self.demo else '依官方輸出辨識 · 非逐句翻譯')
        self.title_label.configure(text=g.title);self.body_label.configure(text=g.body)
        self.action_label.configure(text=h.action);self.wait_label.configure(text=h.wait)
        self.detail_label.configure(text=h.detail);self.caution_label.configure(text=h.caution)
        self.mascot.set_stage(code);self.mascot_hint.configure(text=TIPS[code])
        step=0 if g.progress<20 else 1 if g.progress<53 else 2 if g.progress<95 else 3
        for i,w in enumerate(self.step_chips):w.configure(fg=C['cyan'] if i==step else C['muted'],bg=C['panel'] if i==step else C['bg'])
    def _status(self,text):self.status_label.configure(text=text[:180])
    def _system(self,text):
        self.log.append('\n[導覽器] '+text+'\n');self._status(text)
    def _error(self,text):
        self._stage('error');self._system(text)
        self.excerpt_label.configure(text=text)
    def _write(self,text):
        try:self.session.write(text);return True
        except Exception as exc:self._status(str(exc));return False
    def _terminal_reply(self,text):
        # Only replies constructed by pyte (device/cursor status), never OSC
        # clipboard or output-derived shell commands.
        if self.session.backend and self.session.backend.is_alive():self._write(text)
    def _send_line(self):
        try:value=validate_line(self.entry.get())
        except TerminalError as exc:self._status(str(exc));return
        if self._write(value):self.entry.set('')
    def _interrupt(self):
        if not self.session.active():return
        if messagebox.askyesno('中斷官方工作','要傳送 Ctrl+C 嗎？下載、封裝或服務可能中斷。',parent=self.root):self._write('\x03')
    def _terminal_key(self,e):
        key=e.keysym;ctrl=bool(e.state&4)
        if ctrl and key.lower()=='c':
            if self.term.tag_ranges('sel'):
                self.root.clipboard_clear();self.root.clipboard_append(self.term.get('sel.first','sel.last'))
            else:self._interrupt()
        elif ctrl and key.lower()=='v':
            try:
                text=self.root.clipboard_get();validate_line(text)
                self.entry.set(text);self.input.focus_set()
                self._status('已放入輸入欄；檢查後按「送出」。')
            except (tk.TclError,TerminalError) as exc:self._status(str(exc))
        else:
            seq={'Return':'\r','KP_Enter':'\r','BackSpace':'\x08','Tab':'\t','Up':'\x1b[A','Down':'\x1b[B','Left':'\x1b[D','Right':'\x1b[C','Home':'\x1b[H','End':'\x1b[F','Delete':'\x1b[3~','Escape':'\x1b','Prior':'\x1b[5~','Next':'\x1b[6~'}
            if key in seq:self._write(seq[key])
            elif e.char and all(ord(c)>=32 and ord(c)!=127 for c in e.char):self._write(e.char)
        return 'break'
    def _schedule_resize(self):
        if self.resize_job:self.root.after_cancel(self.resize_job)
        self.resize_job=self.root.after(180,self._resize)
    def _resize(self):
        self.resize_job=None
        rows,cols=self.terminal.dimensions();rows=min(100,rows);cols=min(240,cols)
        self.screen.resize(rows,cols);self.session.resize(rows,cols);self.dirty=True
    def _poll(self):
        for kind,p in self.session.drain(32):
            if kind=='output':
                self.log.append(p);self.screen.feed(p);self.dirty=True;self.last_output=time.monotonic()
                g=self.guide.feed(p)
                if g:self._stage(g.code)
                raw,hint=explain_excerpt(self.screen.text()[-1800:]);self.raw_label.configure(text=raw);self.excerpt_label.configure(text=hint)
            elif kind=='system':self._system(p)
            elif kind=='stage':self._stage(p)
            elif kind=='status':self._status(p)
            elif kind=='error':self._error(p)
            elif kind=='install_info':self.install_label.configure(text=p)
            elif kind=='gpus':self.gpus=p;self._gpu_choices()
            elif kind=='running':
                self._status('官方程序執行中；依左側問題回答。');self._resize();self.input.focus_set()
                if self.settings_open:self._toggle_settings()
            elif kind=='demo_ready':self._stage('demo_ready')
            elif kind=='stopped':
                if p.get('cancelled'):self._stage('cancelled')
                elif self.stage not in ('error','demo_ready'):
                    self._stage('error' if p.get('code') not in (0,None) or p.get('error') else 'stopped')
                code=p.get('code');self._system('展示已結束。' if p.get('demo') else f'官方終端機已結束；退出碼：{code if code is not None else "未取得"}。')
            elif kind=='health':
                r=p['result']
                if r.healthy:
                    self._stage('ready' if self.session.backend and self.session.backend.is_alive() else 'already_running')
                    self._status('本機 /health 回報就緒；未核對 PID，不作為完整安裝驗收。')
                    if p['open_after']:webbrowser.open(CHAT_URL)
                else:
                    if self.stage=='ready':self._stage('starting' if self.session.active() else 'stopped')
                    if p['open_after']:self._status(r.reason+' 尚未開啟網頁。')
        active=self.session.active()
        self.start_btn.configure(state='disabled' if active else 'normal')
        self.stop_btn.configure(state='normal' if active else 'disabled')
        self.live_label.configure(text='●  離線模擬' if self.demo else ('●  正在執行' if active else '●  未執行'),fg=C['green'] if active else C['muted'])
        if self.dirty:self.terminal.render(self.screen);self.dirty=False
        now=time.monotonic()
        if not self.demo and self.stage in ('starting','ready') and active and now-self.health_at>4:
            self.health_at=now;self.session.probe_async()
        if self.closing and not active:
            self.session.closed=True;self.root.destroy();return
        self.poll_job=self.root.after(80,self._poll)
    def _open_chat(self):
        if self.demo:self._status('離線展示不連線、不開啟聊天網頁。');return
        self._status('正在檢查本機 /health…');self.session.probe_async(open_after=True)
    def _copy(self):
        self.root.clipboard_clear();self.root.clipboard_append(self.screen.text());self._status('已複製畫面；分享前請檢查是否包含個人路徑或敏感資訊。')
    def _export_log(self):
        p=filedialog.asksaveasfilename(parent=self.root,title='匯出日誌（分享前請檢查私人資訊）',defaultextension='.txt',initialfile='Strata-Easy-TW-log.txt')
        if not p:return
        try:
            metadata={'guide_version':VERSION,'mode':'demo' if self.demo else 'real','time':datetime.now().astimezone().isoformat(),
                'stage':self.stage,'source_record':self.session.source_record,'terminal_live':bool(self.session.backend and self.session.backend.is_alive()),
                'notice':'輸出可能含敏感資訊；匯出檔案只保留在你選擇的位置。'}
            Path(p).write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n\n'+self.log.text(),encoding='utf-8')
            self._status('已匯出日誌。分享前請檢查路徑、Token 或其他敏感文字。')
        except OSError as exc:self._status('日誌無法儲存：'+str(exc))
    def _stop(self):
        if not self.session.active():return
        if not self.demo and not messagebox.askyesno('停止目前工作','將取消下載，或強制停止本導覽器啟動的程序樹。模型檔案不會刪除；正在寫入的工作可能需要重新執行。確定停止？',parent=self.root):return
        self._status('正在停止；網路請求可能要等逾時後才會結束…');self.session.stop()
    def _close(self):
        if self.closing:return
        if self.session.active():
            if not messagebox.askyesno('關閉並停止工作','離開會停止本導覽器的下載或官方程序，聊天可能中斷。確定離開？',parent=self.root):return
            self.closing=True;self.session.stop();self._status('正在停止，完成後關閉視窗…')
        else:self.session.closed=True;self.root.destroy()
    def _popup(self,title,text,width=740,height=590):
        window=tk.Toplevel(self.root);window.title(title);window.geometry(f'{width}x{height}')
        window.configure(bg=C['surface']);window.transient(self.root)
        label(window,title,color='cyan',size=17,bold=True).pack(anchor='w',padx=20,pady=16)
        body=tk.Text(window,bg=C['surface'],fg=C['text'],wrap='word',font=('Microsoft JhengHei UI',11),relief='flat',padx=20,pady=10)
        body.pack(fill='both',expand=True);body.insert('end',text);body.configure(state='disabled')
        button(window,'關閉',window.destroy).pack(pady=10)
    def _about(self):
        self._popup('關於與第三方授權',f'''Strata Easy TW {VERSION}\n\n這是非官方社群工具，與 Strata、Qwen 及其作者沒有官方隸屬或背書關係。導覽器的原創程式碼沿用 MIT 授權。\n\n官方專案：{REPO}\nStrata 授權：{REPO}/blob/main/LICENSE\n模型來源：https://huggingface.co/Qwen/Qwen3.8-Flash-Next\n\n原始碼與發行包附 LICENSE、THIRD_PARTY_NOTICES.md 及第三方原文。模型、引擎與其元件各有授權，請在官方選單選定後閱讀對應模型條款。本工具不內附模型或 Strata 引擎。\n\n小雪採用 AI 生成的 3D 風格預渲染圖像，依階段切換六種姿態，搭配可關閉的輕微動態。\n\n這是候選測試版；Windows 真實安裝與乾淨機驗收狀態請看附帶測試報告。''')

    def _show_quickstart(self):
        self._popup('第一次使用？五步就懂', '''【1. 選來源】
全新電腦：選「從官方 GitHub 下載」。已經裝過：選「使用已有的 Strata 資料夾」。

【2. 選位置】
請選空間充足的 SSD，例如 D:\\AI。下載 Strata 程式本身不大，但後續模型、封裝資料與暫存可能占用超過 100 GiB。

【3. 顯卡】
只有一張顯卡：保留「官方自動選擇」。多張顯卡：可以自行選擇，但不是一定要改。

【4. 左邊回答、右邊看中文】
左邊會看到真正的 Strata 官方英文選單。請在「我的輸入」填編號並送出；或按「使用官方預設」。你不用一直打 Y！
右邊自動顯示這一步的用途、該做什麼、何時要等。

【5. 聊天】
安裝完成並載入模型後，按「開啟本地聊天網頁」。
下次可雙擊 Strata 目錄中的 START-HERE.bat 或 run-模型名.bat。

【放心事項】
本工具不夾帶原始模型、不修改官方安裝檔、不會偷替你選選項，也不會要求你上傳聊天內容。''')

    def _show_faq(self):
        self._popup('新手常見問題與解法', '''【Q：我電腦已經有 Strata，為什麼跳過 GPU 或下載？】
A：官方會沿用已部署的設定，直接啟動既有模型。這是正常現象。不要為了測試重新下載數十 GB。

【Q：黑色視窗出現 1、2、3 該按什麼？】
A：右邊說明這個選項代表什麼。最保守是按 Enter 使用官方推薦。上方標示的是階段，不是下載百分比。

【Q：Downloading 久久不動？】
A：模型可能有 60–80GB 以上，視網路需要很久；查看官方輸出有無真正錯誤。官方通常能續傳。

【Q：Preparing native pack 不是卡死？】
A：此時可能大量讀寫硬碟。只要沒有報錯，就讓它繼續。

【Q：MTP 是第二個模型嗎？】
A：它是生成加速用的元件，不等於再下載完整的 125B。

【Q：網頁 127.0.0.1:8080 打不開？】
A：模型可能還在載入，或 8080 已被別的程式使用。請先看左側訊息及健康檢查。

【Q：如何改 Context / 圖片理解？】
A：官方提供 SETUP.bat（也可用 START-HERE.bat --setup）。更改已有部署前請備份設定。

【Q：這是無審查 SC117 版本嗎？】
A：不是。本導覽器保留官方標準安裝流程，並未私下換成 SC117 Abliterated 權重。第三方版本應另經使用者授權確認及專屬 Pack。

【Q：關閉導覽器會怎麼樣？】
A：如果官方模型還在這裡執行，關閉可能一起停止 Strata；聊天頁面將無法再回答。''')

    def _show_glossary(self):
        self._popup('AI 安裝英文名詞小字典','\n\n'.join('【'+key+'】\n'+desc for key,desc in GLOSSARY),width=680,height=580)

    def _show_models(self):
        self._popup('模型量化怎麼選？', '''【新手先知道一件事】
Q2_0、IQ2_XS、IQ3_XXS、IQ3_S 不是四個不同智商的 AI，而是模型權重的不同壓縮方式。較高精度通常更忠實，但更占記憶體；實際速度由硬體與設定決定。

【Q2_0｜優先節省空間】
低精度、記憶體壓力相對小。適合想先體驗，但需要接受較大品質誤差的情況。

【IQ2_XS｜省 RAM 的折衷】
比 IQ3 更節省資源，適合 RAM 餘裕有限、還要同時使用其他軟體的人。

【IQ3_XXS｜較平衡】
比低位元量化保留更多資訊，但也會吃更多 RAM。

【IQ3_S｜偏重品質】
模型資訊保留較多，但 RAM 壓力較高。例如 64GB 電腦同時執行大型圖片生成時可能太吃緊。

【你要選哪個？】
保留 Strata 官方左側依硬體提供的建議最重要。不要只看顯卡 VRAM，SSD 可用容量、CPU、Context 也會影響。

【重要】
這些是白話比較，不是官方承諾的精確 GB 或每秒 Token，也不是每個版本永遠都能下載。''')

    def _show_hardware(self):
        data=get_resources(Path(self.path.get()))
        gpu='\n'.join('  '+g.caption for g in self.gpus) or '  未讀取到 NVIDIA GPU；請以官方偵測為準。'
        ram=f'{data.ram_gib:.1f} GiB' if data.ram_gib is not None else '未知'
        disk=f'{data.disk_free_gib:.1f} GiB' if data.disk_free_gib is not None else '未知'
        self._popup('你的電腦：資源檢查',f'''【記憶體】
系統 RAM：{ram}

【顯示卡】
{gpu}

【磁碟空間】
選取磁碟可用：{disk}
安裝路徑：{self.path.get()}
注意：官方預設 Strata-data 放在 Strata 程式資料夾的同層，而不一定在程式資料夾內。

【初步建議】
{data.suggested}

【需注意】
{data.warning}

【重要】
這是導覽器提供的粗略說明，並不是硬體相容性通過證明。最終依官方 Strata 的硬體檢查、顯示卡支援與模型需求為準。''',width=720,height=600)

def self_test(output):
    from smoke import run_self_test
    result=run_self_test()
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['ok'] else 1

def main():
    parser=argparse.ArgumentParser(description='Strata Easy TW 非官方繁體中文導覽')
    parser.add_argument('--demo',action='store_true',help='離線展示，不執行官方安裝')
    parser.add_argument('--self-test',metavar='JSON',help='執行包裝資源與 Windows ConPTY 測試，寫出 JSON')
    parser.add_argument('--smoke-test',metavar='JSON',help='開啟離線 UI、切換階段後關閉，寫出 JSON')
    args=parser.parse_args()
    prepare_frozen_runtime()
    if args.self_test:return self_test(args.self_test)
    if os.name=='nt':
        import ctypes
        try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (OSError,AttributeError):pass
    root=tk.Tk();app=App(root,demo=args.demo or bool(args.smoke_test),autoplay=not bool(args.smoke_test))
    if args.smoke_test:
        def smoke():
            try:
                for code in GUIDES:app._stage(code);root.update_idletasks()
                result={'ok':True,'stages':len(GUIDES),'mode':'offline-ui','version':VERSION}
            except Exception as exc:result={'ok':False,'error':str(exc)}
            Path(args.smoke_test).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            root.destroy()
        root.after(400,smoke)
    root.mainloop()
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        message=traceback.format_exc()
        dest=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'StrataEasyTW'
        try:dest.mkdir(parents=True,exist_ok=True);(dest/'crash.log').write_text(message,encoding='utf-8')
        except OSError:pass
        try:messagebox.showerror('啟動失敗',f'導覽器無法啟動。請確認相依套件與完整資料夾。\n詳細訊息：{dest / "crash.log"}\n\n{message[-500:]}')
        except Exception:print(message,file=sys.stderr)
        sys.exit(1)
