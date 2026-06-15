# r3ngine — WebSockets (Real-Time Updates)

## Overview

r3ngine uses **Django Channels** with a Redis channel layer to push real-time scan progress updates to the web frontend and mobile app. WebSocket connections are established when a user views a scan or navigates to a real-time dashboard.

**File:** `web/reNgine/consumers.py`

---

## Architecture

```
Temporal Activity (Python)
        │  writes progress
        ▼
 PostgreSQL (ScanActivity records) or Redis Pub/Sub
        │
        ▼
 Django Channels Consumer (ASGI)
        │  pushed over WebSocket
        ▼
 React Frontend / Mobile App
```

---

## Django Channels Configuration

**File:** `web/reNgine/routing.py`

WebSocket URL patterns:
```python
websocket_urlpatterns = [
    re_path(r'ws/scan/(?P<scan_id>\d+)/$', ScanConsumer.as_asgi()),
    re_path(r'ws/log/(?P<scan_id>\d+)/$', LogConsumer.as_asgi()),
    re_path(r'ws/ad/assessment/(?P<assessment_id>\d+)/$', ADConsumer.as_asgi()),
]
```

---

## Consumer: `ScanConsumer`

Provides real-time scan status updates.

### Connection Behavior

1. Client connects to `ws://host/ws/scan/{scan_id}/`.
2. Consumer sends an initial status payload (current scan status, tasks list, timestamps).
3. Consumer subscribes to the scan's Redis channel group.
4. When a Temporal activity completes a task, it writes a `ScanActivity` record and publishes to the Redis group.
5. Consumer receives the Redis message and forwards it over the WebSocket.

### Message Format (server → client)

```json
{
  "type": "scan_progress",
  "scan_id": 42,
  "task_name": "subdomain_discovery",
  "status": "completed",
  "timestamp": "2025-05-29T10:00:00Z"
}
```

---

## Consumer: `LogConsumer`

Provides real-time tool output streaming (stdout/stderr) for running scan tasks.

### Connection Behavior

1. Client connects to `ws://host/ws/log/{scan_id}/`.
2. Consumer queries `Command` DB records for the scan and sends buffered output.
3. New log lines from running tools are pushed as they arrive (via Redis pub/sub).

### Message Format (server → client)

```json
{
  "type": "log_line",
  "command_id": 17,
  "line": "[INF] nuclei scanning https://target.example.com",
  "stream": "stdout"
}
```

---

## AD Assessment: Redis Streams

The Active Directory plugin uses **Redis Streams** (not pub/sub) for assessment progress:

- **Write path:** Each Temporal activity in `ADAssessmentWorkflow` calls `_send_ws_update(assessment_id, event_type, data)` which writes to `XADD ad:assessment:{assessment_id}`.
- **Read path:** The AD WebSocket consumer reads from the stream using `XREAD` and pushes events to the connected client.
- **Stream limit:** `maxlen=500` — the stream retains the last 500 events per assessment.

### Event Types

See [Active Directory Plugin — Temporal Workflow](../r3ngine-plugins/active_directory/docs/temporal-workflow.md) for the full event type reference.

---

## Mobile App WebSocket

The mobile app connects to the same WebSocket endpoints. The `src/api/client.ts` handles authentication by including the JWT `Authorization: Bearer` header in WebSocket upgrade requests.

For scan log streaming, the mobile app:
1. Connects to `ws://host/ws/log/{scan_id}/`.
2. Replays historical log lines on initial connection (the consumer sends buffered output).
3. Receives new log lines in real-time as tools execute.

---

## Channel Layer Configuration (`settings.py`)

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}
```

---

## Disconnection Handling

Consumers handle disconnects gracefully:
- On disconnect, the consumer unsubscribes from its channel group.
- If the scan is still running, the consumer can be reconnected — it will replay missed events from the DB/stream buffer.
- Redis channel groups are automatically cleaned up when all consumers disconnect.
