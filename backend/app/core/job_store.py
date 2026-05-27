"""
Redis-backed job store for tracking background ingestion jobs.

Why Redis and not a dict?
- A dict lives only in one process and resets on restart.
- Redis persists across restarts and works when running multiple backend replicas.
- Jobs expire automatically after 24 hours (no manual cleanup needed).
"""
import json
from datetime import datetime

import redis.asyncio as aioredis

from app.config import settings

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)

JOB_TTL_SECONDS = 60 * 60 * 24  # keep job records for 24 hours


async def create_job(job_id: str, filename: str) -> None:
    """Write an initial 'pending' record for a new ingestion job."""
    data = {
        "job_id": job_id,
        "status": "pending",          # pending → processing → done | error
        "filename": filename,
        "chunks_ingested": 0,
        "error": None,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
    }
    await _redis.setex(f"job:{job_id}", JOB_TTL_SECONDS, json.dumps(data))


async def update_job(job_id: str, **kwargs) -> None:
    """Overwrite specific fields on an existing job record."""
    key = f"job:{job_id}"
    raw = await _redis.get(key)
    if not raw:
        return
    data = json.loads(raw)
    data.update(kwargs)
    await _redis.setex(key, JOB_TTL_SECONDS, json.dumps(data))


async def get_job(job_id: str) -> dict | None:
    """Return the job record or None if it doesn't exist."""
    raw = await _redis.get(f"job:{job_id}")
    return json.loads(raw) if raw else None
