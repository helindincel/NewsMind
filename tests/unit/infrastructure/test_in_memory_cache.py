from __future__ import annotations

import time

import pytest

from src.infrastructure.cache.in_memory_adapter import InMemoryCacheAdapter


class TestInMemoryCacheAdapter:
    def test_set_and_get(self):
        cache = InMemoryCacheAdapter()
        cache.set("key1", {"data": 42}, ttl=60)
        assert cache.get("key1") == {"data": 42}

    def test_get_returns_none_for_missing_key(self):
        cache = InMemoryCacheAdapter()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        cache = InMemoryCacheAdapter()
        cache.set("key", "value", ttl=0)
        # Ensure expiry time has passed
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_exists_true_for_fresh_key(self):
        cache = InMemoryCacheAdapter()
        cache.set("key", "v", ttl=60)
        assert cache.exists("key") is True

    def test_exists_false_for_missing_key(self):
        cache = InMemoryCacheAdapter()
        assert cache.exists("nope") is False

    def test_delete_removes_key(self):
        cache = InMemoryCacheAdapter()
        cache.set("key", "v", ttl=60)
        cache.delete("key")
        assert cache.get("key") is None

    def test_max_size_evicts_oldest(self):
        cache = InMemoryCacheAdapter(max_size=3)
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        cache.set("c", 3, ttl=60)
        cache.set("d", 4, ttl=60)  # evicts "a"

        assert cache.size() == 3
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_lru_refresh_prevents_eviction(self):
        cache = InMemoryCacheAdapter(max_size=3)
        cache.set("a", 1, ttl=60)
        cache.set("b", 2, ttl=60)
        cache.set("c", 3, ttl=60)
        cache.get("a")           # refresh "a" — now it is the most recent
        cache.set("d", 4, ttl=60)  # should evict "b" (oldest after refresh)

        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_overwrite_existing_key(self):
        cache = InMemoryCacheAdapter()
        cache.set("key", "old", ttl=60)
        cache.set("key", "new", ttl=60)
        assert cache.get("key") == "new"
