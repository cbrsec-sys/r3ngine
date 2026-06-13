# AD Plugin: Attack Path Layer + Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Active Directory plugin with BloodHound-derived attack path queries (DA paths, Kerberoastable, AS-REP Roastable, unconstrained delegation, ACL abuse), plugin-level and per-assessment configuration modals, and a HOW_TO_BUILD.md plugin authoring guide.

**Architecture:** Extend existing files only — no new subpackages. BloodHound parser gains ACL edge ingestion and Kerberos property extraction. Neo4j graph manager gains 5 attack path query methods. One new API action exposes queries. One new React page renders 4 tabs. Two config modals added: singleton `ADPluginConfig` for plugin-level settings, existing `ADAssessment.config` JSONField for per-assessment settings.

**Tech Stack:** Python/Django (backend), Neo4j Cypher (graph queries), React 18 + MUI (frontend), `@tanstack/react-query` (data), Vite Module Federation (plugin build).

---

## File Map

### Plugin repo: `r3ngine-plugins/active_directory/`

| File | Change |
|------|--------|
| `backend/graph/schema.py` | Add 7 ACL relationship constants + 7 constraint statements |
| `backend/ingestion/bloodhound_parser.py` | Extend `parse_users`, `parse_computers`, add `parse_aces`, `_write_acl_edges` |
| `backend/graph/manager.py` | Add `create_acl_edge`, `find_da_paths`, `find_kerberoastable`, `find_asreproastable`, `find_unconstrained_delegation`, `find_acl_abuse` |
| `backend/models.py` | Add `ADPluginConfig` singleton model |
| `backend/serializers.py` | Add `ADPluginConfigSerializer` |
| `backend/api.py` | Add `attack_paths` action; add `ADPluginConfigView` |
| `backend/api_urls.py` | Register `ADPluginConfigView` |
| `backend/migrations/0004_adpluginconfig.py` | Migration for `ADPluginConfig` |
| `ui/src/api/adApi.ts` | Add `useAttackPaths`, `usePluginConfig`, `useUpdatePluginConfig`, `useUpdateAssessmentConfig` |
| `ui/src/pages/ADAttackPathsPage.tsx` | New 4-tab attack paths page |
| `ui/src/components/ADPluginConfigModal.tsx` | Plugin-level settings modal |
| `ui/src/components/ADAssessmentConfigModal.tsx` | Per-assessment config modal |
| `ui/src/pages/ADAssessmentDetailPage.tsx` | Add settings icon → `ADAssessmentConfigModal` |
| `ui/src/pages/ADAssessmentsPage.tsx` | Add gear icon → `ADPluginConfigModal` |
| `ui/src/pages/ADPluginApp.tsx` | Add `attack_paths` route |
| `HOW_TO_BUILD.md` | Full plugin authoring guide |

---

## Task 1: Schema constants + ACL constraints

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/graph/schema.py`

- [ ] **Step 1: Write the failing test**

In the Django container, create test `tests/test_ad_schema.py` in the plugin test dir. But since this plugin runs tests via Django's test runner in the container, write the test inline using the container shell.

The schema changes have no runtime behavior to test beyond presence, but write a smoke test for the parser that uses these constants later. For now, just verify the file has the constants.

Actually, the schema is data, not behavior — skip the dedicated test and verify the constants are present in the parser test (Task 3). Jump to implementation.

- [ ] **Step 2: Add 7 ACL relationship constants to `schema.py`**

Append to the Relationship Types section (after `AD_ROUTES_THROUGH = 'AD_ROUTES_THROUGH'`):

```python
# Attack path / ACL edge types (BloodHound-derived)
AD_GENERIC_ALL        = 'AD_GENERIC_ALL'
AD_WRITE_DACL         = 'AD_WRITE_DACL'
AD_WRITE_OWNER        = 'AD_WRITE_OWNER'
AD_FORCE_CHANGE_PW    = 'AD_FORCE_CHANGE_PW'
AD_HAS_SESSION        = 'AD_HAS_SESSION'
AD_ADMIN_TO           = 'AD_ADMIN_TO'
AD_ALLOWED_TO_DELEGATE = 'AD_ALLOWED_TO_DELEGATE'
```

- [ ] **Step 3: Add 7 ACL edge constraint statements to `CONSTRAINT_STATEMENTS`**

Append to `CONSTRAINT_STATEMENTS` list:

```python
    "CREATE CONSTRAINT ad_acl_generic_all_unique IF NOT EXISTS "
    "FOR ()-[r:AD_GENERIC_ALL]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_write_dacl_unique IF NOT EXISTS "
    "FOR ()-[r:AD_WRITE_DACL]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_write_owner_unique IF NOT EXISTS "
    "FOR ()-[r:AD_WRITE_OWNER]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_force_change_pw_unique IF NOT EXISTS "
    "FOR ()-[r:AD_FORCE_CHANGE_PW]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_has_session_unique IF NOT EXISTS "
    "FOR ()-[r:AD_HAS_SESSION]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_admin_to_unique IF NOT EXISTS "
    "FOR ()-[r:AD_ADMIN_TO]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",

    "CREATE CONSTRAINT ad_acl_allowed_to_delegate_unique IF NOT EXISTS "
    "FOR ()-[r:AD_ALLOWED_TO_DELEGATE]-() REQUIRE (r.source_sid, r.target_sid, r.assessment_id) IS UNIQUE",
```

**Note:** Neo4j relationship property uniqueness constraints require Neo4j Enterprise. On Community, these will be skipped (the `ensure_schema` method already wraps each statement in try/except). This is fine — on Community edition, ACL edges will still be created, just without uniqueness enforcement. The MERGE in `create_acl_edge` will handle deduplication at query time.

- [ ] **Step 4: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/graph/schema.py
git commit -m "feat(ad-plugin): add 7 ACL relationship type constants to schema"
```

---

## Task 2: ADPluginConfig model + migration

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/models.py`
- Create: `r3ngine-plugins/active_directory/backend/migrations/0004_adpluginconfig.py`

- [ ] **Step 1: Write the failing test**

Test file: run inside container with:
```
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_plugin_config
```

The test checks:
- `ADPluginConfig.get()` returns a singleton (same pk on repeated calls)
- `ADPluginConfig.get_setting('max_path_length', 10)` returns 10 by default
- Saving a new value is reflected on next `get()`

Write the test at `r3ngine-plugins/active_directory/tests/test_plugin_config.py`:

```python
from django.test import TestCase
from active_directory.backend.models import ADPluginConfig


class ADPluginConfigTest(TestCase):
    def test_get_creates_singleton(self):
        cfg1 = ADPluginConfig.get()
        cfg2 = ADPluginConfig.get()
        self.assertEqual(cfg1.pk, cfg2.pk)
        self.assertEqual(ADPluginConfig.objects.count(), 1)

    def test_get_setting_returns_default(self):
        self.assertEqual(ADPluginConfig.get_setting('max_path_length', 10), 10)

    def test_get_setting_returns_saved_value(self):
        cfg = ADPluginConfig.get()
        cfg.max_path_length = 5
        cfg.save()
        self.assertEqual(ADPluginConfig.get_setting('max_path_length', 10), 5)
