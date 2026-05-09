import json
import asyncio
import logging
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)

class StressTelemetryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scan_id = self.scope['url_route']['kwargs']['scan_id']
        self.stream_key = f"stress:telemetry:{self.scan_id}"
        self.group_name = f"stress_test_{self.scan_id}"

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for scan {self.scan_id}")

        # Start background task to tail Redis Stream
        self.keep_running = True
        self.tail_task = asyncio.create_task(self.tail_redis_stream())

    async def disconnect(self, close_code):
        self.keep_running = False
        if hasattr(self, 'tail_task'):
            self.tail_task.cancel()
        
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected for scan {self.scan_id}")

    async def tail_redis_stream(self):
        """Tails the Redis stream and sends updates to the client."""
        r = redis.StrictRedis(
            host=settings.REDIS_HOST, 
            port=settings.REDIS_PORT, 
            db=0,
            decode_responses=True
        )
        
        last_id = '$' # Start from now
        
        while self.keep_running:
            try:
                # Use XREAD to block and wait for new data
                streams = r.xread({self.stream_key: last_id}, count=10, block=5000)
                if streams:
                    for stream_name, messages in streams:
                        for msg_id, data in messages:
                            last_id = msg_id
                            payload = json.loads(data['data'])
                            await self.send(text_data=json.dumps({
                                'type': 'telemetry_update',
                                'data': payload
                            }))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error tailing Redis stream: {e}")
                await asyncio.sleep(1)

    async def stress_message(self, event):
        """Receive message from group (e.g., system alerts, control signals)."""
        await self.send(text_data=json.dumps(event))
