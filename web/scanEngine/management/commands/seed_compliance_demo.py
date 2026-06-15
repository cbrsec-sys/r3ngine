"""
Management command: seed_compliance_demo

Creates realistic mock compliance-assessment data so the frontend UI can be tested
without running a real scan or installing the plugin via the marketplace.

Usage:
    # Inside container
    python manage.py seed_compliance_demo          # create demo data
    python manage.py seed_compliance_demo --teardown   # remove all demo data

All demo records are isolated to a project/domain with the slug marker
'__compliance_demo__' so teardown can remove them without touching real data.

The compliance tables are created on-the-fly with CREATE TABLE IF NOT EXISTS
because the plugin may not be registered in INSTALLED_APPS yet.
"""

import json
import logging

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

# Unique slug that marks all demo records — never used for real targets.
DEMO_SLUG = '__compliance_demo__'
DEMO_DOMAIN = 'demo.compliance-target.internal'
DEMO_PROJECT = 'Compliance Assessment Demo'

# ---------------------------------------------------------------------------
# DDL — create tables if they don't exist
# ---------------------------------------------------------------------------

_CREATE_ASSESSMENT = """
CREATE TABLE IF NOT EXISTS plugin_compliance_assessment_assessment (
    id                  SERIAL PRIMARY KEY,
    scan_history_id     INTEGER NOT NULL
                            REFERENCES "startScan_scanhistory"(id) ON DELETE CASCADE,
    framework           VARCHAR(32)  NOT NULL,
    status              VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
    pass_count          INTEGER      NOT NULL DEFAULT 0,
    fail_count          INTEGER      NOT NULL DEFAULT 0,
    partial_count       INTEGER      NOT NULL DEFAULT 0,
    manual_count        INTEGER      NOT NULL DEFAULT 0,
    compliance_score    DOUBLE PRECISION,
    html_report_path    VARCHAR(500) NOT NULL DEFAULT '',
    pdf_report_path     VARCHAR(500) NOT NULL DEFAULT '',
    attestation_path    VARCHAR(500) NOT NULL DEFAULT '',
    attestation_hash    VARCHAR(64)  NOT NULL DEFAULT '',
    created_at          TIMESTAMPTZ  NOT NULL,
    completed_at        TIMESTAMPTZ,
    UNIQUE (scan_history_id, framework)
);
"""

_CREATE_CONTROL = """
CREATE TABLE IF NOT EXISTS plugin_compliance_assessment_control_result (
    id                  SERIAL PRIMARY KEY,
    assessment_id       INTEGER NOT NULL
                            REFERENCES plugin_compliance_assessment_assessment(id)
                            ON DELETE CASCADE,
    control_id          VARCHAR(64)  NOT NULL,
    control_name        VARCHAR(255) NOT NULL,
    section             VARCHAR(128) NOT NULL,
    result              VARCHAR(16)  NOT NULL,
    confidence          VARCHAR(16)  NOT NULL,
    static_remediation  TEXT         NOT NULL DEFAULT '',
    ai_remediation      TEXT         NOT NULL DEFAULT '',
    ai_enriched_at      TIMESTAMPTZ,
    UNIQUE (assessment_id, control_id)
);
"""

_CREATE_EVIDENCE = """
CREATE TABLE IF NOT EXISTS plugin_compliance_assessment_evidence (
    id                  SERIAL PRIMARY KEY,
    control_result_id   INTEGER NOT NULL
                            REFERENCES plugin_compliance_assessment_control_result(id)
                            ON DELETE CASCADE,
    evidence_type       VARCHAR(16) NOT NULL,
    evidence_id         INTEGER,
    description         TEXT        NOT NULL,
    detail              JSONB       NOT NULL DEFAULT '{}'
);
"""

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

