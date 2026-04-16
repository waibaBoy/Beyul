"""Thin Redis-backed response cache with TTL and JSON serialisation."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis  # type: ignore[import-untyped]

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            retry_on_timeout=True,
        )
    return _pool


async def cache_get(key: str) -> Any | None:
    try:
        r = await _get_redis()
        raw = await r.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception:
        logger.debug("cache miss (error) for %s", key, exc_info=True)
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 30) -> None:
    try:
        r = await _get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        logger.debug("cache set failed for %s", key, exc_info=True)


async def cache_delete_pattern(pattern: str) -> None:
    try:
        r = await _get_redis()
        cursor: int = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.debug("cache delete pattern failed for %s", pattern, exc_info=True)
