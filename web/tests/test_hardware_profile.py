"""Hardware profile values only fill resource limits the engine leaves unset."""
import unittest

from reNgine.temporal.activities.core import apply_hardware_profile_defaults

PROFILE = {'threads': 4, 'rate_limit': 50, 'delay': 1, 'retries': 2}


class HardwareProfileDefaultsTests(unittest.TestCase):

    def test_section_value_wins(self) -> None:
        conf = {'threads': 30, 'port_scan': {'threads': 100, 'rate_limit': 1000}}
        apply_hardware_profile_defaults(conf, PROFILE)
        self.assertEqual(conf['port_scan']['threads'], 100)
        self.assertEqual(conf['port_scan']['rate_limit'], 1000)

    def test_engine_global_beats_the_profile_in_sections(self) -> None:
        conf = {'threads': 30, 'rate_limit': 150, 'dir_file_fuzz': {}}
        apply_hardware_profile_defaults(conf, PROFILE)
        self.assertEqual(conf['threads'], 30)
        self.assertEqual(conf['dir_file_fuzz']['threads'], 30)
        self.assertEqual(conf['dir_file_fuzz']['rate_limit'], 150)

    def test_profile_fills_what_the_engine_leaves_unset(self) -> None:
        conf = {'threads': 30, 'dir_file_fuzz': {}}
        apply_hardware_profile_defaults(conf, PROFILE)
        self.assertEqual(conf['delay'], 1)
        self.assertEqual(conf['retries'], 2)
        self.assertEqual(conf['dir_file_fuzz']['delay'], 1)

    def test_explicit_zero_is_kept(self) -> None:
        conf = {'delay': 0, 'osint': {'retries': 0}}
        apply_hardware_profile_defaults(conf, PROFILE)
        self.assertEqual(conf['delay'], 0)
        self.assertEqual(conf['osint']['retries'], 0)

    def test_scalar_sections_are_left_alone(self) -> None:
        conf = {'dns_security': True, 'custom_headers': ['X-Test: 1']}
        apply_hardware_profile_defaults(conf, PROFILE)
        self.assertIs(conf['dns_security'], True)
        self.assertEqual(conf['custom_headers'], ['X-Test: 1'])
