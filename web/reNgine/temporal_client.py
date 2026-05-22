"""
Temporal Client Provider for r3ngine.

Provides a shared, cached Temporal client instance for use in synchronous
Django view and task code. The client is created once per process and reused
across all subsequent calls to avoid repeated TCP handshakes to the Temporal
server.

This module is safe to import from both synchronous and asynchronous contexts.
"""

import asyncio
import logging
import os
from typing import Optional

from temporalio.client import Client

logger = logging.getLogger(__name__)


class TemporalClientProvider:
    """Singleton provider for a shared Temporal client.

    The client is lazily initialized on first use and cached for subsequent
    calls within the same process. Thread-safe for concurrent Django requests
    because client creation is idempotent and we use asyncio event loops
    correctly.

    Usage in synchronous contexts (Django views, tasks):
        client = asyncio.run(TemporalClientProvider.get_client())

    Usage in asynchronous contexts (workers, management commands):
        client = await TemporalClientProvider.get_client()
    """

    _client: Optional[Client] = None

    @classmethod
    async def get_client(cls) -> Client:
        """Return a connected Temporal client, creating one if needed.

        Connects to the Temporal server at the TEMPORAL_HOST environment
        variable (default: temporal:7233) in the TEMPORAL_NAMESPACE (default:
        default).

        Returns:
            Client: A connected Temporal client instance.

        Raises:
            Exception: If connection to the Temporal server fails.
        """
        if cls._client is None:
            temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
            namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
            logger.info(
                f"[TemporalClientProvider] Connecting to {temporal_host} "
                f"namespace={namespace}..."
            )
            cls._client = await Client.connect(temporal_host, namespace=namespace)
            logger.info("[TemporalClientProvider] Connected successfully.")
        return cls._client

    @classmethod
    def reset(cls) -> None:
        """Reset the cached client (useful in tests or after connection failure).

        Clears the cached client so the next call to get_client() will create
        a fresh connection.
        """
        cls._client = None
