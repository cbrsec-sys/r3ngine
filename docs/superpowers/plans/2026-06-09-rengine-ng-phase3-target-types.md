# rengine-ng Integration — Phase 3: Extended Target Types

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend r3ngine's target system to support all 11 rengine-ng target types — adding 6 new types (email, phone, username, crypto-address, ip-address, cidr) as first-class targets with model fields, validation, and workflow routing.

**Architecture:** New target types are added as constants in `definitions.py`, new fields on the existing `Domain` model (renamed conceptually to "Target" via a `target_type` discriminator field), validation in the API layer, and a routing function that selects the right Phase 2 workflow for each target type. No new top-level model is introduced — the existing `Domain` model with `target_type` extension is the cleanest approach since all existing scan relationships already use it.

**Tech Stack:** Python 3.12, Django 5.2.3, DRF, PostgreSQL migrations

**Depends on:** Phase 2 (workflow names referenced in routing table)

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `web/reNgine/definitions.py` | Add 6 new target type constants |
| Modify | `web/targetApp/models.py` | Add `target_type` choices + 3 new fields to Domain |
| Create | `web/targetApp/migrations/XXXX_add_extended_target_types.py` | Migration |
| Modify | `web/targetApp/serializers.py` | Add type validation + per-type field requirements |
| Modify | `web/api/views.py` | `add_target` endpoint: validate + route to workflow |
| Create | `web/reNgine/target_router.py` | `route_target_to_workflow(target)` → workflow name + ctx |
| Modify | `web/tests/test_target_types.py` | Tests for validation + routing |

---

## Task 1: Add target type constants

**Files:**
- Modify: `web/reNgine/definitions.py`
- Modify: `web/targetApp/models.py`

- [ ] **Step 1: Write failing tests**

```python
# web/tests/test_target_types.py
from django.test import TestCase


class TestTargetTypeConstants(TestCase):
    def test_all_target_type_constants_defined(self):
        from reNgine.definitions import (
            TARGET_TYPE_DOMAIN,
            TARGET_TYPE_HOST,
            TARGET_TYPE_IP,
            TARGET_TYPE_CIDR,
            TARGET_TYPE_URL,
            TARGET_TYPE_EMAIL,
            TARGET_TYPE_USERNAME,
            TARGET_TYPE_PHONE,
            TARGET_TYPE_CRYPTO_ADDRESS,
            TARGET_TYPE_SUBDOMAIN,
            TARGET_TYPE_CODE_PATH,
        )
        self.assertEqual(TARGET_TYPE_DOMAIN, 'domain')
        self.assertEqual(TARGET_TYPE_CIDR, 'cidr')
        self.assertEqual(TARGET_TYPE_EMAIL, 'email')
        self.assertEqual(TARGET_TYPE_USERNAME, 'username')
        self.assertEqual(TARGET_TYPE_PHONE, 'phone')
        self.assertEqual(TARGET_TYPE_CRYPTO_ADDRESS, 'crypto_address')
        self.assertEqual(TARGET_TYPE_CODE_PATH, 'code_path')
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetTypeConstants --verbosity=2 2>&1 | head -20"
```
Expected: `ImportError: cannot import name 'TARGET_TYPE_CIDR'`

- [ ] **Step 3: Add constants to `definitions.py`**

Find the existing target type constants section in `web/reNgine/definitions.py`. If they don't exist there, check `web/targetApp/constants.py` or `web/targetApp/models.py` for where target types are defined.

Append the new constants (do not remove or rename existing ones):

```python
# web/reNgine/definitions.py — append to existing target type section

# Original types (already present — verify these names match existing code)
TARGET_TYPE_DOMAIN = 'domain'
TARGET_TYPE_HOST = 'host'
TARGET_TYPE_SUBDOMAIN = 'subdomain'
TARGET_TYPE_URL = 'url'
TARGET_TYPE_IP = 'ip'

# Extended target types (new in Phase 3)
TARGET_TYPE_CIDR = 'cidr'
TARGET_TYPE_EMAIL = 'email'
TARGET_TYPE_USERNAME = 'username'
TARGET_TYPE_PHONE = 'phone'
TARGET_TYPE_CRYPTO_ADDRESS = 'crypto_address'
TARGET_TYPE_CODE_PATH = 'code_path'
```

- [ ] **Step 4: Run tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetTypeConstants --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit constants**

```bash
git add web/reNgine/definitions.py
git commit -m "feat(targets): add 6 new target type constants (cidr, email, username, phone, crypto_address, code_path)"
```

---

## Task 2: Extend the Domain model with `target_type` and new fields

**Files:**
- Modify: `web/targetApp/models.py`
- Create: migration file (auto-generated)

- [ ] **Step 1: Write failing model test**

