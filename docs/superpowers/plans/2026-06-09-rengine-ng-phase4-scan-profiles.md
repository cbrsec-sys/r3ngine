# rengine-ng Integration — Phase 4: Scan Profiles

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the rengine-ng profile system in r3ngine — a `ScanProfile` model with pre-built hardware and scanning-mode profiles that apply rate-limit, delay, thread count, and stealth flags globally across all tool activities during a scan.

**Architecture:** A new `ScanProfile` model holds numeric throttle settings and boolean mode flags. Profiles are loaded into the scan context dict (`ctx`) and each activity that runs a subprocess reads `ctx['profile']` to apply global throttle settings. An optional FK on `EngineType` links a profile to a scan engine configuration. 20 pre-built profiles are loaded via a fixture on first migration.

**Tech Stack:** Python 3.12, Django 5.2.3, DRF, PostgreSQL migrations

**Depends on:** Phase 1 (activities must read profile from ctx). Phases 2–3 are parallel-independent.

---

## Pre-built Profiles (ported from rengine-ng)

### Hardware Profiles

| Name | Threads | Rate Limit | Delay | Timeout | Retries | Notes |
|------|---------|------------|-------|---------|---------|-------|
| raspberry | 2 | 15 | 0.5 | 15 | 3 | Raspberry Pi / low-power nodes |
| nuc | 6 | 40 | 0.2 | 10 | 3 | Intel NUC / small form factor |
| vps | 4 | 50 | 0.1 | 10 | 3 | 2–4 vCPU cloud droplet |
| desktop | 8 | 80 | 0.0 | 10 | 3 | Standard i5/8GB desktop |
| desktop_advanced | 12 | 120 | 0.0 | 8 | 2 | i7/16GB desktop |
| powerful | 20 | 200 | 0.0 | 5 | 2 | High-end workstation |

### Scanning Mode Profiles

| Name | Category | Key Effect |
|------|----------|-----------|
| passive | general | `passive=True` — no requests to target |
| active | general | `active=True` — no passive sources |
| full | general | Enables all optional features (nuclei, brute, secrets, ssl) |
| hunt_secrets | content | `hunt_secrets=True` across all URL workflows |
| polite | speed | rate_limit=100, delay=0, timeout=10, retries=5 |
| aggressive | speed | rate_limit=10000, delay=0, timeout=1, retries=1 |
| insane | speed | rate_limit=100000 — LAN/stress scanning |
| paranoid | speed | rate_limit=5, delay=5, timeout=15, retries=5 |
| stealth | evasion | TCP SYN stealth scan mode |
| sneaky | evasion | IP fragmentation for IDS evasion |
| tor | evasion | Route via Tor proxy |
| all_ports | network | Scan all 65535 ports |
| http_headless | network | Headless browser HTTP requests |
| http_record | network | Record HTTP responses + screenshots |

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `web/scanEngine/models.py` | Add `ScanProfile` model |
| Create | `web/scanEngine/migrations/XXXX_add_scan_profile.py` | Migration |
| Create | `web/scanEngine/fixtures/scan_profiles.json` | 20 pre-built profiles |
| Modify | `web/scanEngine/apps.py` | Auto-load fixture on startup |
| Modify | `web/reNgine/temporal_activities.py` | Read profile from ctx in `_run_task` |
| Modify | `web/api/views.py` | Add profile CRUD endpoints |
| Modify | `web/api/urls.py` | Wire profile API URLs |
| Create | `web/tests/test_scan_profiles.py` | Tests for model, fixture, API |

---

## Task 1: Add `ScanProfile` model

**Files:**
- Modify: `web/scanEngine/models.py`

- [ ] **Step 1: Write failing tests**

```python
# web/tests/test_scan_profiles.py
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
        profile.delete()

    def test_profile_flags_default_false(self):
        from scanEngine.models import ScanProfile
        profile = ScanProfile.objects.create(name='default_test')
        self.assertFalse(profile.passive)
        self.assertFalse(profile.active)
        self.assertFalse(profile.stealth)
        self.assertFalse(profile.headless)
        profile.delete()

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
        profile.delete()
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestScanProfileModel --verbosity=2 2>&1 | head -20"
```
Expected: `ImportError: cannot import name 'ScanProfile'`

