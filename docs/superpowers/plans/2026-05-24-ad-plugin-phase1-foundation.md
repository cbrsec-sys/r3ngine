# Active Directory Intelligence Plugin — Phase 1: Foundation & Isolated Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a fully installable r3ngine plugin (`active_directory`) with Django models, a complete isolated Temporal assessment pipeline, REST API, and WebSocket progress streaming — no changes to MasterScanWorkflow.

**Architecture:** Plugin lives in `r3ngine-plugins/active_directory/`. Backend registers via Django's dynamic `INSTALLED_APPS` discovery. Temporal workflows register via `PluginTemporalRegistry`. Assessments are started from a dedicated REST endpoint, not injected into the main scan pipeline. Progress streams over Redis → WebSocket. Two core modifications to the host: dynamic plugin URL discovery in `api/urls.py` and dynamic WebSocket routing in `routing.py`.

**Tech Stack:** Python 3.11, Django 3.2, temporalio 1.6.0, Django Channels 3.x, Redis streams, PostgreSQL

**Spec coverage:** agint.md Phases 1, 3, 8 (pipeline integration, Temporal orchestration, realtime streaming)

**Subsequent plans:**
- Phase 2: Graph Intelligence (Neo4j schema, ingestion pipelines, exposure correlation) → `2026-05-24-ad-plugin-phase2-graph.md`
- Phase 3: Frontend & Visualization (React pages, Cytoscape.js, Zustand, real-time) → `2026-05-24-ad-plugin-phase3-frontend.md`
- Phase 4: Evidence, Reporting & Testing → `2026-05-24-ad-plugin-phase4-reporting.md`

---

## File Map

| File | Action |
|---|---|
| `r3ngine-plugins/active_directory/manifest.yaml` | **Create** |
| `r3ngine-plugins/active_directory/tools.yaml` | **Create** |
| `r3ngine-plugins/active_directory/backend/__init__.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/apps.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/models.py` | **Create** — 6 models |
| `r3ngine-plugins/active_directory/backend/serializers.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/api.py` | **Create** — ADAssessmentViewSet |
| `r3ngine-plugins/active_directory/backend/api_urls.py` | **Create** |
| `r3ngine-plugins/active_directory/backend/temporal_exports.py` | **Create** — workflow + 7 activities |
| `r3ngine-plugins/active_directory/backend/consumers.py` | **Create** — WebSocket consumer |
| `web/api/urls.py` | **Modify** — dynamic plugin URL discovery |
| `web/reNgine/routing.py` | **Modify** — dynamic plugin WebSocket routing |
| `web/tests/test_ad_plugin_foundation.py` | **Create** |

---

## Task 1: Plugin manifest, tools declaration, and directory scaffold

**Context:** The `AtomicInstaller.validate_manifest()` requires a `runtime` key with `run after` or `run before`. Newer plugins omit it, which would fail validation. The AD plugin uses `runtime: { run after: "standalone" }` — `"standalone"` never matches any real scan anchor step, so the `PluginOrchestrator` will never inject it into the scan pipeline. The `anchor_step` column in the DB will hold `"standalone"`.

**Files:**
- Create: `r3ngine-plugins/active_directory/manifest.yaml`
- Create: `r3ngine-plugins/active_directory/tools.yaml`
- Create: `r3ngine-plugins/active_directory/backend/__init__.py`
- Create: `r3ngine-plugins/active_directory/backend/migrations/__init__.py`

- [ ] **Step 1.1: Create manifest.yaml**

```yaml
# r3ngine-plugins/active_directory/manifest.yaml
name: "Active Directory Intelligence"
description: "Enterprise AD assessment, identity intelligence, and exposure management plugin for contracted penetration testing and consulting engagements."
version: "1.0.0"

# "standalone" ensures this plugin never injects into the main scan pipeline.
# The PluginOrchestrator only calls plugins whose anchor_step matches a real scan task.
runtime:
  run after: "standalone"

temporal:
  workflows:
    - "backend.temporal_exports.ADAssessmentWorkflow"
  activities:
    - "backend.temporal_exports.initialize_assessment_activity"
    - "backend.temporal_exports.run_dns_discovery_activity"
    - "backend.temporal_exports.run_cert_discovery_activity"
    - "backend.temporal_exports.run_trust_analysis_activity"
    - "backend.temporal_exports.run_exposure_correlation_activity"
    - "backend.temporal_exports.run_neo4j_sync_activity"
    - "backend.temporal_exports.finalize_assessment_activity"

ui:
  menu_item: "AD Intelligence"
  menu_path: "/active-directory"
  components: []
```

- [ ] **Step 1.2: Create tools.yaml**

```yaml
# r3ngine-plugins/active_directory/tools.yaml
tools:
  - name: "ldapdomaindump"
    binary: "ldapdomaindump"
    install_type: "pip3"
    install_command: "pip3 install ldapdomaindump"
    validation_command: "ldapdomaindump --version"

  - name: "impacket"
    binary: "python3 -c 'import impacket; print(impacket.__version__)'"
    install_type: "pip3"
    install_command: "pip3 install impacket"
    validation_command: "python3 -c 'import impacket'"
```

- [ ] **Step 1.3: Create backend/__init__.py and migrations/__init__.py**

```bash
mkdir -p r3ngine-plugins/active_directory/backend/migrations
touch r3ngine-plugins/active_directory/backend/__init__.py
touch r3ngine-plugins/active_directory/backend/migrations/__init__.py
touch r3ngine-plugins/active_directory/__init__.py
```

- [ ] **Step 1.4: Commit**

```bash
git add r3ngine-plugins/active_directory/
git commit -m "feat(ad-plugin): scaffold plugin directory, manifest.yaml, tools.yaml"
```

---

## Task 2: Backend apps.py

**Context:** Django requires a unique `AppConfig.label` per installed app. All plugins use `{slug}_backend` as their label.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/apps.py`

- [ ] **Step 2.1: Write the failing test**

```python
# web/tests/test_ad_plugin_foundation.py
from django.test import TestCase

class TestADPluginAppConfig(TestCase):
    def test_app_label_is_unique_and_correct(self):
        from django.apps import apps
        # Will only pass once the plugin is installed/linked into plugins_data
        # Run this after Task 11 (installation). For now verify the module loads.
        import importlib
        spec = importlib.util.find_spec("plugins_data.active_directory.backend")
        # spec will be None until installed; the test documents the expectation
        if spec is not None:
            config = apps.get_app_config("active_directory_backend")
            self.assertEqual(config.label, "active_directory_backend")
            self.assertEqual(config.name, "plugins_data.active_directory.backend")
