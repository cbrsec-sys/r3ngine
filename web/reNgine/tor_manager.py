import secrets
import socket
import time
import logging

import docker
from django.core.cache import cache

logger = logging.getLogger(__name__)

TOR_CONTAINER_NAME = 'tor'
TOR_IMAGE_NAME = 'r3ngine-tor:latest'
TOR_SOCKS_HOST = 'tor'
TOR_SOCKS_PORT = 9050
TOR_CONTROL_HOST = 'tor'
TOR_CONTROL_PORT = 9051
CACHE_KEY_PASSWORD = 'tor:control_password'


class TorUnavailableError(Exception):
    pass


class TorStartError(Exception):
    pass


class TorManager:

    def _get_client(self):
        try:
            return docker.from_env()
        except docker.errors.DockerException as e:
            raise TorUnavailableError(f"Docker socket not available: {e}")

    def _discover_network(self, client):
        """Find the Docker network this container belongs to."""
        try:
            hostname = socket.gethostname()
            container = client.containers.get(hostname)
            networks = list(container.attrs['NetworkSettings']['Networks'].keys())
            # Prefer the r3ngine network
            return next(
                (n for n in networks if 'r3ngine' in n.lower()),
                networks[0] if networks else 'r3ngine_r3ngine_network'
            )
        except Exception as e:
            logger.debug(f"[TorManager] Could not discover network, using fallback: {e}")
            return 'r3ngine_r3ngine_network'

    def start(self):
        client = self._get_client()

        # Remove any existing tor container (may be stopped from a previous session)
        try:
            existing = client.containers.get(TOR_CONTAINER_NAME)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Generate a fresh random control password for this session
        password = secrets.token_hex(32)
        cache.set(CACHE_KEY_PASSWORD, password, timeout=None)

        network = self._discover_network(client)

        try:
            client.containers.run(
                TOR_IMAGE_NAME,
                detach=True,
                name=TOR_CONTAINER_NAME,
                environment={'TOR_CONTROL_PASSWORD': password},
                network=network,
                restart_policy={'Name': 'no'},
                mem_limit='256m',
            )
        except docker.errors.ImageNotFound:
            cache.delete(CACHE_KEY_PASSWORD)
            raise TorStartError(
                f"Image '{TOR_IMAGE_NAME}' not found. Run: docker compose build tor"
            )
        except docker.errors.APIError as e:
            cache.delete(CACHE_KEY_PASSWORD)
            raise TorStartError(f"Failed to start TOR container: {e}")

        try:
            self._wait_for_ready()
        except TorStartError:
            cache.delete(CACHE_KEY_PASSWORD)
            raise

    def stop(self):
        cache.delete(CACHE_KEY_PASSWORD)
        try:
            client = self._get_client()
            container = client.containers.get(TOR_CONTAINER_NAME)
            if container.status == 'running':
                container.stop(timeout=10)
        except (docker.errors.NotFound, TorUnavailableError):
            pass

    def is_running(self):
        try:
            client = self._get_client()
            container = client.containers.get(TOR_CONTAINER_NAME)
            return container.status == 'running'
        except (docker.errors.NotFound, TorUnavailableError):
            return False

    def _wait_for_ready(self, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                sock = socket.create_connection((TOR_SOCKS_HOST, TOR_SOCKS_PORT), timeout=2)
                sock.close()
                return
            except OSError:
                time.sleep(1)
        raise TorStartError(
            f"TOR SOCKS5 on {TOR_SOCKS_HOST}:{TOR_SOCKS_PORT} "
            f"did not become ready within {timeout}s"
        )

    def new_circuit(self):
        password = cache.get(CACHE_KEY_PASSWORD)
        if not password:
            raise TorUnavailableError("TOR is not running (no control password in cache)")
        try:
            from stem import Signal
            from stem.control import Controller
            with Controller.from_port(
                address=TOR_CONTROL_HOST, port=TOR_CONTROL_PORT
            ) as ctrl:
                ctrl.authenticate(password=password)
                ctrl.signal(Signal.NEWNYM)
                time.sleep(2)
        except Exception as e:
            logger.warning(f"[TorManager] Failed to rotate circuit: {e}")
            raise
