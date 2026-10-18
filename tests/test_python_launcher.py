import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bootstrap_windows import interpreter_supported

class PythonDetection(unittest.TestCase):
    def test_supported_64bit(self):
        for minor in (10,11,12,13):
            with self.subTest(minor=minor):
                self.assertTrue(interpreter_supported((3,minor,9),64))
    def test_reject_unsupported_versions(self):
        for minor in (9,14,15):
            with self.subTest(minor=minor):
                self.assertFalse(interpreter_supported((3,minor),64))
    def test_reject_32bit_or_pypy(self):
        self.assertFalse(interpreter_supported((3,13),32))
        self.assertFalse(interpreter_supported((3,12),64,'pypy'))
    def test_batch_scripts_use_common_launcher(self):
        root=Path(__file__).resolve().parents[1]
        for script in ('RUN_WINDOWS.bat','RUN_DEMO_WINDOWS.bat','BUILD_WINDOWS_EXE.bat'):
            with self.subTest(script=script):
                data=(root/script).read_bytes()
                self.assertIn(b'LAUNCH_WINDOWS.bat',data)
                self.assertIn(b'\r\n',data)
        launcher=(root/'LAUNCH_WINDOWS.bat').read_text(encoding='utf-8')
        self.assertIn('py -%~1',launcher)
        self.assertIn('python bootstrap_windows.py',launcher)
        self.assertIn('STRATA_GUIDE_PYTHON',launcher)