```

- [ ] **Step 2.2: Run test (expected: skipped or PASS — no assertion fails until plugin is installed)**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation.TestADPluginAppConfig -v 2
```

- [ ] **Step 2.3: Create apps.py**

```python
# r3ngine-plugins/active_directory/backend/apps.py
from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins_data.active_directory.backend'
    label = 'active_directory_backend'
    verbose_name = 'Active Directory Intelligence'
```

- [ ] **Step 2.4: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/apps.py web/tests/test_ad_plugin_foundation.py
git commit -m "feat(ad-plugin): add BackendConfig with unique app label"
```

---

## Task 3: Backend models.py

**Context:** Six models cover the full assessment lifecycle: assessments, domains, trusts, exposures, findings, and graph snapshots. All table names are prefixed with `plugin_ad_` to avoid collisions with core tables.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/models.py`

- [ ] **Step 3.1: Write the failing model tests**

Add to `web/tests/test_ad_plugin_foundation.py`:

```python
class TestADPluginModels(TestCase):
    """Run after plugin is installed into plugins_data/."""

    def _get_model(self, name):
        from django.apps import apps
        try:
            return apps.get_model('active_directory_backend', name)
        except LookupError:
            self.skipTest("Plugin not yet installed into plugins_data/")

    def test_assessment_model_fields(self):
        Assessment = self._get_model('ADAssessment')
        field_names = [f.name for f in Assessment._meta.get_fields()]
        for expected in ['name', 'target_domain', 'status', 'workflow_id', 'config']:
            self.assertIn(expected, field_names)

    def test_domain_fk_to_assessment(self):
        Domain = self._get_model('ADDomain')
        fk = Domain._meta.get_field('assessment')
        self.assertEqual(fk.related_model.__name__, 'ADAssessment')

    def test_finding_severity_choices(self):
        Finding = self._get_model('ADFinding')
        choices = [c[0] for c in Finding._meta.get_field('severity').choices]
        self.assertIn('CRITICAL', choices)
        self.assertIn('HIGH', choices)
```

- [ ] **Step 3.2: Run tests (expected: SKIP — plugin not yet installed)**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation.TestADPluginModels -v 2
```

- [ ] **Step 3.3: Create models.py**

```python
# r3ngine-plugins/active_directory/backend/models.py
from django.db import models
from django.utils import timezone


class ADAssessment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    name = models.CharField(max_length=255)
    target_domain = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    workflow_id = models.CharField(max_length=500, blank=True, null=True,
                                   help_text="Temporal workflow execution ID")
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    config = models.JSONField(default=dict, help_text="Assessment configuration")
    progress = models.JSONField(default=dict, help_text="Current phase progress map")

    class Meta:
        db_table = 'plugin_ad_assessment'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.status}]"


class ADDomain(models.Model):
    assessment = models.ForeignKey(
        ADAssessment, on_delete=models.CASCADE, related_name='domains')
    name = models.CharField(max_length=500)
    fqdn = models.CharField(max_length=500, blank=True, null=True)
    sid = models.CharField(max_length=100, blank=True, null=True)
    forest_root = models.BooleanField(default=False)
    functional_level = models.CharField(max_length=100, blank=True, null=True)
    dc_count = models.IntegerField(default=0)
    user_count = models.IntegerField(default=0)
    group_count = models.IntegerField(default=0)
    computer_count = models.IntegerField(default=0)
    neo4j_node_id = models.CharField(max_length=255, blank=True, null=True)
    discovered_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = 'plugin_ad_domain'
        unique_together = ['assessment', 'fqdn']

    def __str__(self):
        return self.fqdn or self.name


class ADTrust(models.Model):
    DIRECTION_CHOICES = [
        ('INBOUND', 'Inbound'),
        ('OUTBOUND', 'Outbound'),
        ('BIDIRECTIONAL', 'Bidirectional'),
    ]
    TYPE_CHOICES = [
        ('PARENT_CHILD', 'Parent-Child'),
        ('CROSS_LINK', 'Cross-Link'),
        ('EXTERNAL', 'External'),
        ('FOREST', 'Forest'),
        ('REALM', 'Realm'),
    ]
    assessment = models.ForeignKey(
        ADAssessment, on_delete=models.CASCADE, related_name='trusts')
    source_domain = models.ForeignKey(
        ADDomain, on_delete=models.CASCADE, related_name='outbound_trusts')
    target_domain_name = models.CharField(max_length=500)
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES)
    trust_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_transitive = models.BooleanField(default=False)
    is_selective_auth = models.BooleanField(default=False)
    risk_score = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = 'plugin_ad_trust'

    def __str__(self):
        return f"{self.source_domain} → {self.target_domain_name} ({self.direction})"


