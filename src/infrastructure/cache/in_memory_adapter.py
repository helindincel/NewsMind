from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

import structlog

from src.domain.ports.i_cache import ICache

log = structlog.get_logger(__name__)


class InMemoryCacheAdapter(ICache):
    """
    LRU in-memory cache with TTL and bounded size.
    Thread-safety note: not thread-safe; use Redis adapter in production (Phase 3).
    """

    def __init__(self, max_size: int = 500) -> None:
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._expiry: dict[str, float] = {}
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        if self._is_expired(key):
            self._evict(key)
            return None
        self._store.move_to_end(key)  # LRU refresh
        return self._store[key]

    def set(self, key: str, value: Any, ttl: int) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        self._expiry[key] = time.monotonic() + ttl
        if len(self._store) > self._max_size:
            oldest = next(iter(self._store))
            self._evict(oldest)
            log.debug("cache.eviction", evicted_key=oldest, size=len(self._store))

    def delete(self, key: str) -> None:
        self._evict(key)

    def exists(self, key: str) -> bool:
        if key not in self._store:
            return False
        if self._is_expired(key):
            self._evict(key)
            return False
        return True

    def size(self) -> int:
        return len(self._store)

    # ── private ──────────────────────────────────────────────

    def _is_expired(self, key: str) -> bool:
        return key in self._expiry and time.monotonic() > self._expiry[key]

    def _evict(self, key: str) -> None:
        self._store.pop(key, None)
        self._expiry.pop(key, None)
