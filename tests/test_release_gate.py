"""Release candidate must fail closed unless the build really passed its checks."""
from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import release_gate

class ReleaseSafety(unittest.TestCase):
    def test_source_packager_excludes_test_caches(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('package_source', ROOT/'tools/package_source.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIn('.pytest_cache', module.EXCLUDED)

    def test_ascii_and_crlf_launchers(self):
        self.assertTrue(release_gate.verify_text_launchers()['ok'])

    def test_mismatched_tag_is_rejected(self):
        with patch.dict(os.environ, {'GITHUB_REF':'refs/tags/v99.9.9'}):
            with self.assertRaisesRegex(release_gate.ReleaseGateError, '標籤'):
                release_gate.verify_text_launchers()

    def test_matching_tag_accepted(self):
        with patch.dict(os.environ, {'GITHUB_REF':'refs/tags/v'+release_gate.VERSION}):
            self.assertTrue(release_gate.verify_text_launchers()['ok'])

    def test_no_unsigned_binary_can_pass_when_missing(self):
        if (ROOT/'release'/f'StrataEasyTW-{release_gate.VERSION}-Setup.exe').is_file():
            self.skipTest('release artifacts exist; this test is for fresh source checkouts')
        with self.assertRaises(release_gate.ReleaseGateError):
            release_gate.verify_binaries()

if __name__ == '__main__':unittest.main()