```

- [ ] **Step 2: Run test to confirm failure**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_plugin_config
```
Expected: ImportError or ModuleNotFoundError (model doesn't exist yet).

- [ ] **Step 3: Add `ADPluginConfig` to `models.py`**

Append to end of `r3ngine-plugins/active_directory/backend/models.py`:

```python


class ADPluginConfig(models.Model):
    """Singleton configuration for the AD plugin."""
    neo4j_bolt_url = models.CharField(max_length=500, blank=True, default='')
    max_path_length = models.IntegerField(default=10)
    bloodhound_ce_url = models.CharField(max_length=500, blank=True, default='')
    default_phases = models.JSONField(default=list)

    class Meta:
        db_table = 'plugin_ad_config'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_setting(cls, key, default=None):
        return getattr(cls.get(), key, default)
```

- [ ] **Step 4: Create migration**

Write `r3ngine-plugins/active_directory/backend/migrations/0004_adpluginconfig.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('active_directory', '0003_adevidencelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ADPluginConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('neo4j_bolt_url', models.CharField(blank=True, default='', max_length=500)),
                ('max_path_length', models.IntegerField(default=10)),
                ('bloodhound_ce_url', models.CharField(blank=True, default='', max_length=500)),
                ('default_phases', models.JSONField(default=list)),
            ],
            options={
                'db_table': 'plugin_ad_config',
            },
        ),
    ]
```

- [ ] **Step 5: Apply migration in container**

```bash
docker exec r3ngine-web-1 python3 manage.py migrate active_directory
```
Expected: `Applying active_directory.0004_adpluginconfig... OK`

- [ ] **Step 6: Run tests**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_plugin_config
```
Expected: `Ran 3 tests in ...s OK`

- [ ] **Step 7: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/models.py active_directory/backend/migrations/0004_adpluginconfig.py active_directory/tests/test_plugin_config.py
git commit -m "feat(ad-plugin): add ADPluginConfig singleton model + migration"
```

---

## Task 3: BloodHound parser — ACL edges + Kerberos properties

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/ingestion/bloodhound_parser.py`

- [ ] **Step 1: Write the failing tests**

Write test file `r3ngine-plugins/active_directory/tests/test_bloodhound_parser.py`:

```python
from django.test import TestCase
from active_directory.backend.ingestion.bloodhound_parser import BloodHoundParser


SAMPLE_USER = {
    'Properties': {
        'name': 'alice@CORP.LOCAL',
        'objectid': 'S-1-5-21-111-222-333-1234',
        'enabled': True,
        'admincount': False,
        'pwdneverexpires': False,
        'lastlogon': 1700000000,
        'domain': 'CORP.LOCAL',
        'serviceprincipalnames': ['MSSQLSvc/sql01.corp.local:1433'],
        'dontreqpreauth': False,
    },
    'PrimaryGroupSid': 'S-1-5-21-111-222-333-513',
    'Aces': [
        {'RightName': 'GenericAll', 'PrincipalSID': 'S-1-5-21-111-222-333-512',
         'PrincipalType': 'Group', 'IsInherited': False},
        {'RightName': 'Irrelevant', 'PrincipalSID': 'S-1-5-21-111-222-333-999',
         'PrincipalType': 'Group', 'IsInherited': False},
    ],
}

SAMPLE_COMPUTER = {
    'Properties': {
        'name': 'DC01.CORP.LOCAL',
        'objectid': 'S-1-5-21-111-222-333-1001',
        'enabled': True,
        'operatingsystem': 'Windows Server 2019',
        'lastlogontimestamp': 1700000000,
        'domain': 'CORP.LOCAL',
        'unconstraineddelegation': True,
        'allowedtodelegate': ['ldap/dc02.corp.local'],
    },
}


class BloodHoundParserKerberosTest(TestCase):
    def test_parse_users_extracts_spn(self):
        users = BloodHoundParser.parse_users([SAMPLE_USER])
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['spn'], ['MSSQLSvc/sql01.corp.local:1433'])

    def test_parse_users_kerberoastable_flag(self):
        users = BloodHoundParser.parse_users([SAMPLE_USER])
        self.assertTrue(users[0]['kerberoastable'])

    def test_parse_users_dont_req_preauth(self):
        users = BloodHoundParser.parse_users([SAMPLE_USER])
        self.assertFalse(users[0]['dont_req_preauth'])

    def test_parse_computers_unconstrained_delegation(self):
        computers = BloodHoundParser.parse_computers([SAMPLE_COMPUTER])
        self.assertEqual(len(computers), 1)
        self.assertTrue(computers[0]['unconstrained_delegation'])

    def test_parse_computers_constrained_delegation_targets(self):
        computers = BloodHoundParser.parse_computers([SAMPLE_COMPUTER])
        self.assertEqual(computers[0]['constrained_delegation_targets'], ['ldap/dc02.corp.local'])


class BloodHoundParserAcesTest(TestCase):
    def test_parse_aces_returns_mapped_rights(self):
        aces = BloodHoundParser.parse_aces(SAMPLE_USER, 'S-1-5-21-111-222-333-1234')
        # Only GenericAll maps — Irrelevant is ignored
        self.assertEqual(len(aces), 1)
        self.assertEqual(aces[0]['right'], 'GenericAll')
        self.assertEqual(aces[0]['source_sid'], 'S-1-5-21-111-222-333-1234')
        self.assertEqual(aces[0]['target_sid'], 'S-1-5-21-111-222-333-512')
        self.assertEqual(aces[0]['target_type'], 'Group')
        self.assertFalse(aces[0]['is_inherited'])

    def test_parse_aces_empty_on_no_aces(self):
        aces = BloodHoundParser.parse_aces({}, 'S-1-1-1')
        self.assertEqual(aces, [])
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_bloodhound_parser
```
Expected: `AttributeError` or `AssertionError` (spn/kerberoastable fields don't exist yet).

- [ ] **Step 3: Extend `parse_users` in `bloodhound_parser.py`**

Replace the `results.append({...})` block in `parse_users` with:

```python
            spn = props.get('serviceprincipalnames', [])
            results.append({
                'sam_account_name': sam,
                'display_name': props.get('displayname', sam),
                'email': props.get('email', ''),
                'enabled': props.get('enabled', True),
                'admin_count': 1 if props.get('admincount') else 0,
                'password_never_expires': props.get('pwdneverexpires', False),
                'last_logon': str(props.get('lastlogon', '')),
                'sid': props.get('objectid', ''),
                'domain': props.get('domain', ''),
                'primary_group_sid': entry.get('PrimaryGroupSid', ''),
                'spn': spn,
                'dont_req_preauth': props.get('dontreqpreauth', False),
                'kerberoastable': bool(spn) and props.get('enabled', True),
            })
```

- [ ] **Step 4: Extend `parse_computers` in `bloodhound_parser.py`**

Replace the `results.append({...})` block in `parse_computers` with:

```python
            results.append({
                'name': name,
                'fqdn': props.get('name', ''),
                'os': props.get('operatingsystem', ''),
                'os_version': '',
                'enabled': props.get('enabled', True),
                'last_logon': str(props.get('lastlogontimestamp', '')),
                'sid': props.get('objectid', ''),
                'domain': props.get('domain', ''),
                'unconstrained_delegation': props.get('unconstraineddelegation', False),
                'constrained_delegation_targets': props.get('allowedtodelegate', []),
            })
```

- [ ] **Step 5: Add `parse_aces` classmethod**

Add after `parse_domains` (before `ingest_from_directory`):

```python
    _ACE_RIGHT_NAMES = {
        'GenericAll', 'WriteDacl', 'WriteOwner',
        'ForceChangePassword', 'HasSession', 'AdminTo', 'AllowedToDelegate',
    }

    @classmethod
    def parse_aces(cls, entry: dict, source_sid: str) -> list:
        """Extract ACL edges from a BloodHound entry's Aces list."""
        result = []
        for ace in entry.get('Aces', []):
            right = ace.get('RightName')
            if right not in cls._ACE_RIGHT_NAMES:
                continue
            target_sid = ace.get('PrincipalSID')
            if not target_sid:
                continue
            result.append({
                'source_sid': source_sid,
                'target_sid': target_sid,
                'target_type': ace.get('PrincipalType', 'Unknown'),
                'right': right,
                'is_inherited': ace.get('IsInherited', False),
            })
        return result