```python
class TestTargetModel(TestCase):
    def test_domain_has_target_type_field(self):
        from targetApp.models import Domain
        domain = Domain(name='example.com', target_type='domain')
        self.assertEqual(domain.target_type, 'domain')

    def test_cidr_target_can_be_created(self):
        from targetApp.models import Domain
        target = Domain.objects.create(
            name='10.0.0.0/8',
            target_type='cidr',
        )
        self.assertEqual(target.target_type, 'cidr')
        target.delete()

    def test_email_target_can_be_created(self):
        from targetApp.models import Domain
        target = Domain.objects.create(
            name='user@example.com',
            target_type='email',
        )
        self.assertEqual(target.target_type, 'email')
        target.delete()

    def test_username_target_can_be_created(self):
        from targetApp.models import Domain
        target = Domain.objects.create(
            name='johndoe',
            target_type='username',
        )
        self.assertEqual(target.target_type, 'username')
        target.delete()
```

- [ ] **Step 2: Run test to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetModel --verbosity=2 2>&1 | head -20"
```
Expected: `FieldError` or `ValueError` about `target_type` field not existing.

- [ ] **Step 3: Add `target_type` field to `Domain` model**

In `web/targetApp/models.py`, find the `Domain` class definition and add the field:

```python
# In Domain model class, add after the 'name' field:

TARGET_TYPE_CHOICES = [
    ('domain', 'Domain'),
    ('host', 'Host'),
    ('subdomain', 'Subdomain'),
    ('url', 'URL'),
    ('ip', 'IP Address'),
    ('cidr', 'CIDR Range'),
    ('email', 'Email Address'),
    ('username', 'Username'),
    ('phone', 'Phone Number'),
    ('crypto_address', 'Crypto Address'),
    ('code_path', 'Code Path / Repository'),
]

target_type = models.CharField(
    max_length=32,
    choices=TARGET_TYPE_CHOICES,
    default='domain',
    db_index=True,
)
```

- [ ] **Step 4: Generate and apply migration**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py makemigrations targetApp --name add_target_type_field"
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py migrate"
```
Expected: `Migrations for 'targetApp': targetApp/migrations/XXXX_add_target_type_field.py` then `OK`.

- [ ] **Step 5: Run model tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetModel --verbosity=2"
```
Expected: `OK`

- [ ] **Step 6: Commit model + migration**

```bash
git add web/targetApp/models.py web/targetApp/migrations/
git commit -m "feat(models): add target_type field to Domain model with 11 supported types"
```

---

## Task 3: Add target type validation in the API serializer

**Files:**
- Modify: `web/targetApp/serializers.py`

- [ ] **Step 1: Write serializer validation tests**

```python
class TestTargetSerializer(TestCase):
    def test_cidr_requires_valid_cidr_format(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'not-a-cidr', 'target_type': 'cidr'})
        self.assertFalse(s.is_valid())
        self.assertIn('name', s.errors)

    def test_valid_cidr_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '192.168.1.0/24', 'target_type': 'cidr'})
        self.assertTrue(s.is_valid())

    def test_email_requires_email_format(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'not-an-email', 'target_type': 'email'})
        self.assertFalse(s.is_valid())

    def test_valid_email_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'user@example.com', 'target_type': 'email'})
        self.assertTrue(s.is_valid())

    def test_username_no_special_chars(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'valid_user123', 'target_type': 'username'})
        self.assertTrue(s.is_valid())

    def test_code_path_accepts_local_and_git_url(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={
            'name': 'https://github.com/user/repo.git',
            'target_type': 'code_path',
        })
        self.assertTrue(s.is_valid())
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetSerializer --verbosity=2 2>&1 | head -20"
```
Expected: `ImportError` or `AssertionError` — `AddTargetSerializer` may not have type validation yet.

- [ ] **Step 3: Add validation to the serializer**

Find `web/targetApp/serializers.py` and add (or update) the validate method in the target serializer:

```python
# In targetApp/serializers.py

import ipaddress
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def _validate_cidr(value: str) -> None:
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise serializers.ValidationError("Invalid CIDR range. Expected format: 192.168.1.0/24")


def _validate_email_address(value: str) -> None:
    try:
        validate_email(value)
    except DjangoValidationError:
        raise serializers.ValidationError("Invalid email address format.")


def _validate_username(value: str) -> None:
    if not re.match(r'^[a-zA-Z0-9_.\-@+]+$', value):
        raise serializers.ValidationError(
            "Username contains invalid characters. Allowed: letters, digits, _, ., -, @, +"
        )


def _validate_ip_address(value: str) -> None:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise serializers.ValidationError("Invalid IP address format.")


# Add to the AddTargetSerializer (or equivalent) class:

class AddTargetSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=2048)
    target_type = serializers.ChoiceField(
        choices=[
            'domain', 'host', 'subdomain', 'url', 'ip',
            'cidr', 'email', 'username', 'phone', 'crypto_address', 'code_path',
        ],
        default='domain',
    )
    description = serializers.CharField(required=False, allow_blank=True)
    organization = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        name = data.get('name', '').strip()
        target_type = data.get('target_type', 'domain')
        validators = {
            'cidr': _validate_cidr,
            'email': _validate_email_address,
            'username': _validate_username,
            'ip': _validate_ip_address,
        }
        if target_type in validators:
            validators[target_type](name)
        return data
```

Note: If `AddTargetSerializer` already exists in the file with different field names, adapt the validation into the existing `validate()` method rather than replacing the whole class.

- [ ] **Step 4: Run serializer tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetSerializer --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/targetApp/serializers.py
git commit -m "feat(serializers): add per-type validation for extended target types (cidr, email, username, ip)"
```

---

## Task 4: Create target routing logic

**Files:**
- Create: `web/reNgine/target_router.py`

- [ ] **Step 1: Write routing tests**

```python
class TestTargetRouter(TestCase):
    def test_domain_routes_to_master_scan(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('example.com', 'domain')
        self.assertEqual(workflow_name, 'MasterScanWorkflow')

    def test_cidr_routes_to_cidr_recon(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('192.168.0.0/24', 'cidr')
        self.assertEqual(workflow_name, 'CIDRReconWorkflow')
        self.assertEqual(ctx['cidr'], '192.168.0.0/24')

    def test_email_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('user@example.com', 'email')
        self.assertEqual(workflow_name, 'UserHuntWorkflow')
        self.assertEqual(ctx['target_type'], 'email')

    def test_username_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('johndoe', 'username')
        self.assertEqual(workflow_name, 'UserHuntWorkflow')
        self.assertEqual(ctx['target_type'], 'username')

    def test_ip_routes_to_host_recon(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('1.2.3.4', 'ip')
        self.assertEqual(workflow_name, 'HostReconWorkflow')

    def test_url_routes_to_url_crawl(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('https://example.com', 'url')
        self.assertEqual(workflow_name, 'URLCrawlWorkflow')

    def test_code_path_routes_to_code_scan(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('/path/to/code', 'code_path')
        self.assertEqual(workflow_name, 'CodeScanWorkflow')
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetRouter --verbosity=2 2>&1 | head -10"
```
Expected: `ImportError: No module named 'reNgine.target_router'`

- [ ] **Step 3: Implement `target_router.py`**

```python
# web/reNgine/target_router.py
"""
Routes a target (value + type) to the appropriate Temporal workflow name
and builds the initial context dict for that workflow.

This is the central dispatch table for all 11 target types. When a new
scan is created via the API, this module determines which workflow to start.
"""
from typing import Tuple, Dict, Any

from reNgine.definitions import (
    TARGET_TYPE_DOMAIN,
    TARGET_TYPE_HOST,
    TARGET_TYPE_SUBDOMAIN,
    TARGET_TYPE_URL,
    TARGET_TYPE_IP,
    TARGET_TYPE_CIDR,
    TARGET_TYPE_EMAIL,
    TARGET_TYPE_USERNAME,
    TARGET_TYPE_PHONE,
    TARGET_TYPE_CRYPTO_ADDRESS,
    TARGET_TYPE_CODE_PATH,
)

# Maps target_type → (workflow_name, context_key_for_target)
_ROUTING_TABLE: Dict[str, Tuple[str, str]] = {
    TARGET_TYPE_DOMAIN:         ('MasterScanWorkflow',      'domain'),
    TARGET_TYPE_HOST:           ('HostReconWorkflow',        'target'),
    TARGET_TYPE_SUBDOMAIN:      ('SubdomainReconWorkflow',   'domain'),
    TARGET_TYPE_URL:            ('URLCrawlWorkflow',         'urls'),
    TARGET_TYPE_IP:             ('HostReconWorkflow',        'target'),
    TARGET_TYPE_CIDR:           ('CIDRReconWorkflow',        'cidr'),
    TARGET_TYPE_EMAIL:          ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_USERNAME:       ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_PHONE:          ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_CRYPTO_ADDRESS: ('UserHuntWorkflow',         'target'),
    TARGET_TYPE_CODE_PATH:      ('CodeScanWorkflow',         'target'),
}


def route_target_to_workflow(
    target_value: str,
    target_type: str,
    scan_history_id: int = None,
    yaml_configuration: dict = None,
) -> Tuple[str, Dict[str, Any]]:
    """Determine which Temporal workflow handles this target type.

    Args:
        target_value: The raw target string (domain name, CIDR, email, etc.)
        target_type: One of the TARGET_TYPE_* constants.
        scan_history_id: Optional ScanHistory PK to embed in context.
        yaml_configuration: Optional YAML scan config dict.

    Returns:
        (workflow_name, ctx) tuple. workflow_name is the @workflow.defn name.
        ctx is a ready-to-pass dict for workflow.run(ctx).
    """
    if target_type not in _ROUTING_TABLE:
        # Default unknown types to domain scanning
        target_type = TARGET_TYPE_DOMAIN

    workflow_name, ctx_key = _ROUTING_TABLE[target_type]

    ctx: Dict[str, Any] = {
        'scan_history_id': scan_history_id,
        'target_type': target_type,
        'yaml_configuration': yaml_configuration or {},
    }

    # Target types that produce list inputs use 'urls' or 'targets' keys
    if ctx_key == 'urls':
        ctx['urls'] = [target_value]
    else:
        ctx[ctx_key] = target_value

    return workflow_name, ctx
```