_CONTROLS = [
    # (control_id, control_name, section, result, confidence, static_remediation, evidence_rows)
    (
        'PCI-2.2.1',
        'System components configuration standards',
        'Requirement 2 — Secure Configurations',
        'PASS',
        'HIGH',
        (
            'Maintain a documented inventory of all system components. '
            'Apply vendor-recommended hardening and CIS Benchmark baselines.'
        ),
        [
            ('PORT', None, 'No unexpected services detected on scanned hosts', {'ports_checked': 12}),
        ],
    ),
    (
        'PCI-4.2.1',
        'Strong cryptography in transit',
        'Requirement 4 — Protect Cardholder Data in Transit',
        'PARTIAL',
        'MEDIUM',
        (
            'Enforce TLS 1.2+ on all exposed services. '
            'Disable SSLv3, TLS 1.0, and TLS 1.1. '
            'Configure HSTS with a minimum max-age of 31536000 seconds.'
        ),
        [
            ('HEADER', None, 'Missing Strict-Transport-Security header on 3 endpoints', {'endpoints': ['/', '/login', '/api/']}),
            ('ENDPOINT', None, 'HTTP (non-TLS) redirect missing on port 80', {'url': 'http://demo.compliance-target.internal/'}),
        ],
    ),
    (
        'PCI-6.2.4',
        'Software development practices prevent common vulnerabilities',
        'Requirement 6 — Secure Systems and Software',
        'FAIL',
        'HIGH',
        (
            'Immediately remediate SQL injection and XSS vulnerabilities detected. '
            'Integrate SAST into the CI/CD pipeline. '
            'Conduct mandatory secure code training for all developers. '
            'Implement parameterised queries and output encoding.'
        ),
        [
            ('VULNERABILITY', 1, 'SQL Injection detected in login endpoint', {'severity': 'critical', 'cve': None, 'url': '/api/auth/login'}),
            ('VULNERABILITY', 2, 'Reflected XSS in search parameter', {'severity': 'high', 'cve': None, 'url': '/search?q='}),
        ],
    ),
    (
        'PCI-6.3.3',
        'All software components protected from known vulnerabilities',
        'Requirement 6 — Secure Systems and Software',
        'FAIL',
        'HIGH',
        (
            'Patch or upgrade the identified components with critical CVEs immediately. '
            'Establish a vulnerability management SLA: critical ≤7 days, high ≤30 days. '
            'Subscribe to vendor security advisories and NVD feeds.'
        ),
        [
            ('VULNERABILITY', 3, 'CVE-2023-44487 (HTTP/2 Rapid Reset) — critical severity', {'severity': 'critical', 'cve': 'CVE-2023-44487', 'cvss': 7.5}),
            ('VULNERABILITY', 4, 'CVE-2024-22262 (Spring Framework RCE) — high severity', {'severity': 'high', 'cve': 'CVE-2024-22262', 'cvss': 8.1}),
        ],
    ),
    (
        'PCI-6.4.1',
        'Public-facing web application protected against attacks',
        'Requirement 6 — Secure Systems and Software',
        'PARTIAL',
        'MEDIUM',
        (
            'Deploy a WAF in blocking mode in front of all public-facing applications. '
            'Configure rulesets for OWASP CRS at paranoia level 2+. '
            'Review and tune WAF rules monthly.'
        ),
        [
            ('HEADER', None, 'No WAF fingerprint detected on HTTP responses', {'checked_headers': ['Server', 'X-Powered-By', 'X-Cache']}),
        ],
    ),
    (
        'PCI-8.2.1',
        'Shared and generic credentials are prohibited',
        'Requirement 8 — User Identification and Authentication',
        'PASS',
        'HIGH',
        (
            'Continue enforcing individual user accounts. '
            'Audit for shared credentials quarterly and disable any found.'
        ),
        [],
    ),
    (
        'PCI-9.4.1',
        'Media with cardholder data is secured',
        'Requirement 9 — Physical Access Controls',
        'MANUAL',
        'MANUAL',
        (
            'Manually verify that all physical and digital media containing cardholder data '
            'is classified, labelled, and stored in locked, access-controlled locations. '
            'Confirm a media destruction policy and records exist.'
        ),
        [],
    ),
    (
        'PCI-10.1.1',
        'Audit log solution captures all required events',
        'Requirement 10 — Log and Monitor All Access',
        'MANUAL',
        'MANUAL',
        (
            'Verify that audit logs capture: all access to cardholder data, '
            'administrative actions, authentication events, and security-relevant exceptions. '
            'Confirm log integrity mechanisms (WORM or cryptographic signing) are in place.'
        ),
        [],
    ),
    (
        'PCI-11.3.1',
        'Internal penetration test performed at least annually',
        'Requirement 11 — Test Security Regularly',
        'PASS',
        'MEDIUM',
        (
            'Document penetration test methodology, scope, and results. '
            'Ensure all critical and high findings are remediated before the next test cycle.'
        ),
        [
            ('VULNERABILITY', None, 'Internal scan completed — 47 hosts enumerated, no critical internal findings', {'hosts': 47}),
        ],
    ),
    (
        'PCI-11.3.2',
        'External penetration test performed at least annually',
        'Requirement 11 — Test Security Regularly',
        'PASS',
        'HIGH',
        (
            'External perimeter is tested and results are documented. '
            'Engage a QSA-approved penetration testing firm for annual external tests.'
        ),
        [
            ('PORT', None, 'External attack surface mapped: 4 open ports on perimeter', {'open_ports': [80, 443, 8080, 8443]}),
        ],
    ),
    (
        'PCI-12.3.4',
        'Hardware and end-user device security reviewed',
        'Requirement 12 — Organisational Policies',
        'MANUAL',
        'MANUAL',
        (
            'Manually confirm that all hardware devices in the cardholder data environment '
            'are inventoried with make/model/serial/location. '
            'Verify tamper-evident seals are intact on all POS terminals.'
        ),
        [],
    ),
]


