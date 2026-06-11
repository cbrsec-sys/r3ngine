from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, mock_open

MOCK_YAML = "subdomain_discovery:\n  uses_tools:\n    - subfinder\n# A comment\n"


class TestYamlConfigReference(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testref', password='pass123')
        self.client.force_login(self.user)

    @patch('scanEngine.views.open', mock_open(read_data=MOCK_YAML))
    def test_returns_yaml_content(self):
        response = self.client.get('/scanEngine/default/yaml_config_reference/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('subdomain_discovery', data['content'])

    @patch('scanEngine.views.open', mock_open(read_data=MOCK_YAML))
    def test_content_is_string(self):
        response = self.client.get('/scanEngine/default/yaml_config_reference/')
        data = response.json()
        self.assertIsInstance(data['content'], str)

    def test_requires_auth(self):
        # Use a fresh client with no session to avoid triggering logged-out signals
        from django.test import Client
        anon_client = Client()
        response = anon_client.get('/scanEngine/default/yaml_config_reference/')
        # login_required redirects unauthenticated requests
        self.assertIn(response.status_code, [302, 403])
