from django.test import TestCase
from django.utils import timezone
from scanEngine.models import EngineType
from startScan.models import CertificateIntelligence, ScanHistory
from targetApp.models import Domain


def _make_scan(domain):
    engine = EngineType.objects.create(engine_name="CertTest Engine", yaml_configuration="")
    return ScanHistory.objects.create(
        scan_status=0,
        domain=domain,
        scan_type=engine,
        start_scan_date=timezone.now(),
        tasks=[],
    )


class TestCertificateIntelligenceModel(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name="test.example.com")
        self.scan = _make_scan(self.domain)

    def test_model_creation(self):
        cert = CertificateIntelligence.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            host="test.example.com",
            port=443,
            subject_cn="test.example.com",
            subject_an=["test.example.com", "www.test.example.com"],
            issuer_cn="R3",
            issuer_org="Let's Encrypt",
            tls_version="tls13",
            cipher="TLS_AES_256_GCM_SHA384",
            fingerprint_sha256="aabbcc112233",
            self_signed=False,
            has_weak_cipher=False,
            is_expired=False,
        )
        self.assertIsNotNone(cert.id)

    def test_is_expired_flag(self):
        from django.utils import timezone
        import datetime
        cert = CertificateIntelligence.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            host="expired.example.com",
            port=443,
            not_after=timezone.now() - datetime.timedelta(days=10),
            fingerprint_sha256="expired001",
            is_expired=True,
        )
        self.assertTrue(cert.is_expired)

    def test_weak_cipher_flag(self):
        cert = CertificateIntelligence.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            host="weak.example.com",
            port=443,
            cipher="TLS_RSA_WITH_3DES_EDE_CBC_SHA",
            fingerprint_sha256="weak001",
            has_weak_cipher=True,
        )
        self.assertTrue(cert.has_weak_cipher)


class TestCertificateParser(TestCase):
    def test_parse_valid_tlsx_json_line(self):
        from reNgine.certificate_tasks import parse_tlsx_json_line
        line = (
            '{"host":"example.com","ip":"1.2.3.4","port":443,'
            '"tls_version":"tls13","cipher":"TLS_AES_256_GCM_SHA384",'
            '"not_before":"2024-01-01T00:00:00Z","not_after":"2025-01-01T00:00:00Z",'
            '"subject_cn":"example.com","subject_an":["example.com","www.example.com"],'
            '"issuer_cn":"R3","issuer_org":["Let\'s Encrypt"],'
            '"fingerprint_hash":{"sha256":"aabbccdd"},'
            '"self_signed":false,"mismatched":false}'
        )
        result = parse_tlsx_json_line(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["host"], "example.com")
        self.assertEqual(result["subject_cn"], "example.com")
        self.assertEqual(result["fingerprint_sha256"], "aabbccdd")
        self.assertFalse(result["self_signed"])

    def test_parse_invalid_json_returns_none(self):
        from reNgine.certificate_tasks import parse_tlsx_json_line
        result = parse_tlsx_json_line("not json at all")
        self.assertIsNone(result)

    def test_parse_empty_line_returns_none(self):
        from reNgine.certificate_tasks import parse_tlsx_json_line
        result = parse_tlsx_json_line("")
        self.assertIsNone(result)

    def test_is_weak_cipher_rc4(self):
        from reNgine.certificate_tasks import is_weak_cipher
        self.assertTrue(is_weak_cipher("TLS_RSA_WITH_RC4_128_SHA"))

    def test_is_weak_cipher_3des(self):
        from reNgine.certificate_tasks import is_weak_cipher
        self.assertTrue(is_weak_cipher("TLS_RSA_WITH_3DES_EDE_CBC_SHA"))

    def test_is_strong_cipher(self):
        from reNgine.certificate_tasks import is_weak_cipher
        self.assertFalse(is_weak_cipher("TLS_AES_256_GCM_SHA384"))

    def test_is_weak_cipher_null(self):
        from reNgine.certificate_tasks import is_weak_cipher
        self.assertTrue(is_weak_cipher("TLS_NULL_WITH_NULL_NULL"))


class TestCertificateActivity(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name="activity.example.com")
        self.scan = _make_scan(self.domain)

    def test_activity_calls_runner(self):
        from unittest.mock import patch
        with patch("reNgine.certificate_tasks.run_certificate_intel") as mock_runner:
            from reNgine.temporal_activities import run_certificate_intel_activity
            mock_runner.return_value = []
            result = run_certificate_intel_activity(self.scan.id)
            mock_runner.assert_called_once()
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["count"], 0)

    def test_activity_returns_count(self):
        from unittest.mock import patch
        with patch("reNgine.certificate_tasks.run_certificate_intel") as mock_runner:
            from reNgine.temporal_activities import run_certificate_intel_activity
            fake_cert = CertificateIntelligence(host="a.example.com", port=443)
            mock_runner.return_value = [fake_cert]
            result = run_certificate_intel_activity(self.scan.id)
            self.assertEqual(result["count"], 1)