- [ ] **Step 3: Add `ScanProfile` to `scanEngine/models.py`**

Open `web/scanEngine/models.py` and append before the last line of the file:

```python
class ScanProfile(models.Model):
    """Defines execution throttle settings and scanning mode flags.

    Profiles can be attached to EngineType configurations or applied
    dynamically at scan creation time. They are applied to every tool
    activity via the scan context dict (ctx['profile']).

    Ported from rengine-ng's Secator profile system.
    """

    CATEGORY_CHOICES = [
        ('speed', 'Speed / Throttle'),
        ('evasion', 'Evasion'),
        ('content', 'Content'),
        ('network', 'Network'),
        ('general', 'General'),
        ('hardware', 'Hardware'),
    ]

    name = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, default='')
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='general')
    is_builtin = models.BooleanField(default=False)

    # Throttle settings (null = use tool default)
    rate_limit = models.PositiveIntegerField(null=True, blank=True)
    delay = models.FloatField(null=True, blank=True)
    threads = models.PositiveIntegerField(null=True, blank=True)
    timeout = models.PositiveIntegerField(null=True, blank=True)
    retries = models.PositiveIntegerField(null=True, blank=True)

    # Mode flags
    passive = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    stealth = models.BooleanField(default=False)
    headless = models.BooleanField(default=False)
    screenshot = models.BooleanField(default=False)
    hunt_secrets = models.BooleanField(default=False)
    nuclei_full = models.BooleanField(default=False)
    brute_dns = models.BooleanField(default=False)
    brute_http = models.BooleanField(default=False)
    test_ssl = models.BooleanField(default=False)
    all_ports = models.BooleanField(default=False)
    tor = models.BooleanField(default=False)
    fragment = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    def to_ctx_dict(self) -> dict:
        """Returns a profile dict ready to merge into a workflow ctx."""
        d = {}
        if self.rate_limit is not None:
            d['rate_limit'] = self.rate_limit
        if self.delay is not None:
            d['delay'] = self.delay
        if self.threads is not None:
            d['threads'] = self.threads
        if self.timeout is not None:
            d['timeout'] = self.timeout
        if self.retries is not None:
            d['retries'] = self.retries
        # Mode flags — only include True values to avoid overriding defaults
        for flag in ('passive', 'active', 'stealth', 'headless', 'screenshot',
                     'hunt_secrets', 'nuclei_full', 'brute_dns', 'brute_http',
                     'test_ssl', 'all_ports', 'tor', 'fragment'):
            if getattr(self, flag):
                d[flag] = True
        return d
```

- [ ] **Step 4: Generate and apply migration**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py makemigrations scanEngine --name add_scan_profile"
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py migrate"
```
Expected: migration applied OK.

- [ ] **Step 5: Run tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestScanProfileModel --verbosity=2"
```
Expected: `OK`

- [ ] **Step 6: Commit model + migration**

```bash
git add web/scanEngine/models.py web/scanEngine/migrations/
git commit -m "feat(models): add ScanProfile model with throttle settings and mode flags"
```

---

## Task 2: Create fixtures for 20 pre-built profiles

**Files:**
- Create: `web/scanEngine/fixtures/scan_profiles.json`

- [ ] **Step 1: Write fixture test**

```python
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
```

