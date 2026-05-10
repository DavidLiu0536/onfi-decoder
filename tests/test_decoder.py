"""Basic unit tests for OnfiDecoder."""
import os
import sys
import subprocess
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from onfi_decoder import OnfiDecoder
from onfi_decoder.commands import lookup_command, parse_status


class TestCommands(unittest.TestCase):
    def test_known_opcodes(self):
        self.assertEqual(lookup_command(0xFF)[0], 'RESET')
        self.assertEqual(lookup_command(0x90)[0], 'READ_ID')
        self.assertEqual(lookup_command(0x80)[0], 'PROGRAM_PAGE')
        self.assertEqual(lookup_command(0x60)[0], 'BLOCK_ERASE')

    def test_unknown_opcode(self):
        self.assertEqual(lookup_command(0x42)[0], 'UNKNOWN')

    def test_parse_status_ready(self):
        # 0xE0 = 0b1110_0000 → WP, RDY, ARDY set, all error bits clear
        flags = parse_status(0xE0)
        active = [f['name'] for f in flags if f['value']]
        self.assertIn('WP', active); self.assertIn('RDY', active); self.assertIn('ARDY', active)
        self.assertNotIn('FAIL', active)

    def test_parse_status_fail(self):
        # 0xE1 = 0b1110_0001 → ready but FAIL bit set
        flags = parse_status(0xE1)
        active = [f['name'] for f in flags if f['value']]
        self.assertIn('FAIL', active)


class TestDecoder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate sample data first
        examples_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples')
        subprocess.run([sys.executable, os.path.join(examples_dir, 'gen_sample_capture.py')], check=True)
        cls.csv_path = os.path.join(examples_dir, 'sample_capture.csv')

    def test_decode_runs_without_error(self):
        dec = OnfiDecoder()
        dec.decode_csv(self.csv_path)
        self.assertGreater(len(dec.events), 0)

    def test_expected_commands_detected(self):
        dec = OnfiDecoder()
        dec.decode_csv(self.csv_path)
        breakdown = dec.stats()['commands_breakdown']
        for cmd in ['RESET', 'READ_ID', 'READ_PAGE', 'READ_PAGE_CONFIRM',
                    'PROGRAM_PAGE', 'PROGRAM_CONFIRM', 'BLOCK_ERASE', 'ERASE_CONFIRM',
                    'READ_STATUS']:
            self.assertIn(cmd, breakdown, f"Missing decoded command: {cmd}")

    def test_read_id_data_count(self):
        dec = OnfiDecoder()
        dec.decode_csv(self.csv_path)
        # Find first DATA event after Read ID
        cmd_seen = False
        for e in dec.events:
            if e.kind == 'CMD' and e.raw['name'] == 'READ_ID':
                cmd_seen = True
            elif cmd_seen and e.kind == 'DATA':
                self.assertEqual(len(e.raw['bytes']), 5, "Read ID should return 5 bytes")
                self.assertEqual(e.raw['bytes'][0], 0x2C)  # Micron
                return
        self.fail("Did not find Read ID data sequence")


if __name__ == '__main__':
    unittest.main()
