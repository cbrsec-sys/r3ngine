from django.test import TestCase
from dashboard.models import LinkedInCredentials


class TestLinkedInCredentialsModel(TestCase):

    def test_model_has_session_fields(self):
        session = LinkedInCredentials.objects.create(
            username='operator@example.com',
            cookies_json='[]',
            state_file_path='/var/scan_results/context/linkedin/storage_state.json',
            is_valid=False,
        )
        self.assertEqual(session.username, 'operator@example.com')
        self.assertEqual(session.cookies_json, '[]')
        self.assertEqual(session.state_file_path, '/var/scan_results/context/linkedin/storage_state.json')
        self.assertFalse(session.is_valid)
        self.assertIsNone(session.last_validated_at)

    def test_model_has_no_password_field(self):
        field_names = [f.name for f in LinkedInCredentials._meta.get_fields()]
        self.assertNotIn('password', field_names)
        self.assertIn('cookies_json', field_names)
        self.assertIn('state_file_path', field_names)
        self.assertIn('is_valid', field_names)
        self.assertIn('last_validated_at', field_names)