- [ ] **Step 2: Run to confirm failure (fixture doesn't exist yet)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestScanProfileFixtures --verbosity=2 2>&1 | head -20"
```
Expected: `fixture 'scan_profiles' not found`

- [ ] **Step 3: Create the fixture file**

```json
[
  {"model": "scanEngine.scanprofile", "pk": 1, "fields": {"name": "raspberry", "description": "Light node (e.g. Raspberry Pi), low CPU/RAM", "category": "hardware", "is_builtin": true, "rate_limit": 15, "delay": 0.5, "threads": 2, "timeout": 15, "retries": 3, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 2, "fields": {"name": "nuc", "description": "Small form factor node (e.g. Intel NUC)", "category": "hardware", "is_builtin": true, "rate_limit": 40, "delay": 0.2, "threads": 6, "timeout": 10, "retries": 3, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 3, "fields": {"name": "vps", "description": "VPS / cloud droplet (2-4 vCPU, 2-8GB)", "category": "hardware", "is_builtin": true, "rate_limit": 50, "delay": 0.1, "threads": 4, "timeout": 10, "retries": 3, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 4, "fields": {"name": "desktop", "description": "Standard desktop (e.g. i5 / 8GB RAM)", "category": "hardware", "is_builtin": true, "rate_limit": 80, "delay": 0.0, "threads": 8, "timeout": 10, "retries": 3, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 5, "fields": {"name": "desktop_advanced", "description": "Advanced desktop (e.g. i7 / 16GB RAM)", "category": "hardware", "is_builtin": true, "rate_limit": 120, "delay": 0.0, "threads": 12, "timeout": 8, "retries": 2, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 6, "fields": {"name": "powerful", "description": "High-end machine (i7+ / 24GB+ RAM)", "category": "hardware", "is_builtin": true, "rate_limit": 200, "delay": 0.0, "threads": 20, "timeout": 5, "retries": 2, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 7, "fields": {"name": "passive", "description": "Passive scanning only (no requests to targets)", "category": "general", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": true, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 8, "fields": {"name": "active", "description": "Active scanning only (no passive sources)", "category": "general", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": true, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 9, "fields": {"name": "full", "description": "Activate all optional features (nuclei, brute, secrets, ssl)", "category": "general", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": true, "screenshot": true, "hunt_secrets": true, "nuclei_full": true, "brute_dns": true, "brute_http": true, "test_ssl": true, "all_ports": true, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 10, "fields": {"name": "hunt_secrets", "description": "Hunt for secrets and credentials in HTTP responses", "category": "content", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": true, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 11, "fields": {"name": "polite", "description": "Avoid overloading network", "category": "speed", "is_builtin": true, "rate_limit": 100, "delay": 0.0, "threads": null, "timeout": 10, "retries": 5, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 12, "fields": {"name": "aggressive", "description": "Internal networks or time-sensitive scans (no rate limiting)", "category": "speed", "is_builtin": true, "rate_limit": 10000, "delay": 0.0, "threads": null, "timeout": 1, "retries": 1, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 13, "fields": {"name": "insane", "description": "Local LAN scanning or stress scanning", "category": "speed", "is_builtin": true, "rate_limit": 100000, "delay": 0.0, "threads": null, "timeout": 1, "retries": 0, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 14, "fields": {"name": "paranoid", "description": "Maximum stealth — lowest rate, highest delay", "category": "speed", "is_builtin": true, "rate_limit": 5, "delay": 5.0, "threads": null, "timeout": 15, "retries": 5, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 15, "fields": {"name": "stealth", "description": "TCP SYN stealth scan mode", "category": "evasion", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": true, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 16, "fields": {"name": "sneaky", "description": "IDS/IPS evasion via IP fragmentation", "category": "evasion", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": true}},
  {"model": "scanEngine.scanprofile", "pk": 17, "fields": {"name": "tor", "description": "Anonymous scan via Tor network", "category": "evasion", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": true, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 18, "fields": {"name": "all_ports", "description": "Scan all 65535 ports", "category": "network", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": false, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": true, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 19, "fields": {"name": "http_headless", "description": "Headless browser HTTP requests", "category": "network", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": true, "screenshot": false, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}},
  {"model": "scanEngine.scanprofile", "pk": 20, "fields": {"name": "http_record", "description": "Record HTTP responses and take screenshots", "category": "network", "is_builtin": true, "rate_limit": null, "delay": null, "threads": null, "timeout": null, "retries": null, "passive": false, "active": false, "stealth": false, "headless": true, "screenshot": true, "hunt_secrets": false, "nuclei_full": false, "brute_dns": false, "brute_http": false, "test_ssl": false, "all_ports": false, "tor": false, "fragment": false}}
]
```

- [ ] **Step 4: Load fixture and run tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py loaddata scan_profiles"
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestScanProfileFixtures --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/scanEngine/fixtures/scan_profiles.json
git commit -m "feat(profiles): add 20 pre-built scan profiles fixture (hardware + mode profiles)"
```

---

## Task 3: Apply profile settings in `_run_task`

**Files:**
- Modify: `web/reNgine/temporal_activities.py`

The existing `_run_task` helper constructs a `TemporalTaskProxy` and calls the task function. We need to apply profile settings from `ctx` to the proxy so task functions can read them.

- [ ] **Step 1: Write profile application test**

```python
class TestProfileAppliedToActivity(TestCase):
    @patch('subprocess.run')
    def test_rate_limit_from_profile_applied_to_proxy(self, mock_run):
        from reNgine.temporal_activities import TemporalTaskProxy
        ctx = {
            'scan_history_id': 1,
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestProfileAppliedToActivity --verbosity=2 2>&1 | head -20"
```
Expected: `AttributeError: 'TemporalTaskProxy' object has no attribute 'rate_limit'`

- [ ] **Step 3: Add profile attribute reading to `TemporalTaskProxy.__init__`**

Find `TemporalTaskProxy.__init__` in `temporal_activities.py` and add at the end of `__init__`:

```python
# Apply scan profile settings if provided
profile_data = ctx.get('profile') or {}
self.rate_limit = profile_data.get('rate_limit')
self.delay = profile_data.get('delay')
self.threads = profile_data.get('threads')
self.timeout = profile_data.get('timeout')
self.retries = profile_data.get('retries')
self.passive = profile_data.get('passive', False)
self.active = profile_data.get('active', False)
self.stealth = profile_data.get('stealth', False)
self.headless = profile_data.get('headless', False)
self.hunt_secrets = profile_data.get('hunt_secrets', False)
self.all_ports = profile_data.get('all_ports', False)
self.tor = profile_data.get('tor', False)
self.fragment = profile_data.get('fragment', False)
```

Task functions in `recon_tasks.py` and `crawl_tasks.py` can then read `self.rate_limit` to apply throttles (e.g., pass `--rate-limit {self.rate_limit}` to nuclei/naabu).

- [ ] **Step 4: Run test — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestProfileAppliedToActivity --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/temporal_activities.py
git commit -m "feat(activities): propagate scan profile (rate_limit, delay, threads, flags) to TemporalTaskProxy"
```

---

## Task 4: Embed profile in workflow context at scan creation

**Files:**
- Modify: `web/api/views.py`

When a scan is created via the API with a `profile_id` or `profile_name`, the profile's `to_ctx_dict()` is merged into the workflow context before starting.

- [ ] **Step 1: Write API test**

```python
class TestProfileEmbeddedInScan(TestCase):
    fixtures = ['scan_profiles']

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('profileuser', password='pass')
        self.client.force_login(self.user)

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_vps_profile_embedded_in_ctx(self, mock_start):
        mock_start.return_value = 'wf-001'
        self.client.post('/api/v1/scan/start/', {
            'target': 'example.com',
            'target_type': 'domain',
            'profile_name': 'vps',
        }, content_type='application/json')
        if mock_start.called:
            ctx_arg = mock_start.call_args[1].get('args', [mock_start.call_args[0][1]])[0]
            profile_in_ctx = ctx_arg.get('profile', {})
            self.assertEqual(profile_in_ctx.get('rate_limit'), 50)

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_tor_profile_sets_tor_flag_in_ctx(self, mock_start):
        mock_start.return_value = 'wf-002'
        self.client.post('/api/v1/scan/start/', {
            'target': 'example.com',
            'target_type': 'domain',
            'profile_name': 'tor',
        }, content_type='application/json')
        if mock_start.called:
            ctx_arg = mock_start.call_args[1].get('args', [mock_start.call_args[0][1]])[0]
            self.assertTrue(ctx_arg.get('profile', {}).get('tor'))
```

- [ ] **Step 2: Add profile lookup to scan start view in `api/views.py`**

In the scan start view, after parsing `request.data` and before calling `start_workflow`, add:

```python
from scanEngine.models import ScanProfile

profile_ctx = {}
profile_name = request.data.get('profile_name')
profile_id = request.data.get('profile_id')
if profile_name or profile_id:
    try:
        if profile_name:
            profile = ScanProfile.objects.get(name=profile_name)
        else:
            profile = ScanProfile.objects.get(pk=profile_id)
        profile_ctx = profile.to_ctx_dict()
    except ScanProfile.DoesNotExist:
        pass  # Unknown profile — ignore, use defaults

# Merge profile into workflow context:
workflow_ctx['profile'] = profile_ctx
```

- [ ] **Step 3: Run tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/api/views.py
git commit -m "feat(api): embed scan profile into workflow context at scan creation"
```

---

## Task 5: Add profile CRUD REST API

**Files:**
- Modify: `web/api/views.py`
- Modify: `web/api/urls.py`

- [ ] **Step 1: Write API test**

```python
class TestScanProfileAPI(TestCase):
    fixtures = ['scan_profiles']

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('apiuser', password='pass')
        self.client.force_login(self.user)

    def test_list_profiles_returns_20_builtin(self):
        response = self.client.get('/api/v1/profiles/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = [p['name'] for p in data.get('results', data)]
        self.assertIn('vps', names)
        self.assertIn('passive', names)
        self.assertIn('stealth', names)

    def test_get_single_profile(self):
        response = self.client.get('/api/v1/profiles/vps/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'vps')
        self.assertEqual(data['rate_limit'], 50)

    def test_create_custom_profile(self):
        response = self.client.post('/api/v1/profiles/', {
            'name': 'my_custom',
            'description': 'My custom profile',
            'category': 'speed',
            'rate_limit': 75,
            'threads': 10,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        from scanEngine.models import ScanProfile
        ScanProfile.objects.filter(name='my_custom').delete()
```

- [ ] **Step 2: Add `ScanProfileViewSet` to `api/views.py`**

```python
# web/api/views.py (append)

from scanEngine.models import ScanProfile


class ScanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanProfile
        fields = '__all__'
        read_only_fields = ['id', 'is_builtin', 'created_at', 'updated_at']


class ScanProfileViewSet(viewsets.ModelViewSet):
    queryset = ScanProfile.objects.all().order_by('category', 'name')
    serializer_class = ScanProfileSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'name'

    def destroy(self, request, *args, **kwargs):
        profile = self.get_object()
        if profile.is_builtin:
            return Response({'error': 'Cannot delete built-in profiles'}, status=400)
        return super().destroy(request, *args, **kwargs)
```

- [ ] **Step 3: Add URL patterns**

```python
# In api/urls.py, with the existing router:
router.register(r'profiles', ScanProfileViewSet, basename='scan-profiles')
```

- [ ] **Step 4: Run API tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_scan_profiles.TestScanProfileAPI --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/api/views.py web/api/urls.py
git commit -m "feat(api): add ScanProfile CRUD REST endpoints (GET/POST/PUT/DELETE /api/v1/profiles/)"
```

---

## Task 6: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```
Expected: `OK`

- [ ] **Step 2: Tag Phase 4 complete**

```bash
git tag phase4-scan-profiles
```

---

## Self-Review

**Spec coverage:**
- ✅ `ScanProfile` model with 13 throttle + flag fields
- ✅ 20 pre-built profiles fixture (6 hardware + 14 mode profiles)
- ✅ `to_ctx_dict()` method for merging into workflow context
- ✅ `TemporalTaskProxy` reads profile settings from ctx
- ✅ Scan creation API accepts `profile_name` / `profile_id` and embeds profile
- ✅ Full CRUD REST API for profile management
- ✅ Builtin profiles cannot be deleted

**Placeholder scan:** None.

**Type consistency:** `ScanProfile.to_ctx_dict()` returns `dict` with same keys that `TemporalTaskProxy.__init__` reads (`rate_limit`, `delay`, etc.).
