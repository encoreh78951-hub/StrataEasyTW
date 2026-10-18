import io
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostics import LocalPort
from guide_rules import StageTracker, GUIDES
from mascot import STAGE_POSES, TIPS
from session import Session, SessionLog
from source_manager import safe_extract, download_official, SourceError, SourceCancelled, validate_zip_name
from terminal_backend import validate_line, TerminalError
from terminal_screen import TerminalScreen

def wait_until(predicate,timeout=2):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.005)
    raise AssertionError('timed out')

class Guides(unittest.TestCase):
    def test_actual_upstream_prompts(self):
        for text,key in [('Which model? [1]:','family'),('Which size? [2]:','size'),
                         ('Context? [1]:','context'),('Images? [y]:','vision'),
                         ('Turn on the experimental speed projection? [n]:','speed')]:
            with self.subTest(text=text):self.assertEqual(StageTracker().feed(text).code,key)
    def test_split_ansi_prompt(self):
        tr=StageTracker();tr.feed('\x1b[3');tr.feed('6mWhich mo')
        self.assertEqual(tr.feed('del?\x1b[0m [1]:').code,'family')
    def test_latest_stage_in_single_read(self):
        tr=StageTracker()
        self.assertEqual(tr.feed('Checking GPU\r\nDownloading model\r\nPreparing native pack\r\n').code,'pack')
    def test_terminal_osc_does_not_trigger_stage(self):
        tr=StageTracker()
        self.assertIsNone(tr.feed('\x1b]0;Downloading model\x07'))
        self.assertEqual(tr.state.code,'welcome')
    def test_error_stays_on_unrecognized_tail(self):
        tr=StageTracker();tr.feed('Downloading model\nERROR: network failure\n')
        self.assertEqual(tr.state.code,'error');tr.feed('details follow\n')
        self.assertEqual(tr.state.code,'error')
    def test_output_never_sets_verified_ready(self):
        tr=StageTracker();tr.feed('Server ready: http://127.0.0.1:8080\n')
        self.assertNotEqual(tr.state.code,'ready')
    def test_every_stage_has_mascot(self):
        self.assertEqual(set(GUIDES),set(STAGE_POSES));self.assertEqual(set(GUIDES),set(TIPS))

class Terminal(unittest.TestCase):
    def test_resize_preserves_short_output(self):
        s=TerminalScreen();s.feed('Which model?\r\nDownloading model\r\n')
        s.resize(8,80)
        self.assertIn('Which model?',s.text())
        self.assertIn('Downloading model',s.text())
        s.resize(40,120);self.assertIn('Which model?',s.text())
    def test_resize_archives_overflow(self):
        s=TerminalScreen(rows=20)
        s.feed('\r\n'.join('line '+str(i) for i in range(18)))
        s.resize(8,80)
        self.assertIn('line 0',s.text());self.assertIn('line 17',s.text())
        self.assertEqual(s.vt.cursor.y,7)
    def test_cursor_clear_and_redraw(self):
        s=TerminalScreen();s.feed('Downloading 99%\r\x1b[2KDone')
        self.assertEqual(s.text(),'Done')
    def test_cursor_up(self):
        s=TerminalScreen();s.feed('old\r\nsecond\x1b[1A\r\x1b[2Knew')
        self.assertEqual(s.text(),'new\nsecond')
    def test_colour_is_preserved(self):
        s=TerminalScreen();s.feed('\x1b[31mERROR\x1b[0m')
        self.assertEqual(s.snapshot()[0][0][1][0],'red')
    def test_chinese_and_osc(self):
        s=TerminalScreen();s.feed('繁體中文\x1b]52;c;aGVsbG8=\x07')
        self.assertEqual(s.text(),'繁體中文')
    def test_status_response_only(self):
        replies=[];s=TerminalScreen(reply=replies.append);s.feed('abc\x1b[6n')
        self.assertEqual(replies,['\x1b[1;4R'])
    def test_multiline_and_controls_blocked(self):
        for text in ('1\n2','abc\r','\x1b[A','x'*1024,'\x00'):
            with self.subTest(text=text[:8]):
                with self.assertRaises(TerminalError):validate_line(text)
        self.assertEqual(validate_line('中文選項'),'中文選項\r')
    def test_log_is_bounded(self):
        log=SessionLog(20);log.append('a'*12);log.append('b'*12)
        self.assertLessEqual(log.size,20);self.assertTrue(log.truncated)
        log.append('c'*100);self.assertLessEqual(log.size,20)

