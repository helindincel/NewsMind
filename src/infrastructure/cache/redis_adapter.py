from __future__ import annotations

import json
from typing import Any

import structlog

from src.domain.ports.i_cache import ICache

log = structlog.get_logger(__name__)


class RedisCacheAdapter(ICache):
    """
    Redis-backed cache adapter.
    Uses JSON serialization (msgpack can be swapped in Phase 4 for perf).
    Falls back gracefully on Redis errors — never crashes the request.
    """

    def __init__(self, redis_url: str) -> None:
        import redis  # deferred — optional in Phase 1/2

        self._client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=2,
        )

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            log.warning("redis.get_failed", key=key, error=str(exc))
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            serialized = json.dumps(value, default=str)
            self._client.setex(key, ttl, serialized)
        except Exception as exc:
            log.warning("redis.set_failed", key=key, error=str(exc))

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as exc:
            log.warning("redis.delete_failed", key=key, error=str(exc))

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except Exception as exc:
            log.warning("redis.exists_failed", key=key, error=str(exc))
            return False

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False