```

- [ ] **Step 6: Add `_write_acl_edges` and update `_write_to_graph`**

Add `_write_acl_edges` classmethod before `_write_to_graph`:

```python
    _RIGHT_TO_REL = {
        'GenericAll': 'AD_GENERIC_ALL',
        'WriteDacl': 'AD_WRITE_DACL',
        'WriteOwner': 'AD_WRITE_OWNER',
        'ForceChangePassword': 'AD_FORCE_CHANGE_PW',
        'HasSession': 'AD_HAS_SESSION',
        'AdminTo': 'AD_ADMIN_TO',
        'AllowedToDelegate': 'AD_ALLOWED_TO_DELEGATE',
    }

    @classmethod
    def _write_acl_edges(cls, assessment_id: int, aces: list) -> None:
        if not aces:
            return
        try:
            from ..graph.manager import ADGraphManager
            with ADGraphManager() as mgr:
                for ace in aces:
                    rel = cls._RIGHT_TO_REL.get(ace['right'])
                    if rel:
                        mgr.create_acl_edge(
                            ace['source_sid'], ace['target_sid'],
                            ace['target_type'], rel, assessment_id,
                        )
        except Exception as exc:
            logger.error(f"[BH] ACL edge write failed: {exc}")
```

Update `_write_to_graph` to collect ACEs and call `_write_acl_edges`:

```python
    @classmethod
    def _write_to_graph(cls, assessment_id: int, parsed: dict) -> None:
        try:
            from ..graph.manager import ADGraphManager
            all_aces = []
            with ADGraphManager() as mgr:
                for domain in parsed.get('domains', []):
                    mgr.upsert_domain({**domain, 'assessment_id': assessment_id})
                for user in parsed.get('users', []):
                    mgr.upsert_user({**user, 'assessment_id': assessment_id})
                for group in parsed.get('groups', []):
                    mgr.upsert_group({**group, 'assessment_id': assessment_id})
                    for member in group.get('members', []):
                        if member['sid'] and member['type']:
                            label_map = {
                                'User': 'ADUser',
                                'Computer': 'ADComputer',
                                'Group': 'ADGroup',
                            }
                            label = label_map.get(member['type'])
                            if label:
                                try:
                                    mgr.create_membership_relationship(
                                        member['sid'], label,
                                        group['sid'], assessment_id)
                                except Exception as exc:
                                    logger.warning(f"[BH] Membership edge skipped (sid={member['sid']}): {exc}")
                for computer in parsed.get('computers', []):
                    mgr.upsert_computer({**computer, 'assessment_id': assessment_id})

            # Collect ACEs from all entities that have them
            for entity_list in (parsed.get('users', []), parsed.get('groups', []),
                                parsed.get('computers', [])):
                for entry in entity_list:
                    source_sid = entry.get('sid', '')
                    if source_sid and '_raw_entry' in entry:
                        all_aces.extend(cls.parse_aces(entry['_raw_entry'], source_sid))

            cls._write_acl_edges(assessment_id, all_aces)
        except Exception as exc:
            logger.error(f"[BH] Graph write failed: {exc}")
```

**Note:** The ACE data comes from the raw BloodHound entry, not the parsed dict. To pass it through, also update `parse_users`, `parse_groups`, `parse_computers` to stash `'_raw_entry': entry` in each result dict, and update `ingest_from_directory` to collect ACEs inline during parsing (before `_write_to_graph` is called). Full update to `ingest_from_directory`:

```python
    @classmethod
    def ingest_from_directory(
            cls, directory: str, assessment_id: int,
            db_write: bool = True) -> dict:
        summary = {'users': 0, 'groups': 0, 'computers': 0, 'domains': 0, 'aces': 0}

        parser_map = {
            'users.json': ('users', cls.parse_users),
            'groups.json': ('groups', cls.parse_groups),
            'computers.json': ('computers', cls.parse_computers),
            'domains.json': ('domains', cls.parse_domains),
        }

        parsed = {}
        all_aces = []
        for filename, (key, parser_fn) in parser_map.items():
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        raw = json.load(f)
                    entries = raw.get('data', raw) if isinstance(raw, dict) else raw
                    parsed[key] = parser_fn(entries)
                    summary[key] = len(parsed[key])
                    # Collect ACEs for users, groups, computers
                    if key in ('users', 'groups', 'computers'):
                        for item, entry in zip(parsed[key], entries):
                            sid = item.get('sid', '')
                            if sid:
                                all_aces.extend(cls.parse_aces(entry, sid))
                except Exception as exc:
                    logger.error(f"[BH] Failed to parse {filename}: {exc}")
            else:
                parsed[key] = []

        summary['aces'] = len(all_aces)

        if db_write and assessment_id:
            cls._write_to_graph(assessment_id, parsed, all_aces)

        return summary

    @classmethod
    def _write_to_graph(cls, assessment_id: int, parsed: dict,
                        all_aces: list | None = None) -> None:
        try:
            from ..graph.manager import ADGraphManager
            with ADGraphManager() as mgr:
                for domain in parsed.get('domains', []):
                    mgr.upsert_domain({**domain, 'assessment_id': assessment_id})
                for user in parsed.get('users', []):
                    mgr.upsert_user({**user, 'assessment_id': assessment_id})
                for group in parsed.get('groups', []):
                    mgr.upsert_group({**group, 'assessment_id': assessment_id})
                    for member in group.get('members', []):
                        if member['sid'] and member['type']:
                            label_map = {
                                'User': 'ADUser',
                                'Computer': 'ADComputer',
                                'Group': 'ADGroup',
                            }
                            label = label_map.get(member['type'])
                            if label:
                                try:
                                    mgr.create_membership_relationship(
                                        member['sid'], label,
                                        group['sid'], assessment_id)
                                except Exception as exc:
                                    logger.warning(
                                        f"[BH] Membership edge skipped (sid={member['sid']}): {exc}")
                for computer in parsed.get('computers', []):
                    mgr.upsert_computer({**computer, 'assessment_id': assessment_id})
            if all_aces:
                cls._write_acl_edges(assessment_id, all_aces)
        except Exception as exc:
            logger.error(f"[BH] Graph write failed: {exc}")
```

- [ ] **Step 7: Run tests**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_bloodhound_parser
```
Expected: `Ran 7 tests in ...s OK`

- [ ] **Step 8: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/ingestion/bloodhound_parser.py active_directory/tests/test_bloodhound_parser.py
git commit -m "feat(ad-plugin): extend BloodHound parser with Kerberos properties and ACL edge ingestion"
```

---

## Task 4: Graph manager — create_acl_edge + 5 attack path query methods

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/graph/manager.py`

- [ ] **Step 1: Write failing tests**

Write test file `r3ngine-plugins/active_directory/tests/test_graph_manager.py`:

```python
from unittest.mock import MagicMock, patch
from django.test import TestCase


class ADGraphManagerAttackPathTest(TestCase):
    """Unit tests for attack-path query methods using a mocked Neo4j driver."""

    def _make_manager(self, records):
        """Return an ADGraphManager with a mocked Neo4j session that returns `records`."""
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(records))
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        mock_session.run = MagicMock(return_value=mock_result)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        with patch('active_directory.backend.graph.manager.ADGraphManager.__init__',
                   lambda self: None):
            from active_directory.backend.graph.manager import ADGraphManager
            mgr = ADGraphManager.__new__(ADGraphManager)
            mgr._driver = mock_driver
        return mgr, mock_session

    def test_find_kerberoastable_returns_list(self):
        from active_directory.backend.graph.manager import ADGraphManager
        rec = MagicMock()
        rec.__getitem__ = lambda self, k: {
            'sid': 'S-1-2-3', 'sam_account_name': 'alice',
            'spn': ['MSSQLSvc/sql01:1433'], 'admin_count': 0,
        }[k]
        mgr, _ = self._make_manager([rec])
        results = mgr.find_kerberoastable(1)
        self.assertIsInstance(results, list)

    def test_find_asreproastable_returns_list(self):
        from active_directory.backend.graph.manager import ADGraphManager
        rec = MagicMock()
        rec.__getitem__ = lambda self, k: {
            'sid': 'S-1-2-3', 'sam_account_name': 'bob', 'admin_count': 0,
        }[k]
        mgr, _ = self._make_manager([rec])
        results = mgr.find_asreproastable(1)
        self.assertIsInstance(results, list)

    def test_find_kerberoastable_returns_empty_on_exception(self):
        from active_directory.backend.graph.manager import ADGraphManager
        with patch('active_directory.backend.graph.manager.ADGraphManager.__init__',
                   lambda self: None):
            mgr = ADGraphManager.__new__(ADGraphManager)
            mgr._driver = MagicMock(side_effect=Exception("Neo4j down"))
        results = mgr.find_kerberoastable(1)
        self.assertEqual(results, [])
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_graph_manager
```
Expected: `AttributeError` — `find_kerberoastable` doesn't exist yet.