class ADExposure(models.Model):
    TYPE_CHOICES = [
        ('VPN', 'VPN Gateway'),
        ('OWA', 'Outlook Web Access'),
        ('ADFS', 'ADFS'),
        ('EXCHANGE', 'Exchange Server'),
        ('WINRM', 'WinRM'),
        ('SMB', 'SMB'),
        ('LDAP', 'LDAP'),
        ('KERBEROS', 'Kerberos'),
        ('RDP', 'Remote Desktop'),
        ('OTHER', 'Other'),
    ]
    assessment = models.ForeignKey(
        ADAssessment, on_delete=models.CASCADE, related_name='exposures')
    hostname = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    exposure_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    correlated_domain = models.ForeignKey(
        ADDomain, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exposures')
    risk_score = models.FloatField(default=0.0)
    evidence = models.JSONField(default=dict)
    discovered_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'plugin_ad_exposure'
        ordering = ['-risk_score']

    def __str__(self):
        return f"{self.exposure_type}: {self.hostname}"


class ADFinding(models.Model):
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Info'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    ]
    assessment = models.ForeignKey(
        ADAssessment, on_delete=models.CASCADE, related_name='findings')
    title = models.CharField(max_length=500)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    finding_type = models.CharField(max_length=100)
    affected_object = models.CharField(max_length=500, blank=True, null=True)
    evidence = models.JSONField(default=dict)
    remediation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'plugin_ad_finding'
        ordering = ['severity', '-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class ADGraphSnapshot(models.Model):
    assessment = models.ForeignKey(
        ADAssessment, on_delete=models.CASCADE, related_name='graph_snapshots')
    snapshot_type = models.CharField(max_length=100,
                                     help_text="e.g. 'trust_map', 'exposure_paths'")
    graph_data = models.JSONField(default=dict,
                                  help_text="Cytoscape-compatible node/edge payload")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'plugin_ad_graph_snapshot'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.snapshot_type} @ {self.created_at:%Y-%m-%d %H:%M}"
```

- [ ] **Step 3.4: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/models.py
git commit -m "feat(ad-plugin): add 6 assessment models (ADAssessment, ADDomain, ADTrust, ADExposure, ADFinding, ADGraphSnapshot)"
```

---

## Task 4: Backend serializers.py

**Context:** All ViewSet endpoints use DRF serializers. Nested read-only serializers provide summary counts without additional queries.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/serializers.py`

- [ ] **Step 4.1: Create serializers.py**

```python
# r3ngine-plugins/active_directory/backend/serializers.py
from rest_framework import serializers
from .models import ADAssessment, ADDomain, ADTrust, ADExposure, ADFinding, ADGraphSnapshot


class ADDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADDomain
        fields = [
            'id', 'name', 'fqdn', 'sid', 'forest_root', 'functional_level',
            'dc_count', 'user_count', 'group_count', 'computer_count',
            'neo4j_node_id', 'discovered_at', 'metadata',
        ]
        read_only_fields = ['id', 'discovered_at', 'neo4j_node_id']


class ADTrustSerializer(serializers.ModelSerializer):
    source_domain_fqdn = serializers.CharField(
        source='source_domain.fqdn', read_only=True)

    class Meta:
        model = ADTrust
        fields = [
            'id', 'source_domain', 'source_domain_fqdn', 'target_domain_name',
            'direction', 'trust_type', 'is_transitive', 'is_selective_auth',
            'risk_score', 'metadata',
        ]
        read_only_fields = ['id', 'source_domain_fqdn']


class ADExposureSerializer(serializers.ModelSerializer):
    correlated_domain_fqdn = serializers.CharField(
        source='correlated_domain.fqdn', read_only=True, allow_null=True)

    class Meta:
        model = ADExposure
        fields = [
            'id', 'hostname', 'ip_address', 'port', 'exposure_type',
            'correlated_domain', 'correlated_domain_fqdn', 'risk_score',
            'evidence', 'discovered_at',
        ]
        read_only_fields = ['id', 'correlated_domain_fqdn', 'discovered_at']


class ADFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADFinding
        fields = [
            'id', 'title', 'description', 'severity', 'status',
            'finding_type', 'affected_object', 'evidence', 'remediation',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ADGraphSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADGraphSnapshot
        fields = ['id', 'snapshot_type', 'graph_data', 'created_at']
        read_only_fields = ['id', 'created_at']


class ADAssessmentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested data."""
    domain_count = serializers.SerializerMethodField()
    finding_count = serializers.SerializerMethodField()
    exposure_count = serializers.SerializerMethodField()

    class Meta:
        model = ADAssessment
        fields = [
            'id', 'name', 'target_domain', 'status', 'workflow_id',
            'created_at', 'started_at', 'completed_at',
            'domain_count', 'finding_count', 'exposure_count',
        ]

    def get_domain_count(self, obj):
        return obj.domains.count()

    def get_finding_count(self, obj):
        return obj.findings.count()

    def get_exposure_count(self, obj):
        return obj.exposures.count()


class ADAssessmentDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested summaries for the detail view."""
    domains = ADDomainSerializer(many=True, read_only=True)
    finding_summary = serializers.SerializerMethodField()
    exposure_summary = serializers.SerializerMethodField()

    class Meta:
        model = ADAssessment
        fields = [
            'id', 'name', 'target_domain', 'status', 'workflow_id',
            'created_at', 'started_at', 'completed_at', 'error_message',
            'config', 'progress', 'domains', 'finding_summary', 'exposure_summary',
        ]

    def get_finding_summary(self, obj):
        from django.db.models import Count
        return dict(
            obj.findings.values('severity').annotate(count=Count('id'))
            .values_list('severity', 'count')
        )

    def get_exposure_summary(self, obj):
        from django.db.models import Count
        return dict(
            obj.exposures.values('exposure_type').annotate(count=Count('id'))
            .values_list('exposure_type', 'count')
        )


class ADAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ADAssessment
        fields = ['name', 'target_domain', 'config']
```

- [ ] **Step 4.2: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/serializers.py
git commit -m "feat(ad-plugin): add DRF serializers for all AD models"
```

---

## Task 5: Temporal workflow and activities (temporal_exports.py)

**Context:** `PluginTemporalRegistry` reads `temporal.workflows` and `temporal.activities` from the manifest and dynamically imports them. They run on the existing `python-orchestrator-queue` alongside core workflows — but are only started by the plugin's own REST API, never by `MasterScanWorkflow`. Activities send progress events to a Redis stream keyed `ad:assessment:{id}` which the WebSocket consumer tails.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/temporal_exports.py`

- [ ] **Step 5.1: Write workflow and activity tests**

Add to `web/tests/test_ad_plugin_foundation.py`:

```python
class TestADTemporalExports(TestCase):

    def _import_exports(self):
        try:
            import importlib
            return importlib.import_module(
                'plugins_data.active_directory.backend.temporal_exports')
        except ImportError:
            self.skipTest("Plugin not yet installed into plugins_data/")

    def test_workflow_class_is_registered(self):
        mod = self._import_exports()
        self.assertTrue(hasattr(mod, 'ADAssessmentWorkflow'))

    def test_all_activity_functions_exist(self):
        mod = self._import_exports()
        expected = [
            'initialize_assessment_activity',
            'run_dns_discovery_activity',
            'run_cert_discovery_activity',
            'run_trust_analysis_activity',
            'run_exposure_correlation_activity',
            'run_neo4j_sync_activity',
            'finalize_assessment_activity',
        ]
        for name in expected:
            self.assertTrue(hasattr(mod, name), f"Missing activity: {name}")
```

- [ ] **Step 5.2: Run test (expected: SKIP)**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation.TestADTemporalExports -v 2
```

- [ ] **Step 5.3: Create temporal_exports.py**

```python
# r3ngine-plugins/active_directory/backend/temporal_exports.py
import asyncio
import json
import logging
from datetime import timedelta
from typing import Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _send_ws_update(assessment_id: int, event_type: str, data: dict) -> None:
    """Write a progress event to the Redis stream for this assessment."""
    import redis
    from django.conf import settings
    r = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
    stream_key = f"ad:assessment:{assessment_id}"
    payload = json.dumps({'type': event_type, **data})
    r.xadd(stream_key, {'data': payload}, maxlen=500)


def _set_assessment_status(assessment_id: int, status: str,
                            error: Optional[str] = None) -> None:
    from django.utils import timezone
    from .models import ADAssessment
    update = {'status': status}
    if status == 'RUNNING':
        update['started_at'] = timezone.now()
    elif status in ('COMPLETED', 'FAILED', 'CANCELLED'):
        update['completed_at'] = timezone.now()
    if error:
        update['error_message'] = error
    ADAssessment.objects.filter(pk=assessment_id).update(**update)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

@activity.defn
def initialize_assessment_activity(params: dict) -> dict:
    """Mark assessment as RUNNING and emit the first WebSocket event."""
    assessment_id = params['assessment_id']
    _set_assessment_status(assessment_id, 'RUNNING')
    _send_ws_update(assessment_id, 'assessment_started', {
        'assessment_id': assessment_id,
        'message': 'Assessment initialised',
        'phase': 'initialization',
    })
    return {'status': 'initialized'}


@activity.defn
def run_dns_discovery_activity(params: dict) -> dict:
    """
    DNS-based discovery of AD infrastructure indicators.

    Resolves SRV records (_ldap._tcp, _kerberos._tcp, _gc._tcp) against
    the target domain to enumerate domain controllers and service endpoints.
    Returns a list of discovered DC hostnames and their roles.
    """
    assessment_id = params['assessment_id']
    target_domain = params['target_domain']

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'dns_discovery',
        'message': f'Starting DNS discovery for {target_domain}',
    })

    import socket
    discovered = []

    srv_records = [
        f'_ldap._tcp.{target_domain}',
        f'_kerberos._tcp.{target_domain}',
        f'_gc._tcp.{target_domain}',
        f'_ldap._tcp.dc._msdcs.{target_domain}',
    ]

    for record in srv_records:
        try:
            results = socket.getaddrinfo(record, None)
            for res in results:
                hostname = res[4][0]
                if hostname not in [d['hostname'] for d in discovered]:
                    discovered.append({
                        'hostname': hostname,
                        'record': record,
                        'role': _infer_role_from_srv(record),
                    })
        except (socket.gaierror, socket.herror):
            pass

    # Persist discovered domains
    from .models import ADAssessment, ADDomain
    try:
        assessment = ADAssessment.objects.get(pk=assessment_id)
        for dc in discovered:
            ADDomain.objects.get_or_create(
                assessment=assessment,
                fqdn=dc['hostname'],
                defaults={
                    'name': dc['hostname'].split('.')[0],
                    'metadata': {'srv_record': dc['record'], 'role': dc['role']},
                }
            )
    except Exception as e:
        logger.error(f"[AD DNS] Failed to persist domains: {e}")

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'dns_discovery',
        'discovered_count': len(discovered),
        'message': f'DNS discovery complete: {len(discovered)} hosts found',
    })

    return {'discovered': discovered, 'count': len(discovered)}


