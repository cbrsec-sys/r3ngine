from django.test import TestCase


class TestScanProfileModel(TestCase):
    def test_profile_can_be_created(self):
        from scanEngine.models import ScanProfile
        profile = ScanProfile.objects.create(
            name='test_profile',
            description='Test profile',
            category='speed',
            rate_limit=100,
            delay=0.0,
            threads=8,
            timeout=10,
            retries=3,
        )
        self.assertEqual(profile.name, 'test_profile')
        self.assertEqual(profile.rate_limit, 100)

    def test_profile_flags_default_false(self):
        from scanEngine.models import ScanProfile
        profile = ScanProfile.objects.create(name='default_test')
        self.assertFalse(profile.passive)
        self.assertFalse(profile.active)
        self.assertFalse(profile.stealth)
        self.assertFalse(profile.headless)

    def test_profile_str_returns_name(self):
        from scanEngine.models import ScanProfile
        profile = ScanProfile(name='my_profile')
        self.assertEqual(str(profile), 'my_profile')

    def test_profile_to_ctx_dict(self):
        from scanEngine.models import ScanProfile
        profile = ScanProfile.objects.create(
            name='to_ctx_test',
            rate_limit=50,
            delay=0.1,
            passive=True,
        )
        ctx_dict = profile.to_ctx_dict()
        self.assertEqual(ctx_dict['rate_limit'], 50)
        self.assertAlmostEqual(ctx_dict['delay'], 0.1)
        self.assertTrue(ctx_dict['passive'])
        profile_zero_delay = ScanProfile.objects.create(name='zero_delay_test', delay=0.0)
        ctx_zero = profile_zero_delay.to_ctx_dict()
        self.assertIn('delay', ctx_zero)
        self.assertEqual(ctx_zero['delay'], 0.0)
