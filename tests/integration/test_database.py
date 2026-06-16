from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.entities.article import Article
from src.domain.entities.summary import Summary, SummaryStatus
from src.infrastructure.database.postgres_article_repository import (
    PostgresArticleRepository,
)
from src.infrastructure.database.postgres_summary_repository import (
    PostgresSummaryRepository,
)


def _article(idx: int = 1) -> Article:
    return Article(
        id=f"article-{idx}",
        title=f"Integration Test Article {idx}",
        url=f"https://example.com/integration-{idx}",
        content="test content " * 15,
        image_url=f"https://example.com/img-{idx}.jpg",
        source="Test",
        published_at=datetime(2026, 6, 15, 10, idx, 0, tzinfo=timezone.utc),
    )


class TestPostgresArticleRepository:
    def test_save_and_find_by_id(self):
        repo = PostgresArticleRepository()
        a = _article(1)
        saved = repo.save(a)
        found = repo.find_by_id(saved.id)
        assert found is not None
        assert found.title == a.title

    def test_save_deduplicates_by_url(self):
        repo = PostgresArticleRepository()
        a = _article(2)
        repo.save(a)
        repo.save(a)  # second save same URL
        _, total = repo.find_top_headlines(page=1, page_size=10)
        assert total == 1

    def test_find_by_id_returns_none_for_missing(self):
        repo = PostgresArticleRepository()
        assert repo.find_by_id("nonexistent-id") is None

    def test_find_top_headlines_pagination(self):
        repo = PostgresArticleRepository()
        for i in range(5):
            repo.save(_article(i + 10))

        page1, total = repo.find_top_headlines(page=1, page_size=3)
        page2, _ = repo.find_top_headlines(page=2, page_size=3)

        assert total == 5
        assert len(page1) == 3
        assert len(page2) == 2

    def test_find_by_keyword(self):
        repo = PostgresArticleRepository()
        a = _article(20)
        a.keyword = "climate"
        repo.save(a)

        results, total = repo.find_by_keyword("climate", page=1, page_size=10)
        assert total == 1
        assert results[0].keyword == "climate"


class TestPostgresSummaryRepository:
    def test_save_and_find_by_id(self):
        article_repo = PostgresArticleRepository()
        summary_repo = PostgresSummaryRepository()

        article_repo.save(_article(30))

        s = Summary(
            id="sum-1",
            article_id="article-30",
            model_version="test-model",
            text="Test summary.",
            status=SummaryStatus.COMPLETED,
        )
        saved = summary_repo.save(s)
        found = summary_repo.find_by_id(saved.id)
        assert found is not None
        assert found.text == "Test summary."
        assert found.status == SummaryStatus.COMPLETED

    def test_find_by_article_id(self):
        article_repo = PostgresArticleRepository()
        summary_repo = PostgresSummaryRepository()

        article_repo.save(_article(31))
        s = Summary(
            id="sum-2",
            article_id="article-31",
            model_version="v1",
            text="Summary text.",
            status=SummaryStatus.COMPLETED,
        )
        summary_repo.save(s)

        found = summary_repo.find_by_article_id("article-31", "v1")
        assert found is not None
        assert found.text == "Summary text."

    def test_find_by_article_id_returns_none_for_wrong_model(self):
        article_repo = PostgresArticleRepository()
        summary_repo = PostgresSummaryRepository()

        article_repo.save(_article(32))
        s = Summary(
            id="sum-3",
            article_id="article-32",
            model_version="v1",
            text="x",
            status=SummaryStatus.COMPLETED,
        )
        summary_repo.save(s)

        assert summary_repo.find_by_article_id("article-32", "v2") is None

    def test_update_status(self):
        article_repo = PostgresArticleRepository()
        summary_repo = PostgresSummaryRepository()

        article_repo.save(_article(33))
        s = Summary(
            id="sum-4",
            article_id="article-33",
            model_version="v1",
            status=SummaryStatus.PENDING,
        )
        summary_repo.save(s)
        summary_repo.update_status("sum-4", "completed", text="Done!")

        updated = summary_repo.find_by_id("sum-4")
        assert updated.status == SummaryStatus.COMPLETED
        assert updated.text == "Done!"
