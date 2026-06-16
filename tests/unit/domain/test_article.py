from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.domain.entities.article import Article


class TestArticle:
    def test_has_sufficient_content_returns_true(self):
        article = Article(
            title="Test",
            url="https://example.com",
            content="word " * 15,
            published_at=datetime.now(timezone.utc),
        )
        assert article.has_sufficient_content() is True

    def test_has_sufficient_content_returns_false_when_short(self):
        article = Article(
            title="Test",
            url="https://example.com",
            content="only five words here",
            published_at=datetime.now(timezone.utc),
        )
        assert article.has_sufficient_content() is False

    def test_has_sufficient_content_returns_false_when_no_content(self):
        article = Article(
            title="Test",
            url="https://example.com",
            content=None,
            published_at=datetime.now(timezone.utc),
        )
        assert article.has_sufficient_content() is False

    def test_has_sufficient_content_custom_min_words(self):
        article = Article(
            title="Test",
            url="https://example.com",
            content="word " * 5,
            published_at=datetime.now(timezone.utc),
        )
        assert article.has_sufficient_content(min_words=5) is True
        assert article.has_sufficient_content(min_words=6) is False

    def test_auto_generated_id_is_uuid_string(self):
        article = Article(
            title="Test",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
        )
        assert len(article.id) == 36  # UUID4 length

    def test_explicit_id_is_preserved(self):
        article = Article(
            id="my-custom-id",
            title="Test",
            url="https://example.com",
            published_at=datetime.now(timezone.utc),
        )
        assert article.id == "my-custom-id"
