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


class TestScanProfileFixtures(TestCase):
    fixtures = ['scan_profiles']

    def test_fixture_loads_20_profiles(self):
        from scanEngine.models import ScanProfile
        count = ScanProfile.objects.filter(is_builtin=True).count()
        self.assertGreaterEqual(count, 20)

    def test_vps_profile_has_correct_values(self):
        from scanEngine.models import ScanProfile
        vps = ScanProfile.objects.get(name='vps')
        self.assertEqual(vps.threads, 4)
        self.assertEqual(vps.rate_limit, 50)
        self.assertAlmostEqual(vps.delay, 0.1)

    def test_passive_profile_sets_passive_flag(self):
        from scanEngine.models import ScanProfile
        passive = ScanProfile.objects.get(name='passive')
        self.assertTrue(passive.passive)
        ctx = passive.to_ctx_dict()
        self.assertTrue(ctx.get('passive'))

    def test_stealth_profile_sets_stealth_flag(self):
        from scanEngine.models import ScanProfile
        stealth = ScanProfile.objects.get(name='stealth')
        self.assertTrue(stealth.stealth)

    def test_tor_profile_sets_tor_flag(self):
        from scanEngine.models import ScanProfile
        tor = ScanProfile.objects.get(name='tor')
        self.assertTrue(tor.tor)


class TestProfileAppliedToActivity(TestCase):
    def test_rate_limit_from_profile_applied_to_proxy(self):
        from reNgine.temporal_activities import TemporalTaskProxy
        ctx = {
            'scan_history_id': None,
            'profile': {
                'rate_limit': 50,
                'delay': 0.5,
                'threads': 4,
            },
            'yaml_configuration': {},
        }
        proxy = TemporalTaskProxy(ctx, task_name='test_task')
        self.assertEqual(proxy.rate_limit, 50)
        self.assertAlmostEqual(proxy.delay, 0.5)
        self.assertEqual(proxy.threads, 4)

    def test_mode_flags_from_profile_applied_to_proxy(self):
        from reNgine.temporal_activities import TemporalTaskProxy
        ctx = {
            'scan_history_id': None,
            'profile': {
                'passive': True,
                'stealth': True,
            },
            'yaml_configuration': {},
        }
        proxy = TemporalTaskProxy(ctx, task_name='test_task')
        self.assertTrue(proxy.passive)
        self.assertTrue(proxy.stealth)
        self.assertFalse(proxy.tor)

    def test_no_profile_in_ctx_gives_none_attributes(self):
        from reNgine.temporal_activities import TemporalTaskProxy
        ctx = {
            'scan_history_id': None,
            'yaml_configuration': {},
        }
        proxy = TemporalTaskProxy(ctx, task_name='test_task')
        self.assertIsNone(proxy.rate_limit)
        self.assertFalse(proxy.passive)


class TestProfileEmbeddedInScan(TestCase):
    fixtures = ['scan_profiles']

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('profilescanuser', password='pass')
        self.client.force_login(self.user)

    def test_vps_profile_ctx_dict_has_rate_limit(self):
        from scanEngine.models import ScanProfile
        vps = ScanProfile.objects.get(name='vps')
        ctx = vps.to_ctx_dict()
        self.assertEqual(ctx['rate_limit'], 50)
        self.assertEqual(ctx['threads'], 4)

    def test_passive_profile_ctx_dict_has_passive_flag(self):
        from scanEngine.models import ScanProfile
        passive = ScanProfile.objects.get(name='passive')
        ctx = passive.to_ctx_dict()
        self.assertTrue(ctx.get('passive'))
        self.assertNotIn('rate_limit', ctx)

    def test_missing_profile_name_gives_empty_ctx(self):
        from scanEngine.models import ScanProfile
        try:
            profile = ScanProfile.objects.get(name='nonexistent_profile_xyz')
            ctx = profile.to_ctx_dict()
        except ScanProfile.DoesNotExist:
            ctx = {}
        self.assertEqual(ctx, {})


class TestScanProfileAPI(TestCase):
    fixtures = ['scan_profiles']

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('scanprofileapiuser', password='pass')
        self.client.force_login(self.user)

    def test_list_profiles_returns_builtin(self):
        response = self.client.get('/api/scanProfiles/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data.get('results', data) if isinstance(data, dict) else data
        names = [p['name'] for p in items]
        self.assertIn('vps', names)
        self.assertIn('passive', names)
        self.assertIn('stealth', names)

    def test_get_single_profile_by_name(self):
        response = self.client.get('/api/scanProfiles/vps/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'vps')
        self.assertEqual(data['rate_limit'], 50)

    def test_create_custom_profile(self):
        response = self.client.post('/api/scanProfiles/', {
            'name': 'my_custom_test',
            'description': 'Custom test profile',
            'category': 'speed',
            'rate_limit': 75,
            'threads': 10,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        from scanEngine.models import ScanProfile
        ScanProfile.objects.filter(name='my_custom_test').delete()

    def test_cannot_delete_builtin_profile(self):
        response = self.client.delete('/api/scanProfiles/vps/')
        self.assertIn(response.status_code, [400, 403])