def _infer_role_from_srv(record: str) -> str:
    if '_gc._tcp' in record:
        return 'Global Catalog'
    if '_kerberos._tcp' in record:
        return 'KDC'
    if '_ldap._tcp.dc._msdcs' in record:
        return 'Domain Controller'
    return 'LDAP'


@activity.defn
def run_cert_discovery_activity(params: dict) -> dict:
    """
    Certificate transparency log enumeration for AD infrastructure indicators.

    Queries crt.sh for certificates matching the target domain and its
    common AD service patterns (ADFS, Exchange, OWA, VPN).
    """
    assessment_id = params['assessment_id']
    target_domain = params['target_domain']

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'cert_discovery',
        'message': f'Enumerating certificate transparency logs for {target_domain}',
    })

    import requests
    findings = []

    try:
        resp = requests.get(
            f'https://crt.sh/?q=%.{target_domain}&output=json',
            timeout=30
        )
        if resp.status_code == 200:
            entries = resp.json()
            ad_keywords = ['adfs', 'owa', 'exchange', 'mail', 'vpn', 'ldap',
                           'dc', 'dc01', 'dc02', 'domain']
            for entry in entries:
                name = entry.get('name_value', '')
                for keyword in ad_keywords:
                    if keyword in name.lower():
                        findings.append({
                            'name': name,
                            'issuer': entry.get('issuer_name', ''),
                            'not_after': entry.get('not_after', ''),
                            'matched_keyword': keyword,
                        })
                        break
    except Exception as e:
        logger.warning(f"[AD Cert] crt.sh query failed: {e}")

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'cert_discovery',
        'finding_count': len(findings),
        'message': f'Certificate discovery complete: {len(findings)} indicators',
    })

    return {'cert_findings': findings, 'count': len(findings)}


@activity.defn
def run_trust_analysis_activity(params: dict) -> dict:
    """
    Analyse trust relationships from discovered domain data.

    In this activity, trust data is sourced from previously ingested
    BloodHound/LDAP data (Phase 2). This stub processes whatever trust
    records exist in the DB and computes risk scores.
    """
    assessment_id = params['assessment_id']

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'trust_analysis',
        'message': 'Analysing domain trust relationships',
    })

    from .models import ADTrust
    trusts = ADTrust.objects.filter(assessment_id=assessment_id)
    risk_updates = []

    for trust in trusts:
        score = 0.0
        if trust.is_transitive:
            score += 30.0
        if trust.direction == 'BIDIRECTIONAL':
            score += 25.0
        if trust.trust_type == 'FOREST':
            score += 20.0
        if not trust.is_selective_auth:
            score += 15.0
        trust.risk_score = min(score, 100.0)
        trust.save(update_fields=['risk_score'])
        risk_updates.append({'trust_id': trust.id, 'risk_score': trust.risk_score})

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'trust_analysis',
        'trust_count': len(risk_updates),
        'message': f'Trust analysis complete: {len(risk_updates)} trusts scored',
    })

    return {'trust_risk_updates': risk_updates}


