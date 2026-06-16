from __future__ import annotations

import os
import pytest

os.environ.setdefault("NEWS_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("USE_REDIS", "false")

from src.infrastructure.cache.in_memory_adapter import InMemoryCacheAdapter


class TestInMemoryCacheIntegration:
    """Full cache lifecycle integration tests."""

    def test_full_lifecycle(self):
        cache = InMemoryCacheAdapter(max_size=10)
        cache.set("key", {"data": [1, 2, 3]}, ttl=60)
        assert cache.exists("key")
        result = cache.get("key")
        assert result == {"data": [1, 2, 3]}
        cache.delete("key")
        assert not cache.exists("key")
        assert cache.get("key") is None

    def test_max_size_under_load(self):
        cache = InMemoryCacheAdapter(max_size=5)
        for i in range(10):
            cache.set(f"key-{i}", i, ttl=60)
        assert cache.size() == 5

    def test_cache_stores_news_list_dto(self):
        from src.application.dtos.news_dto import ArticleDTO, NewsListDTO
        from datetime import datetime, timezone

        cache = InMemoryCacheAdapter()
        dto = NewsListDTO(
            articles=[
                ArticleDTO(
                    id="a1",
                    title="Test",
                    url="https://example.com",
                    published_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
                )
            ],
            page=1,
            page_size=20,
            total=1,
        )
        cache.set("news:top:1:20", dto, ttl=300)
        retrieved = cache.get("news:top:1:20")
        assert retrieved is not None
        assert retrieved.articles[0].title == "Test"
