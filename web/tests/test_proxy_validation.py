from django.test import TestCase
from unittest.mock import patch, MagicMock
from reNgine.common_func import validate_proxies, get_random_proxy
from scanEngine.models import Proxy

class ProxyValidationTests(TestCase):
    def setUp(self):
        # Clear any existing proxies
        Proxy.objects.all().delete()

    @patch('reNgine.common_func.requests.get')
    def test_validate_proxies_concurrently(self, mock_get):
        # Setup mock behavior: first proxy is working, second fails, third is working
        def side_effect(url, **kwargs):
            proxy = kwargs.get('proxies', {}).get('http', '')
            if 'work1' in proxy or 'work2' in proxy:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = 'OK'
                mock_response.headers = {}
                mock_response.json.return_value = {"ip": "1.2.3.4", "query": "1.2.3.4"}
                return mock_response
            else:
                raise Exception("Connection Refused")
        mock_get.side_effect = side_effect

        proxy_text = "work1.com:8080\ndead.com:8080\nwork2.com:1080\n"
        result = validate_proxies(proxy_text)
        self.assertIn("work1.com:8080", result)
        self.assertNotIn("dead.com:8080", result)
        self.assertIn("work2.com:1080", result)

    @patch('reNgine.common_func.requests.get')
    def test_get_random_proxy_limit(self, mock_get):
        # Create a list of 10 dead proxies
        proxy_lines = [f"dead{i}.com:8080" for i in range(10)]
        proxy_db = Proxy.objects.create(
            use_proxy=True,
            proxies="\n".join(proxy_lines)
        )

        mock_get.side_effect = Exception("Connection Timeout")

        # Calling get_random_proxy should try at most 5 proxies, not all 10
        result = get_random_proxy()
        self.assertEqual(result, '')
        self.assertEqual(mock_get.call_count, 10)