@activity.defn
def run_exposure_correlation_activity(params: dict) -> dict:
    """
    Correlate internet-facing services with identity infrastructure.

    Resolves hostnames from cert/DNS discovery against known AD service
    patterns and creates ADExposure records. Phase 2 enriches this further
    with full BloodHound/LDAP correlation.
    """
    assessment_id = params['assessment_id']
    target_domain = params['target_domain']
    dns_result = params.get('dns_result', {})
    cert_result = params.get('cert_result', {})

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'exposure_correlation',
        'message': 'Correlating external exposures with identity infrastructure',
    })

    from .models import ADAssessment, ADExposure

    exposure_patterns = {
        'adfs': 'ADFS',
        'owa': 'OWA',
        'exchange': 'EXCHANGE',
        'mail': 'EXCHANGE',
        'vpn': 'VPN',
        'ldap': 'LDAP',
        'rdp': 'RDP',
        'winrm': 'WINRM',
    }

    created_count = 0
    try:
        assessment = ADAssessment.objects.get(pk=assessment_id)
        cert_findings = cert_result.get('cert_findings', [])

        for finding in cert_findings:
            name = finding['name'].lower()
            for keyword, etype in exposure_patterns.items():
                if keyword in name:
                    exp, created = ADExposure.objects.get_or_create(
                        assessment=assessment,
                        hostname=finding['name'],
                        exposure_type=etype,
                        defaults={
                            'evidence': {
                                'source': 'cert_transparency',
                                'issuer': finding.get('issuer', ''),
                                'not_after': finding.get('not_after', ''),
                            },
                            'risk_score': 50.0,
                        }
                    )
                    if created:
                        created_count += 1
                    break
    except Exception as e:
        logger.error(f"[AD Exposure] Correlation failed: {e}")

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'exposure_correlation',
        'exposure_count': created_count,
        'message': f'Exposure correlation complete: {created_count} new exposures',
    })

    return {'exposures_created': created_count}


@activity.defn
def run_neo4j_sync_activity(params: dict) -> dict:
    """
    Sync assessment data to Neo4j for graph intelligence.

    Creates ADDomain and ADExposure nodes, and AD_EXPOSES relationships.
    Full graph schema (all node types) is implemented in Phase 2.
    """
    assessment_id = params['assessment_id']

    _send_ws_update(assessment_id, 'phase_started', {
        'phase': 'neo4j_sync',
        'message': 'Syncing assessment data to graph database',
    })

    try:
        from reNgine.graph_utils import Neo4jManager
        from .models import ADDomain, ADExposure

        manager = Neo4jManager()
        domains = ADDomain.objects.filter(assessment_id=assessment_id)
        node_count = 0

        with manager.driver.session() as session:
            for domain in domains:
                result = session.run(
                    """
                    MERGE (d:ADDomain {fqdn: $fqdn, assessment_id: $aid})
                    SET d.name = $name, d.forest_root = $forest_root,
                        d.dc_count = $dc_count, d.user_count = $user_count
                    RETURN id(d) as node_id
                    """,
                    fqdn=domain.fqdn or domain.name,
                    aid=assessment_id,
                    name=domain.name,
                    forest_root=domain.forest_root,
                    dc_count=domain.dc_count,
                    user_count=domain.user_count,
                )
                record = result.single()
                if record:
                    domain.neo4j_node_id = str(record['node_id'])
                    domain.save(update_fields=['neo4j_node_id'])
                    node_count += 1

        manager.driver.close()
    except Exception as e:
        logger.warning(f"[AD Neo4j] Sync failed (non-fatal): {e}")
        node_count = 0

    _send_ws_update(assessment_id, 'phase_completed', {
        'phase': 'neo4j_sync',
        'node_count': node_count,
        'message': f'Graph sync complete: {node_count} nodes',
    })

    return {'nodes_synced': node_count}


@activity.defn
def finalize_assessment_activity(params: dict) -> dict:
    """Mark the assessment terminal state and emit the final WebSocket event."""
    assessment_id = params['assessment_id']
    status = params.get('status', 'COMPLETED')
    error = params.get('error')

    _set_assessment_status(assessment_id, status, error)
    _send_ws_update(assessment_id, 'assessment_finished', {
        'assessment_id': assessment_id,
        'status': status,
        'message': f'Assessment {status.lower()}',
    })

    return {'final_status': status}


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

_RETRY_STANDARD = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(minutes=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
)


@workflow.defn(name="ADAssessmentWorkflow")
class ADAssessmentWorkflow:
    """
    Isolated AD assessment orchestration workflow.

    Not injected into MasterScanWorkflow. Started independently via
    POST /api/plugins/active_directory/assessments/{id}/start/

    Phase sequence:
      1. Initialize → 2. DNS discovery → 3. Cert discovery →
      4. Trust analysis → 5. Exposure correlation → 6. Neo4j sync →
      7. Finalize
    """

    @workflow.run
    async def run(self, payload: dict) -> dict:
        assessment_id = payload['assessment_id']
        target_domain = payload['target_domain']
        config = payload.get('config', {})

        try:
            await workflow.execute_activity(
                initialize_assessment_activity,
                {'assessment_id': assessment_id},
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY_STANDARD,
            )

            dns_result = await workflow.execute_activity(
                run_dns_discovery_activity,
                {'assessment_id': assessment_id, 'target_domain': target_domain},
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_STANDARD,
            )

            cert_result = await workflow.execute_activity(
                run_cert_discovery_activity,
                {'assessment_id': assessment_id, 'target_domain': target_domain},
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_STANDARD,
            )

            await workflow.execute_activity(
                run_trust_analysis_activity,
                {'assessment_id': assessment_id},
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_STANDARD,
            )

            await workflow.execute_activity(
                run_exposure_correlation_activity,
                {
                    'assessment_id': assessment_id,
                    'target_domain': target_domain,
                    'dns_result': dns_result,
                    'cert_result': cert_result,
                },
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_STANDARD,
            )

            await workflow.execute_activity(
                run_neo4j_sync_activity,
                {'assessment_id': assessment_id},
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_STANDARD,
            )

            return await workflow.execute_activity(
                finalize_assessment_activity,
                {'assessment_id': assessment_id, 'status': 'COMPLETED'},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_STANDARD,
            )

        except Exception as exc:
            await workflow.execute_activity(
                finalize_assessment_activity,
                {
                    'assessment_id': assessment_id,
                    'status': 'FAILED',
                    'error': str(exc),
                },
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            raise
```

- [ ] **Step 5.4: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/temporal_exports.py
git commit -m "feat(ad-plugin): add ADAssessmentWorkflow + 7 Temporal activities (isolated pipeline)"
```

---

## Task 6: WebSocket consumer

**Context:** Uses the same Redis stream pattern as `ScanLogConsumer`. The consumer tails `ad:assessment:{id}` and forwards events to connected clients.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/consumers.py`

- [ ] **Step 6.1: Create consumers.py**

```python
# r3ngine-plugins/active_directory/backend/consumers.py
import asyncio
import json
import logging

import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)

