from django.test import TestCase
from unittest.mock import patch, MagicMock
from reNgine.common_func import validate_proxies, get_random_proxy, remove_proxy_from_pool, get_valid_proxy_count
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

    def test_remove_proxy_from_pool_is_idempotent(self):
        proxy = Proxy.objects.create(
            use_proxy=True,
            proxies="http://alive.com:8080\ndead.com:8080\nsocks5://foo:1080"
        )

        self.assertTrue(remove_proxy_from_pool("http://dead.com:8080", proxy))
        proxy.refresh_from_db()
        self.assertEqual(proxy.proxies, "http://alive.com:8080\nsocks5://foo:1080")
        self.assertFalse(remove_proxy_from_pool("http://dead.com:8080", proxy))

    @patch('reNgine.common_func.requests.get')
    @patch('reNgine.common_func.random.shuffle', lambda proxies: None)
    def test_get_random_proxy_removes_invalid_entries(self, mock_get):
        proxy = Proxy.objects.create(
            use_proxy=True,
            proxies="dead.com:8080\nwork.com:8080"
        )

        def side_effect(url, **kwargs):
            proxy_url = kwargs.get('proxies', {}).get('http', '')
            if 'work.com' in proxy_url:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"ip": "1.2.3.4", "query": "1.2.3.4"}
                return mock_response
            raise Exception("Connection Refused")

        mock_get.side_effect = side_effect

        result = get_random_proxy()
        proxy.refresh_from_db()

        self.assertEqual(result, "http://work.com:8080")
        self.assertEqual(proxy.proxies, "work.com:8080")
        self.assertEqual(get_valid_proxy_count(proxy), 1)

    @patch('reNgine.common_func.requests.get')
    @patch('reNgine.common_func.random.shuffle', lambda proxies: None)
    def test_get_random_proxy_keeps_valid_entry(self, mock_get):
        proxy = Proxy.objects.create(
            use_proxy=True,
            proxies="work.com:8080"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ip": "1.2.3.4", "query": "1.2.3.4"}
        mock_get.return_value = mock_response

        result = get_random_proxy()
        proxy.refresh_from_db()

        self.assertEqual(result, "http://work.com:8080")
        self.assertEqual(proxy.proxies, "work.com:8080")
