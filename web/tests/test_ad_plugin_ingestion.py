import os
import django
import tempfile
import zipfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from unittest import skipUnless
from django.test import TestCase
from unittest.mock import patch

try:
    from plugins_data.active_directory.backend.api import ADAssessmentViewSet
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADIngestion(TestCase):

    def test_zip_path_traversal_raises_value_error(self):
        """Zip containing '../evil' paths must be rejected before extraction."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, 'w') as zf:
                info = zipfile.ZipInfo('../../../etc/passwd')
                zf.writestr(info, 'root:x:0:0:root:/root:/bin/bash')

            with self.assertRaises(ValueError) as ctx:
                ADAssessmentViewSet._run_ingestion('ldap', tmp_path, 1)
            self.assertIn('Unsafe path', str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_unknown_ingest_type_returns_warning(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp.write(b'{}')
            tmp_path = tmp.name
        try:
            result = ADAssessmentViewSet._run_ingestion('unknown_type', tmp_path, 1)
            self.assertIn('warning', result)
            self.assertIn('Unknown ingest type', result['warning'])
        finally:
            os.unlink(tmp_path)

    def test_directory_with_ldap_files_auto_detects_ldap_type(self):
        """Directory containing domain_users.json triggers ldap ingest path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, 'domain_users.json'), 'w').close()
            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.ldap_parser.LDAPParser.ingest_from_directory',
                return_value=mock_result,
            ) as mock_ldap:
                result = ADAssessmentViewSet._run_ingestion('auto', tmpdir, 1)
            mock_ldap.assert_called_once_with(tmpdir, 1)
            self.assertEqual(result, mock_result)

    def test_directory_with_bloodhound_files_auto_detects_bh_type(self):
        """Directory containing users.json triggers bloodhound ingest path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, 'users.json'), 'w').close()
            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.bloodhound_parser.BloodHoundParser.ingest_from_directory',
                return_value=mock_result,
            ) as mock_bh:
                result = ADAssessmentViewSet._run_ingestion('auto', tmpdir, 1)
            mock_bh.assert_called_once_with(tmpdir, 1)
            self.assertEqual(result, mock_result)

    def test_zip_with_valid_paths_extracts_and_delegates_to_ldap(self):
        """Zip without path traversal should extract and auto-detect ldap type."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, 'w') as zf:
                zf.writestr('domain_users.json', '[]')
                zf.writestr('domain_groups.json', '[]')

            mock_result = {'imported': 0}
            with patch(
                'plugins_data.active_directory.backend.ingestion.ldap_parser.LDAPParser.ingest_from_directory',
                return_value=mock_result,
            ):
                result = ADAssessmentViewSet._run_ingestion('auto', tmp_path, 1)
            self.assertEqual(result, mock_result)
        finally:
            os.unlink(tmp_path)
