"""Offline UI regression checks; requires a graphical desktop or Xvfb DISPLAY.
Screenshots are actual application captures with explicitly simulated logs.
"""
import json
import os
from pathlib import Path
import sys
import time
import tkinter as tk
from PIL import ImageGrab

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import App
from guide_rules import GUIDES

def main():
    out=ROOT/'docs'/'test-results';out.mkdir(parents=True,exist_ok=True)
    errors=[];root=tk.Tk()
    root.report_callback_exception=lambda *e:errors.append(str(e))
    try:
        app=App(root,demo=True,autoplay=False)
        root.geometry('1420x940+0+0')
        def update(seconds=.3):
            until=time.monotonic()+seconds
            while time.monotonic()<until:root.update();time.sleep(.01)
        def shot(name):
            update()
            box=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
            kw={} if os.name=='nt' else {'xdisplay':os.environ.get('DISPLAY')}
            ImageGrab.grab(bbox=box,**kw).save(out/name)
        shot('UI-welcome.png')
        for code in GUIDES:
            app._stage(code);root.update_idletasks()
            assert app.title_label.cget('text')==GUIDES[code].title
        for kind,expected in [('first','demo_ready'),('existing','demo_ready'),('failure','error')]:
            app._reset();app.session.start_demo(kind,delay=.005)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                update(.08)
                if not app.session.active() and app.session.events.empty():break
            assert app.stage==expected,(kind,app.stage)
        app._reset()
        app.session.emit(app.session.generation,'output','\x1b[36mChecking hardware: GPU and RAM\x1b[0m\r\nWhich model? [1]: \r\nChoose model size: IQ2_XS\r\nDownloading model shard 12.0 GB / 70.0 GB\r\n')
        update();assert app.stage=='download'
        app._toggle_settings();update()
        assert 'Downloading model' in app.terminal.text.get('1.0','end')
        shot('UI-installing.png')
        root.geometry('1100x680+0+0');update()
        assert 'Downloading model' in app.terminal.text.get('1.0','end')
        assert app.input.winfo_ismapped()
        assert app.stop_btn.winfo_rooty()+app.stop_btn.winfo_height()<=root.winfo_height()+root.winfo_rooty()
        shot('UI-compact.png')
        app._stage('error');app.excerpt_label.configure(text='下載中斷：請檢查網路，保留已下載檔案後再重試。')
        shot('UI-error.png')
        app.reduced.set(True);app._motion();assert not app.mascot.motion
        app.session.probe=lambda:(_ for _ in ()).throw(AssertionError('unexpected network'))
        app._open_chat();update();assert not errors,errors
        report={'ok':True,'platform':sys.platform,'tk':tk.TkVersion,'stages':len(GUIDES),
                'demo_scenarios':3,'sizes':['1420x940','1100x680'],'callback_errors':errors,
                'windows_verified':False,'note':'offline UI only; no official installer executed'}
        (out/'ui-qa.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report));return 0
    finally:root.destroy()

if __name__=='__main__':sys.exit(main())
