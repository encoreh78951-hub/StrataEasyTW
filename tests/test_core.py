from __future__ import annotations
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from guide_rules import StageTracker
from terminal_screen import TerminalScreen
from source_manager import validate_zip_name, safe_extract, validate_existing, SourceError

class TestGuide(unittest.TestCase):
    def test_stages_and_nonautomatic(self):
        tr=StageTracker()
        self.assertEqual(tr.feed('Checking hardware: GPU NVIDIA, memory available'),tr.state)
        self.assertEqual(tr.state.code,'hardware')
        self.assertEqual(tr.feed('Which model family would you like?').code,'family')
        self.assertEqual(tr.feed('Choose model size (Q2_0, IQ2_XS): ').code,'size')
        self.assertEqual(tr.feed('How much context?').code,'context')
        self.assertEqual(tr.feed('Images? [yes/no]: ').code,'vision')
        self.assertEqual(tr.feed('Downloading model shard 10 GB/70 GB').code,'download')
        self.assertEqual(tr.feed('Preparing native pack...').code,'pack')
        self.assertEqual(tr.feed('Installing MTP draft acceleration...').code,'mtp')
        self.assertEqual(tr.feed('Starting server...').code,'starting')
    def test_unrecognized_does_not_claim_success(self):
        tr=StageTracker()
        self.assertIsNone(tr.feed('We recommend frobulator v37\r\n'))
        self.assertEqual(tr.state.code,'welcome')

class TestScreen(unittest.TestCase):
    def test_ansi_split(self):
        s=TerminalScreen();s.feed('\x1b[31');s.feed('mHello\x1b[0m world\r\n')
        self.assertEqual(s.text(),'Hello world\n')
    def test_carriage_return_progress(self):
        s=TerminalScreen();s.feed('Downloading 1%\rDownloading 20%\n')
        self.assertTrue(s.text().startswith('Downloading 20%'))
    def test_max_lines(self):
        s=TerminalScreen(max_lines=3)
        s.feed('1\n2\n3\n4\n5\n')
        self.assertEqual(len(s.lines),3)

class TestGitHubArchive(unittest.TestCase):
    def test_traversal_block(self):
        for x in ('repo/../../evil','/root/hack','repo/CON','repo/a:b','repo\\hack','repo/a. '):
            with self.subTest(name=x):
                with self.assertRaises(SourceError):validate_zip_name(x)
    def test_safe_extract_and_upstream_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);z=root/'src.zip'
            with zipfile.ZipFile(z,'w') as out:
                for name in ('START-HERE.bat','LICENSE','SETUP.bat','setup.py'):
                    out.writestr('Strata-123/'+name,'test')
            outdir=safe_extract(z,root/'work')
            self.assertEqual(validate_existing(outdir),outdir.resolve())
    def test_prevent_bad_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);z=root/'src.zip'
            with zipfile.ZipFile(z,'w') as out:
                out.writestr('Strata-main/../hack.txt','bad')
            with self.assertRaises(SourceError):safe_extract(z,root/'work')


class TestV03(unittest.TestCase):
    def test_gpu_csv_detection(self):
        from diagnostics import parse_nvidia_smi
        rows=parse_nvidia_smi('0, NVIDIA RTX 5080, 16384 MiB\n1, NVIDIA RTX 3060, 12288 MiB\n')
        self.assertEqual([g.index for g in rows],[0,1])
        self.assertEqual(rows[1].memory_mib,12288)
        self.assertEqual(parse_nvidia_smi('GPU Unknown, broken'),[])

    def test_gpu_choice_never_implicitly_changes_model(self):
        from diagnostics import gpu_args
        self.assertEqual(gpu_args('auto',{0,1}),[])
        self.assertEqual(gpu_args('gpu:1',{0,1}),['--gpu','1'])
        self.assertEqual(gpu_args('all',{0,1}),['--gpus','0,1'])
        with self.assertRaises(ValueError):gpu_args('gpu:9',{0,1})
        with self.assertRaises(ValueError):gpu_args('gpu:1 & calc',{0,1})

    def test_official_command_no_injection(self):
        from terminal_backend import build_official_command, TerminalError
        self.assertEqual(build_official_command(), 'cmd.exe /d /q /c call START-HERE.bat')
        self.assertTrue(build_official_command(['--setup','--gpu','1']).endswith('--setup --gpu 1'))
        with self.assertRaises(TerminalError):build_official_command(['--gpu','1 & calc.exe'])
        with self.assertRaises(TerminalError):build_official_command(['--yes'])
        with self.assertRaises(TerminalError):build_official_command(['--gpu','0,1'])

    def test_existing_source_does_not_prove_configured(self):
        from diagnostics import get_install_info
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            (folder/'START-HERE.bat').write_text('')
            self.assertEqual(get_install_info(folder).level,'source')
            (folder/'run-test.bat').write_text('')
            result=get_install_info(folder)
            self.assertEqual(result.level,'configured')
            self.assertIn('可能直接啟動',result.detail)

    def test_occupied_unrecognized_port(self):
        import socket
        from diagnostics import probe_port
        with socket.socket() as server:
            server.bind(('127.0.0.1',0))
            server.listen(1)
            result=probe_port(server.getsockname()[1])
            self.assertTrue(result.occupied)
            self.assertFalse(result.healthy)

    def test_demo_files_present_and_not_running_real_strata(self):
        from terminal_backend import DemoBackend
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        for demo in ('first','existing','failure'):
            self.assertTrue((root/'demo_logs'/f'{demo}.txt').is_file())
        backend=DemoBackend(lambda *args:None,root/'demo_logs'/'first.txt')
        self.assertFalse(backend.is_alive())

if __name__=='__main__':unittest.main()
