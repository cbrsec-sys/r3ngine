"""Lightweight Redis-backed job status tracker — replaces Celery AsyncResult polling for Phase 3D."""
import uuid
import json
import redis
from django.conf import settings

_redis = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=2,
    decode_responses=True,
)
JOB_TTL = 3600  # 1 hour


def create_job() -> str:
    """Create a new job entry in Redis and return its ID."""
    job_id = uuid.uuid4().hex
    _redis.setex(
        f"job:{job_id}",
        JOB_TTL,
        json.dumps({"status": "PENDING", "progress": 0, "message": "", "result": None}),
    )
    return job_id


def update_job(job_id: str, status: str, progress: int = 0, message: str = "", result=None):
    """Update job status, progress, and optional result payload."""
    _redis.setex(
        f"job:{job_id}",
        JOB_TTL,
        json.dumps({"status": status, "progress": progress, "message": message, "result": result}),
    )


def get_job(job_id: str) -> dict:
    """Return current job state, or {"status": "NOT_FOUND"} if expired/unknown."""
    raw = _redis.get(f"job:{job_id}")
    return json.loads(raw) if raw else {"status": "NOT_FOUND"}