class Archives(unittest.TestCase):
    def make_zip(self,folder,extra=()):
        archive=Path(folder)/'source.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for name in ('START-HERE.bat','SETUP.bat','setup.py','LICENSE'):
                z.writestr('Strata-'+'a'*40+'/'+name,'fixture')
            for name,data in extra:z.writestr('Strata-'+'a'*40+'/'+name,data)
        return archive
    def test_invalid_windows_names(self):
        for name in ('r/a?b','r/a*','r/COM¹.txt','r//a','r/./a','r/a\x01'):
            with self.subTest(name=name):
                with self.assertRaises(SourceError):validate_zip_name(name)
    def test_case_collision(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.make_zip(td,[('license','collision')])
            with self.assertRaises(SourceError):safe_extract(a,Path(td)/'stage')
    def test_symlink_block(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.make_zip(td)
            with zipfile.ZipFile(a,'a') as z:
                info=zipfile.ZipInfo('Strata-'+'a'*40+'/link');info.external_attr=0o120777<<16;z.writestr(info,'/tmp')
            with self.assertRaises(SourceError):safe_extract(a,Path(td)/'stage')
    def test_cancel_before_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            event=threading.Event();event.set();a=self.make_zip(td)
            with self.assertRaises(SourceCancelled):safe_extract(a,Path(td)/'stage',event)
            self.assertFalse((Path(td)/'stage'/'content').exists())
    def test_low_disk(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.make_zip(td)
            with patch('source_manager.shutil.disk_usage') as disk:
                disk.return_value.free=0
                with self.assertRaises(SourceError):safe_extract(a,Path(td)/'stage')
    def test_download_fixed_commit_and_record(self):
        with tempfile.TemporaryDirectory() as td:
            a=self.make_zip(td);data=a.read_bytes();parent=Path(td)/'install'
            class Response(io.BytesIO):
                def geturl(self):return 'https://codeload.github.com/Niko1221/Strata/zip/'+'a'*40
            with patch('source_manager.get_head_sha',return_value='a'*40),patch('source_manager.request',return_value=Response(data)) as req:
                dest,sha,digest=download_official(parent,lambda x:None,threading.Event())
            self.assertTrue((dest/'.strata-easy-tw-source.json').is_file())
            self.assertEqual(sha,'a'*40);self.assertEqual(len(digest),64)
            self.assertTrue(req.call_args.args[0].endswith(sha))
    def test_existing_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'Strata-Official').mkdir()
            with patch('source_manager.get_head_sha') as api:
                with self.assertRaises(SourceError):download_official(Path(td),lambda x:None,threading.Event())
                api.assert_not_called()

class FakeBackend:
    def __init__(self,emit):self.emit=emit;self.alive=False;self.writes=[];self.thread=None
    def start(self,*a,**kw):self.alive=True
    def is_alive(self):return self.alive
    def write(self,text):self.writes.append(text)
    def stop(self):self.alive=False;self.emit('stopped',{'cancelled':True,'code':None})

class Lifecycle(unittest.TestCase):
    def test_occupied_port_does_not_start(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ('START-HERE.bat','SETUP.bat','setup.py','LICENSE'):(Path(td)/name).touch()
            factory=unittest.mock.Mock()
            s=Session(backend_factory=factory,probe=lambda:LocalPort(True,True,'existing'))
            s.start('existing',td);wait_until(lambda:not s.working)
            factory.assert_not_called();self.assertIn(('stage','already_running'),s.drain())
    def test_cancel_download_prevents_spawn(self):
        gate=threading.Event();started=threading.Event();factory=unittest.mock.Mock()
        def download(folder,log,cancel):
            started.set();gate.wait(1)
            if cancel.is_set():raise SourceCancelled('cancelled')
            return folder,'sha','digest'
        s=Session(factory,download,lambda:LocalPort(False,False,''));s.start('download','unused')
        self.assertTrue(started.wait(1));s.stop();gate.set();wait_until(lambda:not s.working)
        factory.assert_not_called();self.assertIn(('stage','cancelled'),s.drain())
    def test_no_automatic_answers_and_restart(self):
        with tempfile.TemporaryDirectory() as td:
            for name in ('START-HERE.bat','SETUP.bat','setup.py','LICENSE'):(Path(td)/name).touch()
            s=Session(FakeBackend,probe=lambda:LocalPort(False,False,''));s.start('existing',td)
            wait_until(lambda:not s.working);self.assertEqual(s.backend.writes,[])
            with self.assertRaises(TerminalError):s.start('existing',td)
            s.write('2\r');self.assertEqual(s.backend.writes,['2\r']);s.stop()
            wait_until(lambda:not s.active());s.start('existing',td);wait_until(lambda:not s.working)
            self.assertEqual(s.backend.writes,[]);s.stop()
    def test_stale_events_ignored(self):
        s=Session();s.emit(0,'status','old');s._begin();s.working=False
        s.emit(0,'status','older');s.emit(1,'status','new')
        self.assertEqual(s.drain(),[('status','new')])
    def test_demo_does_not_probe_or_download(self):
        def forbidden(*a,**k):raise AssertionError('must stay offline')
        s=Session(forbidden,forbidden,forbidden);s.start_demo('first',delay=.001)
        s.probe_async(True);wait_until(lambda:not s.active())
        self.assertIn(('demo_ready',None),s.drain(300))

@unittest.skipUnless(os.name=='nt','requires real Windows ConPTY')
class WindowsIntegration(unittest.TestCase):
    def test_interactive_conpty_fixture(self):
        from smoke import conpty_fixture
        self.assertTrue(conpty_fixture()['ok'])

if __name__=='__main__':unittest.main()