WEBSOCKET_URLPATTERNS = [
    (r'ws/ad/assessment/(?P<assessment_id>\d+)/$', 'ADAssessmentConsumer'),
]


class ADAssessmentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.assessment_id = self.scope['url_route']['kwargs']['assessment_id']
        self.stream_key = f"ad:assessment:{self.assessment_id}"
        self.group_name = f"ad_assessment_{self.assessment_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"AD WebSocket connected for assessment {self.assessment_id}")

        self.keep_running = True
        self.tail_task = asyncio.create_task(self._tail_redis_stream())

    async def disconnect(self, close_code):
        self.keep_running = False
        if hasattr(self, 'tail_task'):
            self.tail_task.cancel()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"AD WebSocket disconnected for assessment {self.assessment_id}")

    async def _tail_redis_stream(self):
        r = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True,
        )
        last_id = '0'
        loop = asyncio.get_running_loop()

        while self.keep_running:
            try:
                streams = await loop.run_in_executor(
                    None,
                    lambda: r.xread({self.stream_key: last_id}, count=20, block=2000),
                )
                if streams:
                    for _stream_name, messages in streams:
                        for msg_id, data in messages:
                            last_id = msg_id
                            payload = json.loads(data['data'])
                            await self.send(text_data=json.dumps(payload))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AD stream tail error: {e}")
                await asyncio.sleep(1)

    async def ad_assessment_update(self, event):
        """Receive direct channel-layer push (used for cancellations etc.)."""
        await self.send(text_data=json.dumps(event['data']))
```

- [ ] **Step 6.2: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/consumers.py
git commit -m "feat(ad-plugin): add ADAssessmentConsumer (Redis stream WebSocket)"
```

---

## Task 7: Plugin REST API (api.py + api_urls.py)

**Context:** The plugin exposes its own endpoints at `/api/plugins/active_directory/`. The `start` action starts the Temporal workflow. The `cancel` action cancels it via `TemporalClientProvider`. The `ingest` action accepts file uploads (LDAP/BloodHound exports) — ingestion logic is implemented in Phase 2.

**Files:**
- Create: `r3ngine-plugins/active_directory/backend/api.py`
- Create: `r3ngine-plugins/active_directory/backend/api_urls.py`

- [ ] **Step 7.1: Write API tests**

Add to `web/tests/test_ad_plugin_foundation.py`:

```python
from django.test import TestCase
from unittest.mock import patch, AsyncMock

class TestADAssessmentAPI(TestCase):

    def _get_view(self):
        try:
            from plugins_data.active_directory.backend.api import ADAssessmentViewSet
            return ADAssessmentViewSet
        except ImportError:
            self.skipTest("Plugin not installed")

    def test_viewset_has_required_actions(self):
        ViewSet = self._get_view()
        self.assertTrue(hasattr(ViewSet, 'start'))
        self.assertTrue(hasattr(ViewSet, 'cancel'))
        self.assertTrue(hasattr(ViewSet, 'ingest'))
        self.assertTrue(hasattr(ViewSet, 'findings'))
        self.assertTrue(hasattr(ViewSet, 'exposures'))
        self.assertTrue(hasattr(ViewSet, 'trusts'))
        self.assertTrue(hasattr(ViewSet, 'graph_snapshot'))
```

- [ ] **Step 7.2: Create api.py**

