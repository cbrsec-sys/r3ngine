import io
import json
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role

from dashboard.models import Project
from scanEngine.models import EngineType
from startScan.models import (
    Command,
    DirectoryFile,
    DirectoryScan,
    EndPoint,
    Parameter,
    ScanActivity,
    ScanHistory,
    SecretLeak,
    Subdomain,
    Vulnerability,
)
from targetApp.models import Domain

User = get_user_model()


class AiExportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="ai-export-user",
            password="testpassword",
            email="ai-export@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.force_login(self.user)
        assign_role(self.user, "sys_admin")

        self.project = Project.objects.create(
            name="AI Export Project",
            slug="ai-export-project",
            insert_date=timezone.now(),
        )
        self.engine = EngineType.objects.create(
            engine_name="AI Export Engine",
            yaml_configuration="",
        )
        self.domain = Domain.objects.create(
            name="ai-export.example",
            project=self.project,
            insert_date=timezone.now(),
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            stop_scan_date=timezone.now(),
            scan_status=2,
            tasks=["vulnerability_scan", "dir_file_fuzz", "fetch_url"],
        )
        self.other_scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            stop_scan_date=timezone.now(),
            scan_status=2,
            tasks=["vulnerability_scan"],
        )

        self.subdomain = Subdomain.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            name="admin.ai-export.example",
            http_url="https://admin.ai-export.example",
            http_status=200,
            is_important=True,
            page_title="Admin Portal",
            criticality_level=5,
        )
        self.endpoint = EndPoint.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=self.subdomain,
            http_url="https://admin.ai-export.example/graphql",
            http_status=200,
            matched_gf_patterns="graphql,debug",
            page_title="GraphQL",
        )
        Parameter.objects.create(
            endpoint=self.endpoint,
            scan_history=self.scan,
            name="access_token",
            type="js_ast",
            confidence=90,
            is_auth_related=True,
            observed_in_graphql=True,
        )
        self.vulnerability = Vulnerability.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=self.subdomain,
            endpoint=self.endpoint,
            name="GraphQL Introspection Enabled",
            severity=3,
            source="nuclei",
            http_url=self.endpoint.http_url,
            description="GraphQL introspection is exposed.",
            impact="Schema disclosure may help attackers map hidden operations.",
            remediation="Disable introspection in production.",
            request="GET /graphql",
            response='{"data":{"__schema":{}}}',
            correlation_score=88.0,
            discovered_date=timezone.now(),
        )
        Vulnerability.objects.create(
            scan_history=self.other_scan,
            target_domain=self.domain,
            name="Historical Finding Should Not Leak",
            severity=4,
            source="nuclei",
            http_url="https://old.ai-export.example/debug",
            description="Should not appear in current scan export.",
            discovered_date=timezone.now(),
        )
        SecretLeak.objects.create(
            scan_history=self.scan,
            subdomain=self.subdomain,
            tool_name="trufflehog",
            secret_type="AWS Key",
            source_url="https://admin.ai-export.example/app.js",
            match_content="AKIA_TEST_EXAMPLE",
        )
        directory_file = DirectoryFile.objects.create(
            name=".env",
            url="https://admin.ai-export.example/.env",
            http_status=200,
            content_type="text/plain",
        )
        directory_scan = DirectoryScan.objects.create(scanned_date=timezone.now())
        directory_scan.directory_files.add(directory_file)
        self.subdomain.directories.add(directory_scan)

        activity = ScanActivity.objects.create(
            scan_of=self.scan,
            title="Run GraphQL Checks",
            name="graphql_scan",
            time=timezone.now(),
            time_started=timezone.now(),
            time_ended=timezone.now(),
            tier=5,
            status=2,
        )
        Command.objects.create(
            scan_history=self.scan,
            activity=activity,
            command="nuclei -u https://admin.ai-export.example/graphql",
            return_code=0,
            output="GraphQL Introspection Enabled",
            time=timezone.now(),
        )

    def _read_zip(self, response):
        zip_buffer = io.BytesIO(b"".join(response.streaming_content))
        return zipfile.ZipFile(zip_buffer, "r")

    def test_export_ai_bundle_returns_zip_with_expected_files(self):
        url = reverse("api:scan_summary_export_ai_api", kwargs={"slug": self.project.slug, "id": self.scan.id})
        response = self.client.post(url, {
            "preset": "analyst_assist",
            "include_raw_outputs": False,
            "include_timeline": True,
            "include_sidecars": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/zip")

        with self._read_zip(response) as zip_file:
            names = set(zip_file.namelist())
            self.assertIn("ai_bundle.md", names)
            self.assertIn("ai_bundle.json", names)
            self.assertIn("findings.ndjson", names)
            self.assertIn("assets.ndjson", names)
            self.assertIn("manifest.json", names)
            self.assertIn("prompt.txt", names)
            self.assertNotIn("commands.ndjson", names)

            bundle = json.loads(zip_file.read("ai_bundle.json"))
            markdown = zip_file.read("ai_bundle.md").decode("utf-8")
            manifest = json.loads(zip_file.read("manifest.json"))

        self.assertEqual(bundle["metadata"]["scan_id"], self.scan.id)
        self.assertEqual(bundle["counts"]["vulnerabilities"], 1)
        self.assertEqual(bundle["counts"]["secret_leaks"], 1)
        self.assertIn("GraphQL Introspection Enabled", markdown)
        self.assertIn("AKIA_TEST_EXAMPLE", markdown)
        self.assertNotIn("Historical Finding Should Not Leak", markdown)
        self.assertNotIn("Historical Finding Should Not Leak", json.dumps(bundle))
        self.assertIn("ai_bundle.md", manifest["included_files"])
        self.assertEqual(manifest["goal"], "analyst_assist")

    def test_export_ai_bundle_includes_commands_sidecar_only_on_opt_in(self):
        url = reverse("api:scan_summary_export_ai_api", kwargs={"slug": self.project.slug, "id": self.scan.id})
        response = self.client.post(url, {
            "preset": "analyst_assist",
            "include_raw_outputs": True,
            "include_timeline": False,
            "include_sidecars": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self._read_zip(response) as zip_file:
            names = set(zip_file.namelist())
            self.assertIn("commands.ndjson", names)
            commands_lines = zip_file.read("commands.ndjson").decode("utf-8").strip().splitlines()
            self.assertGreaterEqual(len(commands_lines), 1)
            first_command = json.loads(commands_lines[0])

        self.assertEqual(first_command["record_type"], "command")
        self.assertIn("nuclei -u https://admin.ai-export.example/graphql", first_command["command"])
