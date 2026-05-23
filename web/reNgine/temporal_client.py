"""
Temporal Client Provider for r3ngine.

Creates a fresh Temporal client per operation. Callers wrap operations in
asyncio.new_event_loop(); a temporalio Client is bound to the event loop it
was created in, so caching across loop boundaries raises gRPC errors. The
SDK manages its own gRPC channel pool — per-operation Client() costs ~5ms
locally and is the correct pattern for synchronous Django callers.
"""
import asyncio
import logging
import os

from temporalio.client import Client

logger = logging.getLogger(__name__)


class TemporalClientProvider:
    """Factory for Temporal client connections.

    Always creates a fresh connection. Do not add caching — see module
    docstring for why caching fails across asyncio.run() boundaries.
    """

    @classmethod
    async def get_client(cls) -> Client:
        temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
        namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
        return await Client.connect(temporal_host, namespace=namespace)

    @classmethod
    def cancel_workflow(cls, workflow_id: str) -> None:
        """Cancel a running Temporal workflow synchronously (safe for Django views).

        Args:
            workflow_id: The Temporal workflow execution ID to cancel.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _cancel():
                client = await cls.get_client()
                handle = client.get_workflow_handle(workflow_id)
                await handle.cancel()
            loop.run_until_complete(_cancel())
        finally:
            loop.close()