- [ ] **Step 3: Add `create_acl_edge` method to `manager.py`**

Add after `create_exposure_link` (before Graph queries section):

```python
    ALLOWED_ACL_RELS = {
        'AD_GENERIC_ALL', 'AD_WRITE_DACL', 'AD_WRITE_OWNER',
        'AD_FORCE_CHANGE_PW', 'AD_HAS_SESSION', 'AD_ADMIN_TO',
        'AD_ALLOWED_TO_DELEGATE',
    }

    ALLOWED_TARGET_LABELS = {'ADUser', 'ADGroup', 'ADComputer'}

    def create_acl_edge(
            self, source_sid: str, target_sid: str,
            target_type: str, rel_type: str, assessment_id: int) -> None:
        """MERGE an ACL relationship between two AD nodes by SID."""
        if rel_type not in self.ALLOWED_ACL_RELS:
            raise ValueError(f"Invalid ACL rel_type: {rel_type!r}")
        label = f"AD{target_type}" if not target_type.startswith('AD') else target_type
        if label not in self.ALLOWED_TARGET_LABELS:
            label = 'ADUser'  # safe fallback
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (src {{sid: $src_sid, assessment_id: $aid}})
                MATCH (tgt:{label} {{sid: $tgt_sid, assessment_id: $aid}})
                MERGE (src)-[r:{rel_type}]->(tgt)
                SET r.assessment_id = $aid,
                    r.source_sid = $src_sid,
                    r.target_sid = $tgt_sid
                """,
                src_sid=source_sid,
                tgt_sid=target_sid,
                aid=assessment_id,
            )
```

- [ ] **Step 4: Add 5 attack path query methods to `manager.py`**

Add after `find_shortest_path`:

```python
    # ------------------------------------------------------------------
    # Attack path queries
    # ------------------------------------------------------------------

    def find_da_paths(self, assessment_id: int, max_hops: int = 10) -> List[Dict]:
        """Shortest paths from non-admin users to Domain Admins group."""
        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (u:{s.ADUserNode} {{assessment_id: $aid, admin_count: 0, enabled: true}})
                    MATCH (g:{s.ADGroupNode} {{assessment_id: $aid, admin_group: true}})
                      WHERE toLower(g.name) CONTAINS 'domain admins'
                    MATCH p = shortestPath((u)-[:AD_MEMBER_OF|AD_GENERIC_ALL|AD_WRITE_DACL|
                      AD_WRITE_OWNER|AD_FORCE_CHANGE_PW|AD_ADMIN_TO*1..{max_hops}]->(g))
                    RETURN u.sam_account_name AS source, g.name AS target,
                           length(p) AS path_length,
                           [n IN nodes(p) | {{id: id(n),
                             label: coalesce(n.sam_account_name, n.name, n.fqdn),
                             type: labels(n)[0]}}] AS hops
                    ORDER BY path_length ASC LIMIT 50
                    """,
                    aid=assessment_id,
                )
                return [
                    {
                        'source': r['source'],
                        'target': r['target'],
                        'path_length': r['path_length'],
                        'hops': r['hops'],
                    }
                    for r in result
                ]
        except Exception as exc:
            logger.warning(f"[ADGraph] find_da_paths failed: {exc}")
            return []

    def find_kerberoastable(self, assessment_id: int) -> List[Dict]:
        """Return users with SPNs (Kerberoastable)."""
        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (u:{s.ADUserNode} {{assessment_id: $aid, kerberoastable: true, enabled: true}})
                    RETURN u.sid AS sid, u.sam_account_name AS sam_account_name,
                           u.spn AS spn, u.admin_count AS admin_count
                    ORDER BY u.admin_count DESC
                    """,
                    aid=assessment_id,
                )
                return [
                    {
                        'sid': r['sid'],
                        'sam_account_name': r['sam_account_name'],
                        'spn': r['spn'],
                        'admin_count': r['admin_count'],
                    }
                    for r in result
                ]
        except Exception as exc:
            logger.warning(f"[ADGraph] find_kerberoastable failed: {exc}")
            return []

    def find_asreproastable(self, assessment_id: int) -> List[Dict]:
        """Return users with dont_req_preauth=true (AS-REP Roastable)."""
        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (u:{s.ADUserNode} {{assessment_id: $aid,
                           dont_req_preauth: true, enabled: true}})
                    RETURN u.sid AS sid, u.sam_account_name AS sam_account_name,
                           u.admin_count AS admin_count
                    ORDER BY u.admin_count DESC
                    """,
                    aid=assessment_id,
                )
                return [
                    {
                        'sid': r['sid'],
                        'sam_account_name': r['sam_account_name'],
                        'admin_count': r['admin_count'],
                    }
                    for r in result
                ]
        except Exception as exc:
            logger.warning(f"[ADGraph] find_asreproastable failed: {exc}")
            return []

    def find_unconstrained_delegation(self, assessment_id: int) -> List[Dict]:
        """Return computers with unconstrained Kerberos delegation."""
        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (c:{s.ADComputerNode} {{assessment_id: $aid,
                           unconstrained_delegation: true, enabled: true}})
                    RETURN c.sid AS sid, c.name AS name, c.fqdn AS fqdn,
                           c.constrained_delegation_targets AS delegation_targets
                    """,
                    aid=assessment_id,
                )
                return [
                    {
                        'sid': r['sid'],
                        'name': r['name'],
                        'fqdn': r['fqdn'],
                        'delegation_targets': r['delegation_targets'] or [],
                    }
                    for r in result
                ]
        except Exception as exc:
            logger.warning(f"[ADGraph] find_unconstrained_delegation failed: {exc}")
            return []

    def find_acl_abuse(self, assessment_id: int) -> List[Dict]:
        """Return non-admin users with dangerous ACL rights over admin objects."""
        try:
            with self._driver.session() as session:
                result = session.run(
                    f"""
                    MATCH (u:{s.ADUserNode} {{assessment_id: $aid, admin_count: 0, enabled: true}})
                          -[r:AD_GENERIC_ALL|AD_WRITE_DACL|AD_WRITE_OWNER|AD_FORCE_CHANGE_PW]->(t)
                      WHERE (t:{s.ADGroupNode} AND t.admin_group = true)
                         OR (t:{s.ADUserNode} AND t.admin_count > 0)
                    RETURN u.sid AS source_sid, u.sam_account_name AS source_name,
                           type(r) AS edge_type,
                           t.sid AS target_sid,
                           coalesce(t.sam_account_name, t.name) AS target_name,
                           labels(t)[0] AS target_type
                    ORDER BY edge_type
                    """,
                    aid=assessment_id,
                )
                return [
                    {
                        'source_sid': r['source_sid'],
                        'source_name': r['source_name'],
                        'edge_type': r['edge_type'],
                        'target_sid': r['target_sid'],
                        'target_name': r['target_name'],
                        'target_type': r['target_type'],
                    }
                    for r in result
                ]
        except Exception as exc:
            logger.warning(f"[ADGraph] find_acl_abuse failed: {exc}")
            return []
```

- [ ] **Step 5: Run tests**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_graph_manager
```
Expected: `Ran 3 tests in ...s OK`

- [ ] **Step 6: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/graph/manager.py active_directory/tests/test_graph_manager.py
git commit -m "feat(ad-plugin): add create_acl_edge and 5 attack path query methods to ADGraphManager"
```

---

## Task 5: Serializers + API — attack_paths action + ADPluginConfigView

**Files:**
- Modify: `r3ngine-plugins/active_directory/backend/serializers.py`
- Modify: `r3ngine-plugins/active_directory/backend/api.py`
- Modify: `r3ngine-plugins/active_directory/backend/api_urls.py`

- [ ] **Step 1: Write failing tests**

