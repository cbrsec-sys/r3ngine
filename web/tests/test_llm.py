from django.test import TestCase
from unittest.mock import patch, MagicMock


class TestLLMSSLAndSecurity(TestCase):

    def _make_generator(self, provider_const):
        from unittest.mock import MagicMock
        from reNgine.llm import LLMBaseGenerator
        gen = LLMBaseGenerator.__new__(LLMBaseGenerator)
        gen.logger = MagicMock()
        gen.gate = MagicMock()
        gen.gate.anonymize = lambda x: x
        gen.gate.deanonymize = lambda x: x
        gen.model_name = "test-model"
        gen.provider = provider_const
        gen.api_key = "test-api-key"
        return gen

    def test_openai_ssl_verification_enabled(self):
        """OpenAI call must use SSL verification (no verify=False)."""
        from reNgine.definitions import OPENAI
        gen = self._make_generator(OPENAI)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test"}}]
        }
        with patch("requests.post", return_value=mock_response) as mock_post:
            gen._call_openai("sys", "user")
        mock_response.raise_for_status.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertNotIn("verify", call_kwargs,
                         "verify=False must not be passed — default (True) must apply")
        self.assertNotIn("proxies", call_kwargs,
                         "proxies override must not be set")

    def test_openai_fallback_to_max_completion_tokens(self):
        """OpenAI call must fallback to max_completion_tokens when max_tokens returns 400 error."""
        from reNgine.definitions import OPENAI
        gen = self._make_generator(OPENAI)

        # Mock initial 400 response for max_tokens
        mock_400 = MagicMock()
        mock_400.status_code = 400
        mock_400.text = "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."

        # Mock second 200 response for max_completion_tokens
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "choices": [{"message": {"content": "fallback success"}}]
        }

        with patch("requests.post", side_effect=[mock_400, mock_200]) as mock_post:
            result = gen._call_openai("sys", "user", max_tokens=100)

        self.assertEqual(result, "fallback success")
        self.assertEqual(mock_post.call_count, 2)

        # Verify second call used max_completion_tokens instead of max_tokens
        second_call_json = mock_post.call_args_list[1].kwargs["json"]
        self.assertNotIn("max_tokens", second_call_json)
        self.assertEqual(second_call_json.get("max_completion_tokens"), 100)

    def test_anthropic_system_field_separate(self):
        """Anthropic call must send system_message as top-level 'system' field, not in messages."""
        from reNgine.definitions import ANTHROPIC
        gen = self._make_generator(ANTHROPIC)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "test"}]
        }
        with patch("requests.post", return_value=mock_response) as mock_post:
            gen._call_anthropic("my system prompt", "my user message")
        mock_response.raise_for_status.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("system", payload, "Anthropic payload must have top-level 'system' key")
        self.assertEqual(payload["system"], "my system prompt")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "my user message"}])

    def test_anthropic_ssl_verification_enabled(self):
        """Anthropic call must use SSL verification."""
        from reNgine.definitions import ANTHROPIC
        gen = self._make_generator(ANTHROPIC)
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"type": "text", "text": "test"}]}
        with patch("requests.post", return_value=mock_response) as mock_post:
            gen._call_anthropic("sys", "user")
        mock_response.raise_for_status.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        self.assertNotIn("verify", call_kwargs)
        self.assertNotIn("proxies", call_kwargs)

    def test_gemini_api_key_in_header_not_url(self):
        """Gemini API key must be in x-goog-api-key header, NOT in the URL query string."""
        from reNgine.definitions import GEMINI
        gen = self._make_generator(GEMINI)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "test"}]}}]
        }
        with patch("requests.post", return_value=mock_response) as mock_post:
            gen._call_gemini("sys", "user")
        mock_response.raise_for_status.assert_called_once()
        url = mock_post.call_args.args[0]
        headers = mock_post.call_args.kwargs.get("headers", {})
        self.assertNotIn("key=", url, "API key must not appear in URL query string")
        self.assertIn("x-goog-api-key", headers, "API key must be in x-goog-api-key header")
        self.assertEqual(headers["x-goog-api-key"], "test-api-key")


class TestLLMSettingsSwitch(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from rolepermissions.roles import assign_role
        from dashboard.models import Project

        User = get_user_model()
        self.user = User.objects.create_user(username='llm-admin', password='x')
        assign_role(self.user, 'sys_admin')
        self.project = Project.objects.create(
            name='LLM Project',
            slug='llm-project',
            insert_date=timezone.now(),
        )

    def test_llm_enabled_follows_settings_row(self):
        from dashboard.models import LLMSettings
        from reNgine.llm import llm_enabled

        settings_row = LLMSettings.get_solo()
        self.assertFalse(settings_row.enabled)
        self.assertFalse(llm_enabled())

        settings_row.enabled = True
        settings_row.save(update_fields=['enabled'])
        self.assertTrue(llm_enabled())

    def test_toggle_endpoint_updates_settings(self):
        from dashboard.models import LLMSettings

        self.client.force_login(self.user)
        res = self.client.post(
            f'/scanEngine/{self.project.slug}/update_llm_settings',
            {'action': 'toggle_enabled', 'llm_enabled': 'true'},
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload['llm_enabled'])
        self.assertTrue(LLMSettings.get_solo().enabled)

        toolkit = self.client.get(
            f'/scanEngine/{self.project.slug}/llm_toolkit',
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(toolkit.status_code, 200)
        self.assertTrue(toolkit.json()['llm_enabled'])

