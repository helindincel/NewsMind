from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.domain.entities.article import Article
from src.domain.exceptions import NewsProviderException
from src.infrastructure.news.newsapi_adapter import NewsAPIAdapter


def _make_adapter() -> NewsAPIAdapter:
    return NewsAPIAdapter(
        api_key="test-key",
        base_url="https://newsapi.org/v2",
        timeout=5,
    )


def _ok_response(articles: list, total: int = 1):
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "status": "ok",
        "totalResults": total,
        "articles": articles,
    }
    return mock


_RAW_ARTICLE = {
    "title": "Test Headline",
    "url": "https://example.com/test",
    "urlToImage": "https://example.com/img.jpg",
    "content": "Test content here. " * 5,
    "publishedAt": "2026-06-15T10:00:00Z",
    "source": {"name": "Test Source"},
    "description": "A test article.",
}


class TestNewsAPIAdapter:
    def test_fetch_top_headlines_returns_articles(self):
        adapter = _make_adapter()
        with patch.object(
            adapter._session, "get", return_value=_ok_response([_RAW_ARTICLE])
        ):
            articles, total = adapter.fetch_top_headlines(page=1, page_size=10)

        assert len(articles) == 1
        assert isinstance(articles[0], Article)
        assert articles[0].title == "Test Headline"
        assert articles[0].image_url == "https://example.com/img.jpg"
        assert total == 1

    def test_articles_without_image_are_filtered(self):
        raw = {**_RAW_ARTICLE, "urlToImage": None}
        adapter = _make_adapter()
        with patch.object(
            adapter._session, "get", return_value=_ok_response([raw])
        ):
            articles, _ = adapter.fetch_top_headlines()

        assert articles == []

    def test_timeout_raises_news_provider_exception(self):
        adapter = _make_adapter()
        with patch.object(
            adapter._session,
            "get",
            side_effect=requests.exceptions.Timeout,
        ):
            with pytest.raises(NewsProviderException, match="timed out"):
                adapter.fetch_top_headlines()

    def test_api_error_status_raises_news_provider_exception(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "status": "error",
            "message": "apiKeyInvalid",
        }
        adapter = _make_adapter()
        with patch.object(adapter._session, "get", return_value=mock_resp):
            with pytest.raises(NewsProviderException, match="apiKeyInvalid"):
                adapter.fetch_top_headlines()

    def test_fetch_by_keyword_passes_query_param(self):
        adapter = _make_adapter()
        with patch.object(
            adapter._session, "get", return_value=_ok_response([_RAW_ARTICLE])
        ) as mock_get:
            adapter.fetch_by_keyword("climate", page=1, page_size=10)

        call_kwargs = mock_get.call_args
        params = call_kwargs[1]["params"]
        assert params["q"] == "climate"
        assert params["pageSize"] == 10

    def test_published_at_parsed_correctly(self):
        adapter = _make_adapter()
        with patch.object(
            adapter._session, "get", return_value=_ok_response([_RAW_ARTICLE])
        ):
            articles, _ = adapter.fetch_top_headlines()

        assert articles[0].published_at == datetime(
            2026, 6, 15, 10, 0, 0, tzinfo=timezone.utc
        )
