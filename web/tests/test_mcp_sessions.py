from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role

from mcp.keys import display_prefix, generate_mcp_secret, hash_mcp_secret
from mcp.models import McpApiKey, McpSession

User = get_user_model()


class McpSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sess', password='x')
        assign_role(self.user, 'penetration_tester')
        self.secret = generate_mcp_secret()
        self.key = McpApiKey.objects.create(
            user=self.user,
            name='cursor',
            prefix=display_prefix(self.secret),
            key_hash=hash_mcp_secret(self.secret),
        )
        self.mcp = APIClient()
        self.mcp.credentials(HTTP_AUTHORIZATION=f'Bearer {self.secret}')
        self.ui = APIClient()
        self.ui.force_authenticate(user=self.user)
        self.ui.force_login(self.user)

    def test_open_session_returns_id(self):
        res = self.mcp.post('/api/mcp/sessions/', {
            'transport': 'stdio',
            'client_name': 'cursor',
            'client_version': '1.0.0',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(McpSession.objects.filter(pk=res.json()['session_id']).exists())

    def test_heartbeat_unknown_session_is_401(self):
        res = self.mcp.post(
            '/api/mcp/sessions/00000000-0000-0000-0000-000000000000/heartbeat/',
            format='json',
            HTTP_X_MCP_SESSION_ID='00000000-0000-0000-0000-000000000000',
        )
        self.assertEqual(res.status_code, 401)

    def test_revoke_session_blocks_old_id_allows_new(self):
        sid = self.mcp.post('/api/mcp/sessions/', {
            'transport': 'stdio',
            'client_name': 'cursor',
            'client_version': '1',
        }, format='json').json()['session_id']
        rev = self.ui.post(f'/api/mcp/sessions/{sid}/revoke/', format='json')
        self.assertEqual(rev.status_code, 200)
        hb = self.mcp.post(
            f'/api/mcp/sessions/{sid}/heartbeat/',
            format='json',
            HTTP_X_MCP_SESSION_ID=str(sid),
        )
        self.assertEqual(hb.status_code, 401)
        new = self.mcp.post('/api/mcp/sessions/', {
            'transport': 'stdio',
            'client_name': 'cursor',
            'client_version': '1',
        }, format='json')
        self.assertEqual(new.status_code, 201)
