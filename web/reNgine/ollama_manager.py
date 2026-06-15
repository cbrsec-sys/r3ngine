import logging
import socket
import docker
from django.core.cache import cache

logger = logging.getLogger(__name__)

OLLAMA_CONTAINER_NAME = 'ollama'
OLLAMA_IMAGE_NAME = 'ollama/ollama:latest'

class OllamaUnavailableError(Exception):
    pass

class OllamaStartError(Exception):
    pass

class OllamaManager:

    def _get_client(self):
        try:
            return docker.from_env()
        except docker.errors.DockerException as e:
            raise OllamaUnavailableError(f"Docker socket not available: {e}")

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
            logger.debug(f"[OllamaManager] Could not discover network, using fallback: {e}")
            return 'r3ngine_r3ngine_network'

    def start(self):
        client = self._get_client()

        # Remove any existing ollama container (may be stopped from a previous session)
        try:
            existing = client.containers.get(OLLAMA_CONTAINER_NAME)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        try:
            client.images.get(OLLAMA_IMAGE_NAME)
        except docker.errors.ImageNotFound:
            logger.info(f"[OllamaManager] Image '{OLLAMA_IMAGE_NAME}' not found locally. Attempting to pull...")
            try:
                client.images.pull(OLLAMA_IMAGE_NAME)
                logger.info(f"[OllamaManager] Image '{OLLAMA_IMAGE_NAME}' pulled successfully.")
            except docker.errors.APIError as e:
                raise OllamaStartError(f"Failed to pull Ollama image: {e}")

        network = self._discover_network(client)

        try:
            client.containers.run(
                OLLAMA_IMAGE_NAME,
                detach=True,
                name=OLLAMA_CONTAINER_NAME,
                network=network,
                volumes={'r3ngine_ollama_data': {'bind': '/root/.ollama', 'mode': 'rw'}},
                ports={'11434/tcp': 11434},
                labels={
                    'com.docker.compose.project': 'r3ngine',
                    'com.docker.compose.service': 'ollama'
                },
                restart_policy={'Name': 'no'},
                mem_limit='4g',
                mem_reservation='2g'
            )
        except docker.errors.APIError as e:
            raise OllamaStartError(f"Failed to start Ollama container: {e}")

    def stop(self):
        try:
            client = self._get_client()
            container = client.containers.get(OLLAMA_CONTAINER_NAME)
            if container.status == 'running':
                container.stop(timeout=10)
        except (docker.errors.NotFound, OllamaUnavailableError):
            pass

    def is_running(self):
        try:
            client = self._get_client()
            container = client.containers.get(OLLAMA_CONTAINER_NAME)
            return container.status == 'running'
        except (docker.errors.NotFound, OllamaUnavailableError):
            return False
