"""Shared pytest fixtures."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from src.domain.entities.article import Article
from src.domain.entities.summary import Summary, SummaryStatus
from src.infrastructure.cache.in_memory_adapter import InMemoryCacheAdapter
from src.infrastructure.database.in_memory_article_repository import (
    InMemoryArticleRepository,
)
from src.infrastructure.database.in_memory_summary_repository import (
    InMemorySummaryRepository,
)


# ── Entities ─────────────────────────────────────────────────

@pytest.fixture
def sample_article() -> Article:
    return Article(
        id="article-1",
        title="AI Breaks New Record in Chess",
        url="https://example.com/ai-chess",
        content=(
            "An artificial intelligence system has broken new records "
            "in chess by defeating the world champion in a 10-game match. "
            "The system uses a novel reinforcement learning approach that "
            "learns from self-play without any human knowledge."
        ),
        image_url="https://example.com/images/chess.jpg",
        source="Tech Daily",
        published_at=datetime(2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_summary(sample_article: Article) -> Summary:
    return Summary(
        id="summary-1",
        article_id=sample_article.id,
        model_version="sshleifer/distilbart-cnn-12-6",
        text="AI defeats world chess champion using self-play reinforcement learning.",
        status=SummaryStatus.COMPLETED,
    )


# ── Infrastructure singletons ────────────────────────────────

@pytest.fixture
def article_repo() -> InMemoryArticleRepository:
    return InMemoryArticleRepository()


@pytest.fixture
def summary_repo() -> InMemorySummaryRepository:
    return InMemorySummaryRepository()


@pytest.fixture
def cache() -> InMemoryCacheAdapter:
    return InMemoryCacheAdapter(max_size=100)


# ── Mocks ────────────────────────────────────────────────────

@pytest.fixture
def mock_news_provider():
    return MagicMock()


@pytest.fixture
def mock_summarizer():
    summarizer = MagicMock()
    summarizer.summarize.return_value = "Mocked summary text."
    return summarizer