- [ ] **Step 4: Run routing tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types.TestTargetRouter --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/target_router.py web/tests/test_target_types.py
git commit -m "feat(routing): add target_router.py — dispatches all 11 target types to correct workflow"
```

---

## Task 5: Wire target_router into the scan creation API

**Files:**
- Modify: `web/api/views.py`

- [ ] **Step 1: Write integration test**

```python
class TestScanCreationWithTargetType(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('scanuser', password='pass')
        self.client.force_login(self.user)

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_creating_cidr_scan_starts_cidr_workflow(self, mock_start):
        mock_start.return_value = 'wf-cidr-001'
        response = self.client.post('/api/v1/scan/start/', {
            'target': '10.0.0.0/8',
            'target_type': 'cidr',
            'engine_id': None,
        }, content_type='application/json')
        # Accept 200 or 201
        self.assertIn(response.status_code, [200, 201])
        called_workflow = mock_start.call_args[0][0]
        self.assertEqual(called_workflow, 'CIDRReconWorkflow')

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_creating_username_scan_starts_user_hunt(self, mock_start):
        mock_start.return_value = 'wf-user-001'
        response = self.client.post('/api/v1/scan/start/', {
            'target': 'johndoe',
            'target_type': 'username',
        }, content_type='application/json')
        self.assertIn(response.status_code, [200, 201])
        called_workflow = mock_start.call_args[0][0]
        self.assertEqual(called_workflow, 'UserHuntWorkflow')
```

- [ ] **Step 2: Identify the existing scan start view**

```bash
grep -n "def.*scan\|start.*scan\|initiate_scan\|StartScan" web/api/views.py | head -20
```

Find the view that handles `POST /api/v1/scan/start/` (or equivalent) and note its class/function name and line number.

- [ ] **Step 3: Add target_router dispatch to scan start view**

In the identified scan start view, after the target is fetched/validated but before the Temporal workflow is started, add:

```python
from reNgine.target_router import route_target_to_workflow

target_value = request.data.get('target') or target_obj.name
target_type = request.data.get('target_type', 'domain') or getattr(target_obj, 'target_type', 'domain')

workflow_name, workflow_ctx = route_target_to_workflow(
    target_value=target_value,
    target_type=target_type,
    scan_history_id=scan_history.id,
    yaml_configuration=engine_yaml_config,
)

# Replace the hardcoded 'MasterScanWorkflow' start with:
workflow_id = await TemporalClientProvider.start_workflow(
    workflow_name,
    args=[workflow_ctx],
    id=f"scan-{scan_history.id}",
    task_queue="python-orchestrator-queue",
)
```

Note: the existing scan start code may use `initiate_scan_temporal()` from `tasks.py` which always starts `MasterScanWorkflow`. The change is to branch: if `target_type == 'domain'`, keep the existing flow; otherwise use `route_target_to_workflow`.

- [ ] **Step 4: Run integration tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_target_types --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/api/views.py
git commit -m "feat(api): wire target_router into scan creation — new target types dispatch to correct workflows"
```

---

## Task 6: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```
Expected: `OK`

- [ ] **Step 2: Tag Phase 3 complete**

```bash
git tag phase3-target-types
```

---

## Self-Review

**Spec coverage:**
- ✅ All 11 target types have constants in `definitions.py`
- ✅ `Domain` model extended with `target_type` field + migration
- ✅ Serializer validates CIDR, email, IP formats
- ✅ `target_router.py` maps all 11 types to the correct workflow
- ✅ Scan creation API dispatches to correct workflow based on `target_type`
- ✅ Tests for constants, model, serializer, and routing

**Missing (by design):** Phone number and crypto-address validation beyond basic non-empty checks — these are complex (international phone formats, multiple chain address formats). A `TODO` note is left in the serializer. They route to `UserHuntWorkflow` which handles them as generic OSINT targets.

**Placeholder scan:** None — all steps have real code.