Write `r3ngine-plugins/active_directory/tests/test_api_attack_paths.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient
from active_directory.backend.models import ADAssessment, ADPluginConfig

User = get_user_model()


class AttackPathsAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('analyst', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.assessment = ADAssessment.objects.create(
            name='Test', target_domain='corp.local', created_by=self.user)

    @patch('active_directory.backend.api.ADGraphManager')
    def test_attack_paths_kerberoastable(self, mock_mgr_cls):
        mock_mgr = mock_mgr_cls.return_value.__enter__.return_value
        mock_mgr.find_kerberoastable.return_value = [
            {'sid': 'S-1', 'sam_account_name': 'alice', 'spn': ['SVC/x'], 'admin_count': 0}
        ]
        url = f'/api/plugins/active_directory/assessments/{self.assessment.pk}/attack-paths/'
        resp = self.client.get(url, {'category': 'kerberoastable'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)

    def test_attack_paths_invalid_category(self):
        url = f'/api/plugins/active_directory/assessments/{self.assessment.pk}/attack-paths/'
        resp = self.client.get(url, {'category': 'invalid'})
        self.assertEqual(resp.status_code, 400)

    def test_plugin_config_get(self):
        resp = self.client.get('/api/plugins/active_directory/config/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('max_path_length', resp.data)

    def test_plugin_config_put(self):
        resp = self.client.put(
            '/api/plugins/active_directory/config/',
            {'max_path_length': 7, 'neo4j_bolt_url': '', 'bloodhound_ce_url': '',
             'default_phases': []},
            format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['max_path_length'], 7)
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_api_attack_paths
```
Expected: 404 or `AttributeError` (endpoint not registered yet).

- [ ] **Step 3: Add `ADPluginConfigSerializer` to `serializers.py`**

Add after the last serializer class:

```python
from .models import ADAssessment, ADDomain, ADTrust, ADExposure, ADFinding, ADGraphSnapshot, ADEvidenceLog, ADPluginConfig

class ADPluginConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADPluginConfig
        fields = ['id', 'neo4j_bolt_url', 'max_path_length', 'bloodhound_ce_url', 'default_phases']
        read_only_fields = ['id']
```

- [ ] **Step 4: Add `attack_paths` action and `ADPluginConfigView` to `api.py`**

Update import in `api.py` — add `ADPluginConfig` to the models import:

```python
from .models import (ADAssessment, ADDomain, ADEvidenceLog, ADExposure, ADFinding,
                     ADGraphSnapshot, ADTrust, ADPluginConfig)
```

Add `ADPluginConfigSerializer` to serializers import:

```python
from .serializers import (ADAssessmentCreateSerializer,
                          ADAssessmentDetailSerializer,
                          ADAssessmentListSerializer, ADEvidenceLogSerializer,
                          ADExposureSerializer, ADFindingSerializer,
                          ADGraphSnapshotSerializer, ADTrustSerializer,
                          ADPluginConfigSerializer)
```

Add `attack_paths` action to `ADAssessmentViewSet` (after the last existing `@action`):

```python
    @action(detail=True, methods=['get'], url_path='attack-paths')
    def attack_paths(self, request, pk=None):
        assessment = self.get_object()
        category = request.query_params.get('category')
        valid = {'da_paths', 'kerberoastable', 'asreproastable',
                 'unconstrained_delegation', 'acl_abuse'}
        if category not in valid:
            return Response(
                {'error': f'category must be one of {sorted(valid)}'},
                status=status.HTTP_400_BAD_REQUEST)
        method_map = {
            'da_paths': 'find_da_paths',
            'kerberoastable': 'find_kerberoastable',
            'asreproastable': 'find_asreproastable',
            'unconstrained_delegation': 'find_unconstrained_delegation',
            'acl_abuse': 'find_acl_abuse',
        }
        try:
            from .graph.manager import ADGraphManager
            max_hops = int(ADPluginConfig.get_setting('max_path_length', 10))
            kwargs = {'max_hops': max_hops} if category == 'da_paths' else {}
            with ADGraphManager() as mgr:
                results = getattr(mgr, method_map[category])(assessment.id, **kwargs)
            return Response({'results': results, 'count': len(results)})
        except Exception as exc:
            logger.error(f"[AD API] attack_paths failed: {exc}")
            return Response({'results': [], 'error': str(exc), 'count': 0})
```

Add `ADPluginConfigView` class after `ADAssessmentViewSet`:

```python
from rest_framework.views import APIView


class ADPluginConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cfg = ADPluginConfig.get()
        return Response(ADPluginConfigSerializer(cfg).data)

    def put(self, request):
        cfg = ADPluginConfig.get()
        serializer = ADPluginConfigSerializer(cfg, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
```

- [ ] **Step 5: Register `ADPluginConfigView` in `api_urls.py`**

Replace `api_urls.py` content with:

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ADAssessmentViewSet, ADPluginConfigView

router = DefaultRouter()
router.register(r'assessments', ADAssessmentViewSet, basename='ad-assessment')

urlpatterns = [
    path('', include(router.urls)),
    path('config/', ADPluginConfigView.as_view(), name='ad-plugin-config'),
]
```

- [ ] **Step 6: Run tests**

```bash
docker exec r3ngine-web-1 python3 manage.py test active_directory.tests.test_api_attack_paths
```
Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 7: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/backend/api.py active_directory/backend/api_urls.py \
  active_directory/backend/serializers.py active_directory/tests/test_api_attack_paths.py
git commit -m "feat(ad-plugin): add attack_paths API action and ADPluginConfigView"
```

---

## Task 6: Frontend API hooks — `adApi.ts`

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/api/adApi.ts`
- Modify: `r3ngine-plugins/active_directory/ui/src/types/index.ts` (add `ADPluginConfig` type)

- [ ] **Step 1: Add `ADPluginConfig` type to `types/index.ts`**

Open `r3ngine-plugins/active_directory/ui/src/types/index.ts` and add:

```typescript
export interface ADPluginConfig {
  id: number;
  neo4j_bolt_url: string;
  max_path_length: number;
  bloodhound_ce_url: string;
  default_phases: string[];
}

export interface AttackPathsResult {
  results: unknown[];
  count: number;
  error?: string;
}
```

- [ ] **Step 2: Add 4 hooks to `adApi.ts`**

Append to end of `r3ngine-plugins/active_directory/ui/src/api/adApi.ts`:

```typescript
const CONFIG_BASE = '/api/plugins/active_directory/config';

export function useAttackPaths(assessmentId: number, category: string) {
  return useQuery({
    queryKey: ['ad', 'assessments', assessmentId, 'attack-paths', category],
    queryFn: () =>
      apiFetch<{ results: unknown[]; count: number; error?: string }>(
        `${API_BASE}/${assessmentId}/attack-paths/?category=${category}`
      ),
    enabled: !!assessmentId && !!category,
  });
}

export function usePluginConfig() {
  return useQuery({
    queryKey: ['ad', 'plugin-config'],
    queryFn: () => apiFetch<import('../types').ADPluginConfig>(`${CONFIG_BASE}/`),
  });
}

export function useUpdatePluginConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<import('../types').ADPluginConfig>) =>
      apiFetch<import('../types').ADPluginConfig>(`${CONFIG_BASE}/`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ad', 'plugin-config'] }),
  });
}

