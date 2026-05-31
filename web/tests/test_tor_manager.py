from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestTorManager(TestCase):

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_start_removes_existing_and_runs_new_container(self, mock_docker, mock_cache):
        from reNgine.tor_manager import TorManager
        client = mock_docker.return_value
        client.containers.get.return_value = MagicMock()  # existing container found

        tm = TorManager()
        with patch.object(tm, '_discover_network', return_value='r3ngine_r3ngine_network'):
            with patch.object(tm, '_wait_for_ready'):
                tm.start()

        client.containers.get.return_value.remove.assert_called_once_with(force=True)
        client.containers.run.assert_called_once()
        # Password was cached
        mock_cache.set.assert_called_once()
        self.assertEqual(mock_cache.set.call_args[0][0], 'tor:control_password')

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_start_when_no_existing_container(self, mock_docker, mock_cache):
        from reNgine.tor_manager import TorManager
        import docker as docker_lib
        client = mock_docker.return_value
        client.containers.get.side_effect = docker_lib.errors.NotFound('r3ngine-tor')

        tm = TorManager()
        with patch.object(tm, '_discover_network', return_value='r3ngine_r3ngine_network'):
            with patch.object(tm, '_wait_for_ready'):
                tm.start()

        client.containers.run.assert_called_once()

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_stop_clears_cache_and_stops_container(self, mock_docker, mock_cache):
        from reNgine.tor_manager import TorManager
        container = MagicMock()
        container.status = 'running'
        mock_docker.return_value.containers.get.return_value = container

        TorManager().stop()

        mock_cache.delete.assert_called_once_with('tor:control_password')
        container.stop.assert_called_once_with(timeout=10)

    @patch('reNgine.tor_manager.docker.from_env')
    def test_is_running_true(self, mock_docker):
        from reNgine.tor_manager import TorManager
        container = MagicMock()
        container.status = 'running'
        mock_docker.return_value.containers.get.return_value = container
        self.assertTrue(TorManager().is_running())

    @patch('reNgine.tor_manager.docker.from_env')
    def test_is_running_false_when_stopped(self, mock_docker):
        from reNgine.tor_manager import TorManager
        container = MagicMock()
        container.status = 'exited'
        mock_docker.return_value.containers.get.return_value = container
        self.assertFalse(TorManager().is_running())

    @patch('reNgine.tor_manager.docker.from_env')
    def test_is_running_false_when_missing(self, mock_docker):
        import docker as docker_lib
        from reNgine.tor_manager import TorManager
        mock_docker.return_value.containers.get.side_effect = docker_lib.errors.NotFound('r3ngine-tor')
        self.assertFalse(TorManager().is_running())

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_start_raises_tor_start_error_on_image_not_found(self, mock_docker, mock_cache):
        import docker as docker_lib
        from reNgine.tor_manager import TorManager, TorStartError
        client = mock_docker.return_value
        client.containers.get.side_effect = docker_lib.errors.NotFound('r3ngine-tor')
        client.containers.run.side_effect = docker_lib.errors.ImageNotFound('r3ngine-tor:latest')

        tm = TorManager()
        with patch.object(tm, '_discover_network', return_value='r3ngine_r3ngine_network'):
            with self.assertRaises(TorStartError):
                tm.start()

        mock_cache.delete.assert_called_once_with('tor:control_password')

    @patch('reNgine.tor_manager.cache')
    def test_new_circuit_raises_when_no_password_in_cache(self, mock_cache):
        from reNgine.tor_manager import TorManager, TorUnavailableError
        mock_cache.get.return_value = None

        with self.assertRaises(TorUnavailableError):
            TorManager().new_circuit()

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_start_clears_cache_on_api_error(self, mock_docker, mock_cache):
        import docker as docker_lib
        from reNgine.tor_manager import TorManager, TorStartError
        client = mock_docker.return_value
        client.containers.get.side_effect = docker_lib.errors.NotFound('r3ngine-tor')
        client.containers.run.side_effect = docker_lib.errors.APIError('network error')

        tm = TorManager()
        with patch.object(tm, '_discover_network', return_value='r3ngine_r3ngine_network'):
            with self.assertRaises(TorStartError):
                tm.start()

        mock_cache.delete.assert_called_with('tor:control_password')

    @patch('reNgine.tor_manager.cache')
    @patch('reNgine.tor_manager.docker.from_env')
    def test_start_clears_cache_when_wait_for_ready_times_out(self, mock_docker, mock_cache):
        import docker as docker_lib
        from reNgine.tor_manager import TorManager, TorStartError
        client = mock_docker.return_value
        client.containers.get.side_effect = docker_lib.errors.NotFound('r3ngine-tor')

        tm = TorManager()
        with patch.object(tm, '_discover_network', return_value='r3ngine_r3ngine_network'):
            with patch.object(tm, '_wait_for_ready', side_effect=TorStartError("timeout")):
                with self.assertRaises(TorStartError):
                    tm.start()

        mock_cache.delete.assert_called_with('tor:control_password')