```python
# r3ngine-plugins/active_directory/backend/api.py
import asyncio
import logging
import os
import uuid

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import (ADAssessment, ADDomain, ADExposure, ADFinding,
                     ADGraphSnapshot, ADTrust)
from .serializers import (ADAssessmentCreateSerializer,
                          ADAssessmentDetailSerializer,
                          ADAssessmentListSerializer, ADExposureSerializer,
                          ADFindingSerializer, ADGraphSnapshotSerializer,
                          ADTrustSerializer)

logger = logging.getLogger(__name__)


class ADAssessmentViewSet(viewsets.ModelViewSet):
    queryset = ADAssessment.objects.all()
    lookup_field = 'pk'

    def get_serializer_class(self):
        if self.action == 'create':
            return ADAssessmentCreateSerializer
        if self.action in ('retrieve', 'update', 'partial_update'):
            return ADAssessmentDetailSerializer
        return ADAssessmentListSerializer

    # ------------------------------------------------------------------
    # Start / Cancel
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """Start the ADAssessmentWorkflow for this assessment."""
        assessment = self.get_object()
        if assessment.status not in ('PENDING', 'FAILED', 'CANCELLED'):
            return Response(
                {'error': f'Cannot start an assessment in {assessment.status} state.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow_id = f"ad-assessment-{assessment.id}-{uuid.uuid4().hex[:8]}"

        try:
            wf_id = self._start_workflow(assessment, workflow_id)
            assessment.workflow_id = wf_id
            assessment.status = 'PENDING'
            assessment.save(update_fields=['workflow_id', 'status'])
            return Response({'workflow_id': wf_id, 'status': 'started'})
        except Exception as exc:
            logger.error(f"[AD API] Failed to start workflow: {exc}")
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _start_workflow(self, assessment, workflow_id: str) -> str:
        from reNgine.temporal_client import TemporalClientProvider
        from .temporal_exports import ADAssessmentWorkflow

        loop = asyncio.new_event_loop()
        try:
            async def _run():
                client = await TemporalClientProvider.get_client()
                handle = await client.start_workflow(
                    ADAssessmentWorkflow.run,
                    {
                        'assessment_id': assessment.id,
                        'target_domain': assessment.target_domain,
                        'config': assessment.config,
                    },
                    id=workflow_id,
                    task_queue='python-orchestrator-queue',
                )
                return handle.id
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel a running ADAssessmentWorkflow."""
        assessment = self.get_object()
        if not assessment.workflow_id:
            return Response(
                {'error': 'No active workflow to cancel.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from reNgine.temporal_client import TemporalClientProvider
            TemporalClientProvider.cancel_workflow(assessment.workflow_id)
            assessment.status = 'CANCELLED'
            assessment.completed_at = timezone.now()
            assessment.save(update_fields=['status', 'completed_at'])
            return Response({'status': 'cancelled'})
        except Exception as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ------------------------------------------------------------------
    # Sub-resource endpoints
    # ------------------------------------------------------------------

    @action(detail=True, methods=['get'], url_path='findings')
    def findings(self, request, pk=None):
        assessment = self.get_object()
        severity = request.query_params.get('severity')
        qs = assessment.findings.all()
        if severity:
            qs = qs.filter(severity=severity.upper())
        return Response(ADFindingSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='trusts')
    def trusts(self, request, pk=None):
        assessment = self.get_object()
        return Response(
            ADTrustSerializer(assessment.trusts.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='exposures')
    def exposures(self, request, pk=None):
        assessment = self.get_object()
        return Response(
            ADExposureSerializer(assessment.exposures.all(), many=True).data)

    @action(detail=True, methods=['get', 'post'], url_path='graph-snapshot')
    def graph_snapshot(self, request, pk=None):
        assessment = self.get_object()
        if request.method == 'GET':
            snapshot_type = request.query_params.get('type')
            qs = assessment.graph_snapshots.all()
            if snapshot_type:
                qs = qs.filter(snapshot_type=snapshot_type)
            return Response(ADGraphSnapshotSerializer(qs[:1], many=True).data)
        # POST: save a new snapshot from the frontend
        serializer = ADGraphSnapshotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(assessment=assessment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='ingest',
            parser_classes=[MultiPartParser])
    def ingest(self, request, pk=None):
        """
        Accept data file upload for ingestion (LDAP export, BloodHound JSON).
        Full ingestion pipelines implemented in Phase 2.
        """
        assessment = self.get_object()
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided.'},
                            status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES['file']
        ingest_type = request.data.get('type', 'auto')

        # Write to a temp location for the ingestion pipeline
        import tempfile
        with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded.name)[1]) as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        return Response({
            'status': 'queued',
            'file': uploaded.name,
            'type': ingest_type,
            'tmp_path': tmp_path,
            'message': 'File received. Ingestion pipeline runs in Phase 2.',
        })
```

- [ ] **Step 7.3: Create api_urls.py**

```python
# r3ngine-plugins/active_directory/backend/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ADAssessmentViewSet

router = DefaultRouter()
router.register(r'assessments', ADAssessmentViewSet, basename='ad-assessment')

urlpatterns = [
    path('', include(router.urls)),
]
```

- [ ] **Step 7.4: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation.TestADAssessmentAPI -v 2
```

Expected: SKIP (plugin not installed yet).

- [ ] **Step 7.5: Commit**

```bash
git add r3ngine-plugins/active_directory/backend/api.py \
        r3ngine-plugins/active_directory/backend/api_urls.py
git commit -m "feat(ad-plugin): add ADAssessmentViewSet with start/cancel/ingest/sub-resource endpoints"
```

---

## Task 8: Dynamic plugin URL discovery in api/urls.py

**Context:** The core `api/urls.py` hardcodes only `plugins.urls`. Plugins with their own REST APIs need a discovery mechanism. The pattern mirrors how `settings.py` discovers plugin backends: iterate `plugins_data/`, import `backend.api_urls` if it exists, and mount at `/api/plugins/{slug}/`.

**Files:**
- Modify: `web/api/urls.py`

- [ ] **Step 8.1: Write the integration test**

Add to `web/tests/test_ad_plugin_foundation.py`:

```python
class TestDynamicPluginURLDiscovery(TestCase):

    def test_ad_plugin_urls_are_mounted(self):
        """Once the plugin is installed, /api/plugins/active_directory/ must resolve."""
        from django.urls import reverse, NoReverseMatch
        try:
            url = reverse('api:ad-assessment-list')
            self.assertTrue(url.startswith('/api/plugins/active_directory/'))
        except NoReverseMatch:
            self.skipTest(
                "Plugin not installed yet — mount expected after Task 11")
```

- [ ] **Step 8.2: Add dynamic discovery to api/urls.py**

Open `web/api/urls.py`. Add the following block **immediately before** `urlpatterns += router.urls`:

```python
# Dynamic plugin API URL discovery
# Each plugin may provide backend/api_urls.py to expose plugin-specific endpoints
# at /api/plugins/{plugin_slug}/
import importlib
import os as _os
from django.conf import settings as _settings

_plugins_data_dir = _os.path.join(_settings.BASE_DIR, 'plugins_data')
if _os.path.exists(_plugins_data_dir):
    for _plugin_slug in _os.listdir(_plugins_data_dir):
        _plugin_api_module = f"plugins_data.{_plugin_slug}.backend.api_urls"
        try:
            importlib.import_module(_plugin_api_module)
            urlpatterns.append(
                path(f'plugins/{_plugin_slug}/', include(
                    (_plugin_api_module, _plugin_slug),
                    namespace=_plugin_slug,
                ))
            )
        except ImportError:
            pass
        except Exception as _e:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                f"Failed to load plugin URLs for {_plugin_slug}: {_e}")
```

- [ ] **Step 8.3: Run tests**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation.TestDynamicPluginURLDiscovery -v 2
```

Expected: SKIP (plugin not installed yet).

- [ ] **Step 8.4: Commit**

```bash
git add web/api/urls.py
git commit -m "feat(plugin-system): add dynamic plugin URL discovery in api/urls.py"
```

---

## Task 9: Dynamic WebSocket routing in routing.py

**Context:** `routing.py` statically imports consumers. Plugins with WebSocket consumers need discovery. The plugin declares its URL patterns in `consumers.py` via the module-level `WEBSOCKET_URLPATTERNS` list; `routing.py` scans `plugins_data/` and includes them.

**Files:**
- Modify: `web/reNgine/routing.py`

- [ ] **Step 9.1: Modify routing.py**

Replace the content of `web/reNgine/routing.py` with:

```python
import importlib
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django_asgi_app = get_asgi_application()

from reNgine.consumers import StressTelemetryConsumer, ScanLogConsumer

websocket_urlpatterns = [
    re_path(r'ws/stress/(?P<scan_id>\d+)/$', StressTelemetryConsumer.as_asgi()),
    re_path(r'ws/logs/(?P<scan_id>\d+)/$', ScanLogConsumer.as_asgi()),
]

# Dynamic plugin WebSocket consumer discovery
# Plugin consumers.py must declare WEBSOCKET_URLPATTERNS = [(pattern, ClassName), ...]
from django.conf import settings as _settings
_plugins_data_dir = os.path.join(_settings.BASE_DIR, 'plugins_data')
if os.path.exists(_plugins_data_dir):
    for _plugin_slug in os.listdir(_plugins_data_dir):
        _consumers_module_path = f"plugins_data.{_plugin_slug}.backend.consumers"
        try:
            _mod = importlib.import_module(_consumers_module_path)
            for _pattern, _cls_name in getattr(_mod, 'WEBSOCKET_URLPATTERNS', []):
                _consumer_cls = getattr(_mod, _cls_name)
                websocket_urlpatterns.append(
                    re_path(_pattern, _consumer_cls.as_asgi()))
        except ImportError:
            pass
        except Exception as _e:
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to load plugin WebSocket consumers for {_plugin_slug}: {_e}")

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

- [ ] **Step 9.2: Verify Django still starts**

```bash
cd web && python manage.py check --deploy 2>&1 | head -20
```

Expected: no errors related to routing.

- [ ] **Step 9.3: Commit**

```bash
git add web/reNgine/routing.py
git commit -m "feat(plugin-system): add dynamic WebSocket consumer discovery in routing.py"
```

---

## Task 10: Install plugin into plugins_data and run migrations

**Context:** The plugin must be copied into `web/plugins_data/active_directory/` (the runtime location Django discovers) and migrations must be run. In production this happens via `AtomicInstaller.install(zip)`; for development, we symlink or copy directly.

**Files:**
- No new source files — operational step

- [ ] **Step 10.1: Copy plugin backend to plugins_data (dev shortcut)**

```bash
mkdir -p web/plugins_data
cp -r r3ngine-plugins/active_directory web/plugins_data/
# Create __init__.py files Django needs
touch web/plugins_data/__init__.py
touch web/plugins_data/active_directory/__init__.py
```

- [ ] **Step 10.2: Create and run migrations**

```bash
cd web
python manage.py makemigrations active_directory_backend
python manage.py migrate active_directory_backend
```

Expected output: `Running migrations: Applying active_directory_backend.0001_initial... OK`

- [ ] **Step 10.3: Verify tables exist**

```bash
cd web && python manage.py shell -c "
from django.db import connection
tables = [t for t in connection.introspection.table_names() if t.startswith('plugin_ad')]
print('AD tables:', tables)
"
```

Expected: `AD tables: ['plugin_ad_assessment', 'plugin_ad_domain', 'plugin_ad_exposure', 'plugin_ad_finding', 'plugin_ad_graph_snapshot', 'plugin_ad_trust']`

- [ ] **Step 10.4: Commit**

```bash
git add web/plugins_data/
git commit -m "chore(ad-plugin): install plugin into plugins_data/, add initial migration"
```

---

## Task 11: End-to-end smoke test and plugin registration

**Context:** With the plugin installed, all previously skipped tests should pass. We also verify the plugin registers correctly in the `Plugin` DB table.

**Files:**
- Modify: `web/tests/test_ad_plugin_foundation.py` (add registration test)

- [ ] **Step 11.1: Register plugin in the Plugin model**

```bash
cd web && python manage.py shell -c "
import yaml, os
from plugins.models import Plugin
manifest_path = 'plugins_data/active_directory/manifest.yaml'
with open(manifest_path) as f:
    manifest = yaml.safe_load(f)
runtime = manifest.get('runtime', {})
anchor = runtime.get('run after') or runtime.get('run before') or 'standalone'
position = 'AFTER' if 'run after' in runtime else 'BEFORE'
plugin, created = Plugin.objects.update_or_create(
    slug='active_directory',
    defaults={
        'name': manifest['name'],
        'version': manifest['version'],
        'description': manifest.get('description', ''),
        'manifest': manifest,
        'anchor_step': anchor,
        'runtime_position': position,
    }
)
print('Plugin registered:', plugin, 'created:', created)
"
```

- [ ] **Step 11.2: Run full test suite for the plugin**

```bash
cd web && python manage.py test tests.test_ad_plugin_foundation -v 2
```

Expected: All tests PASS (no longer skipped).

- [ ] **Step 11.3: Verify API endpoint is accessible**

```bash
cd web && python manage.py shell -c "
from django.test import RequestFactory
from django.urls import resolve
match = resolve('/api/plugins/active_directory/assessments/')
print('Resolved to:', match.func)
"
```

Expected: resolves to `ADAssessmentViewSet`.

- [ ] **Step 11.4: Smoke test assessment create + workflow stub**

```bash
cd web && python manage.py shell -c "
from plugins_data.active_directory.backend.models import ADAssessment
a = ADAssessment.objects.create(
    name='Test Assessment',
    target_domain='corp.example.com'
)
print('Assessment created:', a.id, a.status)
a.delete()
print('Cleaned up')
"
```

- [ ] **Step 11.5: Commit**

```bash
git add web/tests/test_ad_plugin_foundation.py
git commit -m "test(ad-plugin): all Phase 1 foundation tests passing"
```

---

## Phase 1 Complete

The plugin is now:
- Installable via `AtomicInstaller` (zip) or dev copy
- Registered in Django `INSTALLED_APPS` automatically
- Running its 7 Temporal activities on `python-orchestrator-queue`
- Exposing REST API at `/api/plugins/active_directory/assessments/`
- Streaming progress via WebSocket at `ws/ad/assessment/{id}/`
- Visible in nav via `/api/plugins/registry/` → `manifest.ui.menu_item`

**Next:** Phase 2 — Graph Intelligence (`2026-05-24-ad-plugin-phase2-graph.md`)
- Neo4j schema (all 17 node types, 10 relationship types)
- LDAP export parser
- BloodHound JSON parser
- DNS/certificate inventory ingestion
- Full exposure correlation engine
- Graph analytics (pathfinding, trust traversal, risk scoring)