export function useUpdateAssessmentConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ assessmentId, config }: { assessmentId: number; config: Record<string, unknown> }) =>
      apiFetch<import('../types').ADAssessment>(`${API_BASE}/${assessmentId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ config }),
      }),
    onSuccess: (_data, { assessmentId }) => {
      qc.invalidateQueries({ queryKey: ['ad', 'assessments', assessmentId] });
    },
  });
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui
npm run build 2>&1 | tail -20
```
Expected: no TypeScript errors (build may warn about bundle size, that's OK).

- [ ] **Step 4: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/api/adApi.ts active_directory/ui/src/types/index.ts
git commit -m "feat(ad-plugin): add useAttackPaths, usePluginConfig, useUpdatePluginConfig, useUpdateAssessmentConfig hooks"
```

---

## Task 7: `ADAttackPathsPage.tsx` — 4-tab attack paths page

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/pages/ADAttackPathsPage.tsx`

- [ ] **Step 1: Create the page**

Write `r3ngine-plugins/active_directory/ui/src/pages/ADAttackPathsPage.tsx`:

```tsx
import { useState } from 'react';
import {
  Box, Typography, Tabs, Tab, Table, TableHead, TableBody,
  TableRow, TableCell, Chip, CircularProgress, Collapse,
  IconButton, Tooltip,
} from '@mui/material';
import { ChevronDown, ChevronRight, AlertTriangle, ShieldOff } from 'lucide-react';
import { useAttackPaths } from '../api/adApi';

interface Props {
  assessmentId: number;
}

const EMPTY_MSG = 'No attack path data. Upload a BloodHound JSON export via the Ingest tab.';

function SeverityChip({ level }: { level: 'CRITICAL' | 'HIGH' | 'MEDIUM' }) {
  const colorMap = { CRITICAL: 'error', HIGH: 'warning', MEDIUM: 'info' } as const;
  return <Chip label={level} size="small" color={colorMap[level]} sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem' }} />;
}

function EmptyState() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 8, gap: 2, opacity: 0.5 }}>
      <ShieldOff size={40} />
      <Typography variant="body2" sx={{ fontFamily: 'Orbitron' }}>{EMPTY_MSG}</Typography>
    </Box>
  );
}

interface DaPathRow {
  source: string;
  target: string;
  path_length: number;
  hops: { id: number; label: string; type: string }[];
}

function DaPathsTab({ assessmentId }: { assessmentId: number }) {
  const { data, isLoading } = useAttackPaths(assessmentId, 'da_paths');
  const [expanded, setExpanded] = useState<number | null>(null);
  const results = (data?.results ?? []) as DaPathRow[];

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}><CircularProgress size={24} /></Box>;
  if (!results.length) return <EmptyState />;

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell />
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SOURCE USER</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>TARGET GROUP</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>HOPS</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SEVERITY</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {results.map((row, i) => (
          <>
            <TableRow key={i} hover>
              <TableCell padding="checkbox">
                <IconButton size="small" onClick={() => setExpanded(expanded === i ? null : i)}>
                  {expanded === i ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </IconButton>
              </TableCell>
              <TableCell sx={{ fontFamily: 'monospace' }}>{row.source}</TableCell>
              <TableCell sx={{ fontFamily: 'monospace' }}>{row.target}</TableCell>
              <TableCell>{row.path_length}</TableCell>
              <TableCell><SeverityChip level="CRITICAL" /></TableCell>
            </TableRow>
            <TableRow key={`exp-${i}`}>
              <TableCell colSpan={5} sx={{ p: 0 }}>
                <Collapse in={expanded === i} unmountOnExit>
                  <Box sx={{ px: 3, py: 1.5, background: 'rgba(0,229,255,0.04)' }}>
                    <Typography variant="caption" sx={{ fontFamily: 'Orbitron', color: 'primary.main', mb: 1, display: 'block' }}>
                      ATTACK PATH
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
                      {row.hops.map((hop, hi) => (
                        <Box key={hi} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Chip
                            label={`${hop.label} (${hop.type})`}
                            size="small"
                            variant="outlined"
                            sx={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                          />
                          {hi < row.hops.length - 1 && <Typography variant="caption" sx={{ color: 'text.secondary' }}>→</Typography>}
                        </Box>
                      ))}
                    </Box>
                  </Box>
                </Collapse>
              </TableCell>
            </TableRow>
          </>
        ))}
      </TableBody>
    </Table>
  );
}

function KerberosTab({ assessmentId }: { assessmentId: number }) {
  const kerb = useAttackPaths(assessmentId, 'kerberoastable');
  const asrep = useAttackPaths(assessmentId, 'asreproastable');

  type KerbRow = { sid: string; sam_account_name: string; spn: string[]; admin_count: number };
  type AsrepRow = { sid: string; sam_account_name: string; admin_count: number };

  const kerbResults = (kerb.data?.results ?? []) as KerbRow[];
  const asrepResults = (asrep.data?.results ?? []) as AsrepRow[];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.75rem' }}>
            KERBEROASTABLE
          </Typography>
          <SeverityChip level="HIGH" />
        </Box>
        {kerb.isLoading ? <CircularProgress size={20} /> : !kerbResults.length ? <EmptyState /> : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>ACCOUNT</TableCell>
                <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SPN</TableCell>
                <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>ADMIN</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {kerbResults.map((row, i) => (
                <TableRow key={i} hover>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{row.sam_account_name}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {(row.spn ?? []).join(', ')}
                  </TableCell>
                  <TableCell>{row.admin_count > 0 ? <AlertTriangle size={14} color="#f44336" /> : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Box>

      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontFamily: 'Orbitron', fontSize: '0.75rem' }}>
            AS-REP ROASTABLE
          </Typography>
          <SeverityChip level="HIGH" />
        </Box>
        {asrep.isLoading ? <CircularProgress size={20} /> : !asrepResults.length ? <EmptyState /> : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>ACCOUNT</TableCell>
                <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>ADMIN</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {asrepResults.map((row, i) => (
                <TableRow key={i} hover>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{row.sam_account_name}</TableCell>
                  <TableCell>{row.admin_count > 0 ? <AlertTriangle size={14} color="#f44336" /> : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Box>
    </Box>
  );
}

function DelegationTab({ assessmentId }: { assessmentId: number }) {
  const { data, isLoading } = useAttackPaths(assessmentId, 'unconstrained_delegation');
  type Row = { sid: string; name: string; fqdn: string; delegation_targets: string[] };
  const results = (data?.results ?? []) as Row[];

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}><CircularProgress size={24} /></Box>;
  if (!results.length) return <EmptyState />;

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>COMPUTER</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>FQDN</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>DELEGATION TARGETS</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SEVERITY</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {results.map((row, i) => (
          <TableRow key={i} hover>
            <TableCell sx={{ fontFamily: 'monospace' }}>{row.name}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{row.fqdn}</TableCell>
            <TableCell sx={{ fontSize: '0.75rem' }}>{(row.delegation_targets ?? []).join(', ') || '—'}</TableCell>
            <TableCell><SeverityChip level="HIGH" /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function AclAbuseTab({ assessmentId }: { assessmentId: number }) {
  const { data, isLoading } = useAttackPaths(assessmentId, 'acl_abuse');
  type Row = { source_sid: string; source_name: string; edge_type: string; target_sid: string; target_name: string; target_type: string };
  const results = (data?.results ?? []) as Row[];

  const edgeSeverity = (edge: string): 'CRITICAL' | 'HIGH' | 'MEDIUM' => {
    if (edge === 'AD_GENERIC_ALL') return 'CRITICAL';
    if (edge === 'AD_WRITE_DACL' || edge === 'AD_WRITE_OWNER') return 'HIGH';
    return 'MEDIUM';
  };

  if (isLoading) return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}><CircularProgress size={24} /></Box>;
  if (!results.length) return <EmptyState />;

  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SOURCE</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>EDGE TYPE</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>TARGET</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>TARGET TYPE</TableCell>
          <TableCell sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }}>SEVERITY</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {results.map((row, i) => (
          <TableRow key={i} hover>
            <TableCell sx={{ fontFamily: 'monospace' }}>{row.source_name}</TableCell>
            <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'warning.main' }}>
              {row.edge_type}
            </TableCell>
            <TableCell sx={{ fontFamily: 'monospace' }}>{row.target_name}</TableCell>
            <TableCell>{row.target_type}</TableCell>
            <TableCell><SeverityChip level={edgeSeverity(row.edge_type)} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ADAttackPathsPage({ assessmentId }: Props) {
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <Typography variant="h6" sx={{ fontFamily: 'Orbitron', letterSpacing: 2, mb: 2 }}>
        ATTACK PATHS
      </Typography>
      <Tabs
        value={tab}
        onChange={(_e, v) => setTab(v)}
        textColor="primary"
        indicatorColor="primary"
        sx={{ mb: 2, borderBottom: '1px solid rgba(255,255,255,0.08)' }}
      >
        <Tab label="DA PATHS" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }} />
        <Tab label="KERBEROS" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }} />
        <Tab label="DELEGATION" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }} />
        <Tab label="ACL ABUSE" sx={{ fontFamily: 'Orbitron', fontSize: '0.7rem' }} />
      </Tabs>
      {tab === 0 && <DaPathsTab assessmentId={assessmentId} />}
      {tab === 1 && <KerberosTab assessmentId={assessmentId} />}
      {tab === 2 && <DelegationTab assessmentId={assessmentId} />}
      {tab === 3 && <AclAbuseTab assessmentId={assessmentId} />}
    </Box>
  );
}
```

- [ ] **Step 2: Verify TypeScript builds**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui
npm run build 2>&1 | tail -20
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/pages/ADAttackPathsPage.tsx
git commit -m "feat(ad-plugin): add ADAttackPathsPage with 4-tab attack paths view"
```

---

## Task 8: `ADPluginConfigModal.tsx` — plugin-level config modal

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/components/ADPluginConfigModal.tsx`

- [ ] **Step 1: Create the component**

Write `r3ngine-plugins/active_directory/ui/src/components/ADPluginConfigModal.tsx`:

```tsx
import { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Box, Typography, Checkbox,
  FormControlLabel, CircularProgress,
} from '@mui/material';
import { usePluginConfig, useUpdatePluginConfig } from '../api/adApi';

const PHASE_OPTIONS = [
  { key: 'dns_discovery', label: 'DNS Discovery' },
  { key: 'cert_discovery', label: 'Cert Discovery' },
  { key: 'trust_analysis', label: 'Trust Analysis' },
  { key: 'exposure_correlation', label: 'Exposure Correlation' },
  { key: 'neo4j_sync', label: 'Neo4j Sync' },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ADPluginConfigModal({ open, onClose }: Props) {
  const { data: config, isLoading } = usePluginConfig();
  const { mutate: update, isPending } = useUpdatePluginConfig();

  const [neo4jUrl, setNeo4jUrl] = useState('');
  const [maxPathLength, setMaxPathLength] = useState(10);
  const [bhUrl, setBhUrl] = useState('');
  const [phases, setPhases] = useState<string[]>([]);

  useEffect(() => {
    if (config) {
      setNeo4jUrl(config.neo4j_bolt_url ?? '');
      setMaxPathLength(config.max_path_length ?? 10);
      setBhUrl(config.bloodhound_ce_url ?? '');
      setPhases(config.default_phases ?? []);
    }
  }, [config]);

  const togglePhase = (key: string) => {
    setPhases(prev => prev.includes(key) ? prev.filter(p => p !== key) : [...prev, key]);
  };

  const handleSave = () => {
    update({
      neo4j_bolt_url: neo4jUrl,
      max_path_length: maxPathLength,
      bloodhound_ce_url: bhUrl,
      default_phases: phases,
    }, { onSuccess: onClose });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>PLUGIN CONFIGURATION</DialogTitle>
      <DialogContent>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Neo4j Bolt URL"
              value={neo4jUrl}
              onChange={e => setNeo4jUrl(e.target.value)}
              placeholder="bolt://neo4j:7687"
              fullWidth
              size="small"
            />
            <TextField
              label="Max Path Length"
              type="number"
              value={maxPathLength}
              onChange={e => setMaxPathLength(Math.max(1, Math.min(20, Number(e.target.value))))}
              inputProps={{ min: 1, max: 20 }}
              fullWidth
              size="small"
            />
            <TextField
              label="BloodHound CE URL (optional)"
              value={bhUrl}
              onChange={e => setBhUrl(e.target.value)}
              placeholder="http://bloodhound:8080"
              fullWidth
              size="small"
            />
            <Box>
              <Typography variant="caption" sx={{ fontFamily: 'Orbitron', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                DEFAULT PHASES
              </Typography>
              {PHASE_OPTIONS.map(opt => (
                <FormControlLabel
                  key={opt.key}
                  control={
                    <Checkbox
                      checked={phases.includes(opt.key)}
                      onChange={() => togglePhase(opt.key)}
                      size="small"
                    />
                  }
                  label={opt.label}
                  sx={{ display: 'block', '& .MuiFormControlLabel-label': { fontSize: '0.85rem' } }}
                />
              ))}
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={isPending || isLoading}>
          {isPending ? <CircularProgress size={16} /> : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 2: Verify TypeScript builds**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui
npm run build 2>&1 | tail -20
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/components/ADPluginConfigModal.tsx
git commit -m "feat(ad-plugin): add ADPluginConfigModal for plugin-level Neo4j and phase settings"
```

---

## Task 9: `ADAssessmentConfigModal.tsx` — per-assessment config modal

**Files:**
- Create: `r3ngine-plugins/active_directory/ui/src/components/ADAssessmentConfigModal.tsx`

- [ ] **Step 1: Create the component**

Write `r3ngine-plugins/active_directory/ui/src/components/ADAssessmentConfigModal.tsx`:

```tsx
import { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Box, Typography, Checkbox,
  FormControlLabel, CircularProgress,
} from '@mui/material';
import { useAssessment, useUpdateAssessmentConfig } from '../api/adApi';

const PHASE_OPTIONS = [
  { key: 'dns_discovery', label: 'DNS Discovery' },
  { key: 'cert_discovery', label: 'Cert Discovery' },
  { key: 'trust_analysis', label: 'Trust Analysis' },
  { key: 'exposure_correlation', label: 'Exposure Correlation' },
  { key: 'neo4j_sync', label: 'Neo4j Sync' },
];

interface Props {
  open: boolean;
  onClose: () => void;
  assessmentId: number;
}

export function ADAssessmentConfigModal({ open, onClose, assessmentId }: Props) {
  const { data: assessment, isLoading } = useAssessment(assessmentId);
  const { mutate: updateConfig, isPending } = useUpdateAssessmentConfig();

  const [dcIp, setDcIp] = useState('');
  const [ldapUser, setLdapUser] = useState('');
  const [ldapPass, setLdapPass] = useState('');
  const [phases, setPhases] = useState<string[]>([]);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (assessment?.config) {
      const cfg = assessment.config as Record<string, unknown>;
      setDcIp((cfg.dc_ip as string) ?? '');
      setLdapUser((cfg.ldap_username as string) ?? '');
      setLdapPass((cfg.ldap_password as string) ?? '');
      setPhases((cfg.enabled_phases as string[]) ?? []);
      setNotes((cfg.analyst_notes as string) ?? '');
    }
  }, [assessment]);

  const togglePhase = (key: string) => {
    setPhases(prev => prev.includes(key) ? prev.filter(p => p !== key) : [...prev, key]);
  };

  const handleSave = () => {
    const existing = (assessment?.config as Record<string, unknown>) ?? {};
    const merged = {
      ...existing,
      dc_ip: dcIp,
      ldap_username: ldapUser,
      ldap_password: ldapPass,
      enabled_phases: phases,
      analyst_notes: notes,
    };
    updateConfig({ assessmentId, config: merged }, { onSuccess: onClose });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>ASSESSMENT CONFIGURATION</DialogTitle>
      <DialogContent>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="DC IP Override"
              value={dcIp}
              onChange={e => setDcIp(e.target.value)}
              placeholder="192.168.1.1"
              fullWidth size="small"
            />
            <TextField
              label="LDAP Username"
              value={ldapUser}
              onChange={e => setLdapUser(e.target.value)}
              placeholder="CORP\\analyst"
              fullWidth size="small"
            />
            <TextField
              label="LDAP Password"
              type="password"
              value={ldapPass}
              onChange={e => setLdapPass(e.target.value)}
              fullWidth size="small"
            />
            <Box>
              <Typography variant="caption" sx={{ fontFamily: 'Orbitron', color: 'text.secondary', mb: 0.5, display: 'block' }}>
                ENABLED PHASES (overrides plugin defaults)
              </Typography>
              {PHASE_OPTIONS.map(opt => (
                <FormControlLabel
                  key={opt.key}
                  control={
                    <Checkbox
                      checked={phases.includes(opt.key)}
                      onChange={() => togglePhase(opt.key)}
                      size="small"
                    />
                  }
                  label={opt.label}
                  sx={{ display: 'block', '& .MuiFormControlLabel-label': { fontSize: '0.85rem' } }}
                />
              ))}
            </Box>
            <TextField
              label="Analyst Notes"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              multiline
              rows={3}
              fullWidth size="small"
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" disabled={isPending || isLoading}>
          {isPending ? <CircularProgress size={16} /> : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

- [ ] **Step 2: Verify TypeScript builds**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui
npm run build 2>&1 | tail -20
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/components/ADAssessmentConfigModal.tsx
git commit -m "feat(ad-plugin): add ADAssessmentConfigModal for per-assessment configuration"
```

---

## Task 10: Wire modals + attack_paths route into app shell

**Files:**
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentsPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADAssessmentDetailPage.tsx`
- Modify: `r3ngine-plugins/active_directory/ui/src/pages/ADPluginApp.tsx`

- [ ] **Step 1: Read `ADAssessmentDetailPage.tsx` to find the right insertion points**

Read the full file before editing.

- [ ] **Step 2: Add gear icon → `ADPluginConfigModal` to `ADAssessmentsPage.tsx`**

In `ADAssessmentsPage.tsx`:

1. Add imports at top:
```tsx
import { Settings } from 'lucide-react';
import { ADPluginConfigModal } from '../components/ADPluginConfigModal';
```

2. Add `configOpen` state:
```tsx
const [configOpen, setConfigOpen] = useState(false);
```

3. In the header `Box`, add a gear `IconButton` next to "New Assessment":
```tsx
<Box sx={{ display: 'flex', gap: 1 }}>
  <Tooltip title="Plugin settings">
    <IconButton size="small" onClick={() => setConfigOpen(true)} sx={{ color: 'rgba(255,255,255,0.5)' }}>
      <Settings size={18} />
    </IconButton>
  </Tooltip>
  <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>
    New Assessment
  </Button>
</Box>
```

4. Add `ADPluginConfigModal` before closing `</Box>`:
```tsx
<ADPluginConfigModal open={configOpen} onClose={() => setConfigOpen(false)} />
```

- [ ] **Step 3: Add settings icon + Attack Paths button to `ADAssessmentDetailPage.tsx`**

Read the file first, then:

1. Add imports:
```tsx
import { Settings } from 'lucide-react';
import { ADAssessmentConfigModal } from '../components/ADAssessmentConfigModal';
```

2. Add `settingsOpen` state.

3. In the action bar row, add:
```tsx
<Tooltip title="Assessment settings">
  <IconButton size="small" onClick={() => setSettingsOpen(true)} sx={{ color: 'rgba(255,255,255,0.5)' }}>
    <Settings size={16} />
  </IconButton>
</Tooltip>
```

4. Find where "Reports" button navigates and add after it:
```tsx
<Button size="small" startIcon={<ShieldAlert size={14} />}
  onClick={() => onNavigate?.('attack_paths')}
  variant="outlined" sx={{ fontFamily: 'Orbitron', fontSize: '0.65rem' }}>
  Attack Paths
</Button>
```

5. Add `ADAssessmentConfigModal`:
```tsx
<ADAssessmentConfigModal open={settingsOpen} onClose={() => setSettingsOpen(false)} assessmentId={assessmentId} />
```

- [ ] **Step 4: Add `attack_paths` route to `ADPluginApp.tsx`**

1. Add import:
```tsx
import { ADAttackPathsPage } from './ADAttackPathsPage';
```

2. Extend `Route` type:
```tsx
type Route =
  | { view: 'list' }
  | { view: 'detail'; assessmentId: number }
  | { view: 'graph'; assessmentId: number }
  | { view: 'trusts'; assessmentId: number }
  | { view: 'exposures'; assessmentId: number }
  | { view: 'reports'; assessmentId: number }
  | { view: 'attack_paths'; assessmentId: number };
```

3. In `parseSubpath`, add before the final `return { view: 'detail', assessmentId }`:
```tsx
if (view === 'attack_paths') return { view: 'attack_paths', assessmentId };
```

4. In `navigate`, add:
```tsx
if (path === 'attack_paths') { setRoute({ view: 'attack_paths', assessmentId }); return; }
```

5. Add render:
```tsx
{route.view === 'attack_paths' && <ADAttackPathsPage assessmentId={route.assessmentId} />}
```

- [ ] **Step 5: Build and verify no TypeScript errors**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui
npm run build 2>&1 | tail -30
```
Expected: build succeeds.

- [ ] **Step 6: Sync built assets to container**

```bash
docker cp d:/Repos/r3ngine/r3ngine-plugins/active_directory/ui/dist/. r3ngine-web-1:/app/staticfiles/plugins/active_directory/
```

- [ ] **Step 7: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add active_directory/ui/src/pages/ADAssessmentsPage.tsx \
  active_directory/ui/src/pages/ADAssessmentDetailPage.tsx \
  active_directory/ui/src/pages/ADPluginApp.tsx
git commit -m "feat(ad-plugin): wire attack_paths route and config modals into app shell"
```

---

## Task 11: `HOW_TO_BUILD.md` — plugin authoring guide

**Files:**
- Create: `r3ngine-plugins/HOW_TO_BUILD.md`

- [ ] **Step 1: Write the guide**

Write `r3ngine-plugins/HOW_TO_BUILD.md` with all 10 sections as defined in the spec (plugin structure, backend, frontend, installation, dev workflow, PluginPageLoader, tools, Temporal activities, Neo4j, checklist).

See spec section 7 for full content requirements.

- [ ] **Step 2: Commit**

```bash
cd d:/Repos/r3ngine/r3ngine-plugins
git add HOW_TO_BUILD.md
git commit -m "docs(ad-plugin): add HOW_TO_BUILD.md plugin authoring guide"
```

---

## Self-Review Checklist

After writing this plan, verify against spec:

- [x] Task 1 covers schema constants (all 7) and constraint statements
- [x] Task 2 covers `ADPluginConfig` model with all 4 fields + `get()` + `get_setting()`
- [x] Task 3 covers `parse_users` extension, `parse_computers` extension, `parse_aces`, `_write_acl_edges`, updated `ingest_from_directory`
- [x] Task 4 covers `create_acl_edge` + all 5 query methods (`find_da_paths`, `find_kerberoastable`, `find_asreproastable`, `find_unconstrained_delegation`, `find_acl_abuse`)
- [x] Task 5 covers `attack_paths` action + `ADPluginConfigView` + URL registration
- [x] Task 6 covers all 4 hooks + `ADPluginConfig` TypeScript type
- [x] Task 7 covers `ADAttackPathsPage` with all 4 tabs (DA Paths, Kerberos, Delegation, ACL Abuse)
- [x] Task 8 covers `ADPluginConfigModal` with all 4 fields + phase checkboxes
- [x] Task 9 covers `ADAssessmentConfigModal` with all 5 fields + deep-merge pattern
- [x] Task 10 covers gear icon in `ADAssessmentsPage`, settings + Attack Paths button in detail page, `attack_paths` route
- [x] Task 11 covers `HOW_TO_BUILD.md`

**Type consistency check:**
- `ADPluginConfig.get_setting('max_path_length', 10)` — used in Task 5 API, defined in Task 2 model ✓
- `ADGraphManager.create_acl_edge` — used in Task 3 `_write_acl_edges`, defined in Task 4 ✓
- `useAttackPaths` — defined in Task 6, used in Task 7 ✓
- `usePluginConfig`, `useUpdatePluginConfig` — defined in Task 6, used in Task 8 ✓
- `useAssessment`, `useUpdateAssessmentConfig` — existing + Task 6, used in Task 9 ✓
- `ADAttackPathsPage` — created in Task 7, imported in Task 10 ✓
- `ADPluginConfigModal` — created in Task 8, imported in Task 10 ✓
- `ADAssessmentConfigModal` — created in Task 9, imported in Task 10 ✓
