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
