import logging
import os
import unittest

os.environ['RENGINE_SECRET_KEY'] = 'secret'
os.environ['CELERY_ALWAYS_EAGER'] = 'True'

from reNgine.settings import DEBUG
from reNgine.tasks import parse_nmap_results
import pathlib

logger = logging.getLogger(__name__)
DOMAIN_NAME = os.environ.get('DOMAIN_NAME', 'test.local')
FIXTURES_DIR = pathlib.Path().absolute() / 'fixtures' / 'nmap_xml'

if not DEBUG:
    logging.disable(logging.CRITICAL)


class TestNmapParsing(unittest.TestCase):
    def setUp(self):
        self.nmap_vuln_single_xml = FIXTURES_DIR / 'nmap_vuln_single.xml'
        self.nmap_vuln_multiple_xml = FIXTURES_DIR / 'nmap_vuln_multiple.xml'
        self.nmap_vulscan_single_xml = FIXTURES_DIR / 'nmap_vulscan_single.xml'
        self.nmap_vulscan_multiple_xml = FIXTURES_DIR / 'nmap_vulscan_multiple.xml'
        self.all_xml = [
            self.nmap_vuln_single_xml,
            self.nmap_vuln_multiple_xml,
            self.nmap_vulscan_single_xml,
            self.nmap_vulscan_multiple_xml
        ]

    def test_nmap_parse(self):
        for xml_file in self.all_xml:
            if os.path.exists(xml_file):
                vulns = parse_nmap_results(str(xml_file))
                self.assertIsNotNone(vulns)

    def test_nmap_vuln_single(self):
        pass

    def test_nmap_vuln_multiple(self):
        pass

    def test_nmap_vulscan_single(self):
        pass

    def test_nmap_vulscan_multiple(self):
        pass


from django.test import TestCase
from startScan.models import Vulnerability


class NmapTestCase(TestCase):
    def test_vulnerability_has_group_key_field(self):
        """Vulnerability model must have a group_key field."""
        v = Vulnerability(
            name='Exim smtpd 4.99.2 (CVE-2026-45185)',
            severity=3,
            group_key='Exim smtpd 4.99.2'
        )
        self.assertEqual(v.group_key, 'Exim smtpd 4.99.2')