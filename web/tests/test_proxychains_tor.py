from unittest import TestCase
from unittest.mock import patch, MagicMock


class TestProxychainsWrapperTOR(TestCase):

    @patch('reNgine.utils.opsec.Proxy.objects')
    def test_fetch_proxies_returns_tor_entry_when_tor_enabled(self, mock_objects):
        from reNgine.utils.opsec import ProxychainsWrapper
        proxy = MagicMock()
        proxy.use_tor = True
        mock_objects.first.return_value = proxy

        wrapper = ProxychainsWrapper.__new__(ProxychainsWrapper)
        result = wrapper._fetch_proxies()

        self.assertEqual(result, ["socks5 tor 9050"])

    @patch('reNgine.utils.opsec.Proxy.objects')
    def test_fetch_proxies_uses_normal_path_when_tor_disabled(self, mock_objects):
        from reNgine.utils.opsec import ProxychainsWrapper
        proxy = MagicMock()
        proxy.use_tor = False
        proxy.use_proxy = False
        proxy.proxies = None
        mock_objects.first.return_value = proxy

        wrapper = ProxychainsWrapper.__new__(ProxychainsWrapper)
        result = wrapper._fetch_proxies()

        self.assertEqual(result, [])

    @patch('reNgine.utils.opsec.Proxy.objects')
    def test_should_wrap_true_when_tor_enabled(self, mock_objects):
        from reNgine.utils.opsec import ProxychainsWrapper
        proxy = MagicMock()
        proxy.use_tor = True
        mock_objects.first.return_value = proxy

        wrapper = ProxychainsWrapper.__new__(ProxychainsWrapper)
        self.assertTrue(wrapper.should_wrap())

    @patch('reNgine.utils.opsec.Proxy.objects')
    def test_should_wrap_false_when_both_disabled(self, mock_objects):
        from reNgine.utils.opsec import ProxychainsWrapper
        proxy = MagicMock()
        proxy.use_tor = False
        proxy.use_proxy = False
        proxy.use_proxychains = False
        mock_objects.first.return_value = proxy

        wrapper = ProxychainsWrapper.__new__(ProxychainsWrapper)
        self.assertFalse(wrapper.should_wrap())
