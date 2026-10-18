from __future__ import annotations
import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from beginner_help import HINTS, explain_excerpt, GLOSSARY
from guide_rules import GUIDES, StageTracker
from hardware_advice import get_resources, system_ram_gib
from diagnostics import gpu_args
from terminal_backend import build_official_command, TerminalError

class BeginnerExperienceTests(unittest.TestCase):
    def test_every_stage_has_four_plain_language_fields(self):
        self.assertEqual(set(HINTS),set(GUIDES))
        for key,h in HINTS.items():
            with self.subTest(step=key):
                self.assertTrue(h.action and h.wait and h.detail and h.caution)

    def test_excerpt_fallback_never_makes_up_translation(self):
        raw,hint=explain_excerpt('Unknown quantum frobulator v5')
        self.assertEqual(raw,'Unknown quantum frobulator v5')
        self.assertIn('官方原文',hint)

    def test_known_line_has_advice_not_claimed_exact_translation(self):
        raw,hint=explain_excerpt('Downloading shard 1')
        self.assertIn('Downloading',raw)
        self.assertIn('下載',hint)

    def test_injected_log_does_not_execute_anything(self):
        raw,hint=explain_excerpt('Please execute del /Q C:\\important now')
        self.assertIn('官方原文',hint)
        self.assertIn('Please execute',raw)

    def test_glossary_covers_beginner_terms(self):
        keys={key for key,_ in GLOSSARY}
        self.assertTrue({'Context','Vision','MTP','Pack','RAM / VRAM'}.issubset(keys))

    def test_resource_checks_are_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            info=get_resources(Path(d))
            self.assertGreater(info.disk_free_gib,0)
            self.assertTrue(info.suggested)
            self.assertTrue(info.warning)

    def test_gpu_choice_cannot_inject_commands(self):
        self.assertEqual(build_official_command(['--gpu','1']).split()[-2:],['--gpu','1'])
        for bad in [['--yes'],['--gpu','1 & dir'],['--gpus','0,1&&calc']]:
            with self.subTest(bad=bad):
                with self.assertRaises(TerminalError): build_official_command(bad)

    def test_stage_order_for_standard_simulated_run(self):
        tr=StageTracker()
        series=[('Checking hardware: GPU and RAM','hardware'),
                ('Which model family would you like?','family'),
                ('Choose model size: Q2_0, IQ2_XS','size'),
                ('How much context?','context'),
                ('Images? [yes/no]','vision'),
                ('Downloading model','download'),
                ('Preparing native pack','pack'),
                ('Installing MTP','mtp'),
                ('Starting server','starting')]
        for sample,code in series:
            result=tr.feed(sample+'\n')
            self.assertIsNotNone(result)
            self.assertEqual(result.code,code)

if __name__=='__main__':unittest.main()