class Command(BaseCommand):
    help = (
        'Seed realistic compliance-assessment demo data for frontend testing. '
        'Use --teardown to remove all demo records without affecting real data.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--teardown',
            action='store_true',
            default=False,
            help='Remove all demo data created by this command.',
        )

    def handle(self, *args, **options):
        if options['teardown']:
            self._teardown()
        else:
            self._seed()

    # ------------------------------------------------------------------
    # Teardown
    # ------------------------------------------------------------------

    def _teardown(self):
        from dashboard.models import Project
        from targetApp.models import Domain

        self.stdout.write('Removing compliance demo data...')
        with connection.cursor() as cur:
            # Delete evidence → control → assessment (cascade should handle it,
            # but explicit deletes are safer against partial installs)
            cur.execute("""
                DELETE FROM plugin_compliance_assessment_evidence
                WHERE control_result_id IN (
                    SELECT cr.id
                    FROM plugin_compliance_assessment_control_result cr
                    JOIN plugin_compliance_assessment_assessment a ON a.id = cr.assessment_id
                    JOIN "startScan_scanhistory" sh ON sh.id = a.scan_history_id
                    JOIN targetApp_domain d ON d.id = sh.domain_id
                    WHERE d.name = %s
                )
            """, [DEMO_DOMAIN])

            cur.execute("""
                DELETE FROM plugin_compliance_assessment_control_result
                WHERE assessment_id IN (
                    SELECT a.id
                    FROM plugin_compliance_assessment_assessment a
                    JOIN "startScan_scanhistory" sh ON sh.id = a.scan_history_id
                    JOIN targetApp_domain d ON d.id = sh.domain_id
                    WHERE d.name = %s
                )
            """, [DEMO_DOMAIN])

            cur.execute("""
                DELETE FROM plugin_compliance_assessment_assessment
                WHERE scan_history_id IN (
                    SELECT sh.id
                    FROM "startScan_scanhistory" sh
                    JOIN targetApp_domain d ON d.id = sh.domain_id
                    WHERE d.name = %s
                )
            """, [DEMO_DOMAIN])

        # Use ORM cascade for the scan/domain/project records
        Domain.objects.filter(name=DEMO_DOMAIN).delete()
        Project.objects.filter(slug=DEMO_SLUG).delete()
        self.stdout.write(self.style.SUCCESS('Demo data removed.'))

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def _seed(self):
        from django.contrib.auth.models import User
        from dashboard.models import Project
        from targetApp.models import Domain
        from scanEngine.models import EngineType
        from startScan.models import ScanHistory

        self.stdout.write('Creating compliance demo data...')

        # -- Project
        project, _ = Project.objects.get_or_create(
            slug=DEMO_SLUG,
            defaults={
                'name': DEMO_PROJECT,
                'insert_date': timezone.now(),
            },
        )

        # -- Domain
        domain, _ = Domain.objects.get_or_create(
            name=DEMO_DOMAIN,
            defaults={
                'target_type': 'domain',
                'insert_date': timezone.now(),
                'project': project,
            },
        )
        if domain.project_id != project.id:
            domain.project = project
            domain.save(update_fields=['project'])

        # -- EngineType (reuse existing default engine if available)
        engine = EngineType.objects.filter(default_engine=True).first()
        if engine is None:
            engine, _ = EngineType.objects.get_or_create(
                engine_name='Compliance Demo Engine',
                defaults={'yaml_configuration': 'subdomain_discovery: true\n'},
            )

        # -- ScanHistory
        superuser = User.objects.filter(is_superuser=True).first()
        scan, created = ScanHistory.objects.get_or_create(
            domain=domain,
            scan_type=engine,
            scan_status=2,  # SUCCESS_TASK
            defaults={
                'start_scan_date': timezone.now() - timezone.timedelta(hours=2),
                'stop_scan_date': timezone.now() - timezone.timedelta(minutes=10),
                'results_dir': f'/usr/src/app/scan_results/demo/{DEMO_DOMAIN}',
                'tasks': ['subdomain_discovery', 'port_scan', 'vulnerability_scan'],
                'initiated_by': superuser,
            },
        )
        if not created:
            self.stdout.write(f'  Reusing existing demo ScanHistory id={scan.id}')

        # -- Create compliance tables
        self._ensure_tables()

        # -- Check for existing assessment
        with connection.cursor() as cur:
            cur.execute(
                'SELECT id FROM plugin_compliance_assessment_assessment WHERE scan_history_id=%s AND framework=%s',
                [scan.id, 'pci_dss_4'],
            )
            row = cur.fetchone()

        if row:
            self.stdout.write(f'  Demo assessment already exists (id={row[0]}), skipping insert.')
            self._print_access_info(scan.id, row[0])
            return

        now_str = timezone.now().isoformat()
        completed_str = (timezone.now() - timezone.timedelta(minutes=5)).isoformat()

        # Compute counts
        pass_count = sum(1 for c in _CONTROLS if c[3] == 'PASS')
        fail_count = sum(1 for c in _CONTROLS if c[3] == 'FAIL')
        partial_count = sum(1 for c in _CONTROLS if c[3] == 'PARTIAL')
        manual_count = sum(1 for c in _CONTROLS if c[3] == 'MANUAL')
        scoreable = pass_count + fail_count + partial_count
        score = round(pass_count / scoreable * 100, 1) if scoreable else None

        with connection.cursor() as cur:
            # Assessment
            cur.execute("""
                INSERT INTO plugin_compliance_assessment_assessment
                    (scan_history_id, framework, status, pass_count, fail_count,
                     partial_count, manual_count, compliance_score,
                     html_report_path, pdf_report_path, attestation_path,
                     attestation_hash, created_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, [
                scan.id, 'pci_dss_4', 'COMPLETE',
                pass_count, fail_count, partial_count, manual_count, score,
                '', '', '', '',
                now_str, completed_str,
            ])
            assessment_id = cur.fetchone()[0]

            # Controls + Evidence
            for (ctrl_id, ctrl_name, section, result, confidence, remediation, evidence_rows) in _CONTROLS:
                cur.execute("""
                    INSERT INTO plugin_compliance_assessment_control_result
                        (assessment_id, control_id, control_name, section,
                         result, confidence, static_remediation, ai_remediation, ai_enriched_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, [
                    assessment_id, ctrl_id, ctrl_name, section,
                    result, confidence, remediation, '', None,
                ])
                control_result_id = cur.fetchone()[0]

                for (ev_type, ev_id, ev_desc, ev_detail) in evidence_rows:
                    cur.execute("""
                        INSERT INTO plugin_compliance_assessment_evidence
                            (control_result_id, evidence_type, evidence_id, description, detail)
                        VALUES (%s, %s, %s, %s, %s)
                    """, [
                        control_result_id, ev_type, ev_id, ev_desc,
                        json.dumps(ev_detail),
                    ])

        self._print_access_info(scan.id, assessment_id)

    def _ensure_tables(self):
        with connection.cursor() as cur:
            cur.execute(_CREATE_ASSESSMENT)
            cur.execute(_CREATE_CONTROL)
            cur.execute(_CREATE_EVIDENCE)

    def _print_access_info(self, scan_id: int, assessment_id: int) -> None:
        self.stdout.write(self.style.SUCCESS('\n✓ Compliance demo data ready'))
        self.stdout.write('')
        self.stdout.write('  Scan ID      : ' + str(scan_id))
        self.stdout.write('  Assessment ID: ' + str(assessment_id))
        self.stdout.write('  Framework    : PCI-DSS 4.0  (COMPLETE)')
        self.stdout.write('')
        self.stdout.write('  API endpoint : /api/plugins/compliance_assessment/assessments/')
        self.stdout.write(f'  Filter by    : ?scan_id={scan_id}')
        self.stdout.write('')
        self.stdout.write('  Frontend URL : /p/compliance-assessment?scan_id=' + str(scan_id))
        self.stdout.write('')
        self.stdout.write('  Teardown     : python manage.py seed_compliance_demo --teardown')
