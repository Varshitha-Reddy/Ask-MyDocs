import json

import redis.asyncio as aioredis
from loguru import logger

from app.config import settings

# Async Redis client — one connection reused across all requests
_redis = aioredis.from_url(settings.redis_url, decode_responses=True)


async def get_cached_result(key: str) -> dict | None:
    try:
        data = await _redis.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        # If Redis is down, we skip the cache and do the full search.
        # This keeps the app working even when Redis is unavailable.
        logger.warning(f"Redis GET failed (cache miss forced): {e}")
        return None


async def cache_result(key: str, result: dict) -> None:
    try:
        await _redis.setex(
            key,
            settings.redis_ttl,
            json.dumps(result),
        )
    except Exception as e:
        logger.warning(f"Redis SET failed (result not cached): {e}")
