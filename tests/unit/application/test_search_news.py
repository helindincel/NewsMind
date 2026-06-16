from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.application.use_cases.search_news import SearchNewsUseCase
from src.domain.entities.article import Article
from src.domain.exceptions import InvalidKeywordException, NewsProviderException


def _make_use_case(
    news_provider, article_repo, summary_repo, summarizer, cache
) -> SearchNewsUseCase:
    return SearchNewsUseCase(
        news_provider=news_provider,
        article_repo=article_repo,
        summary_repo=summary_repo,
        summarizer=summarizer,
        cache=cache,
        model_version="test-model",
    )


def _make_article(idx: int = 1) -> Article:
    return Article(
        id=f"article-{idx}",
        title=f"Climate Article {idx}",
        url=f"https://example.com/climate-{idx}",
        content=("climate word " * 15).strip(),
        image_url=f"https://example.com/img-{idx}.jpg",
        published_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
        keyword="climate",
    )


class TestSearchNewsUseCase:
    def test_calls_news_provider_with_normalized_keyword(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        mock_news_provider.fetch_by_keyword.return_value = ([], 0)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        uc.execute("  Climate  ", page=1, page_size=20)

        mock_news_provider.fetch_by_keyword.assert_called_once_with(
            "climate", 1, 20
        )

    def test_same_keyword_cached_on_second_call(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(1)]
        mock_news_provider.fetch_by_keyword.return_value = (articles, 1)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        uc.execute("climate")
        uc.execute("climate")

        assert mock_news_provider.fetch_by_keyword.call_count == 1

    def test_different_keywords_not_cached_together(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        mock_news_provider.fetch_by_keyword.return_value = ([], 0)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        uc.execute("climate")
        uc.execute("technology")

        assert mock_news_provider.fetch_by_keyword.call_count == 2

    def test_invalid_keyword_raises_value_error(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )
        with pytest.raises(ValueError):
            uc.execute("<script>alert(1)</script>")

    def test_result_dto_has_correct_fields(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(1)]
        mock_news_provider.fetch_by_keyword.return_value = (articles, 1)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        result = uc.execute("climate")

        assert len(result.articles) == 1
        dto = result.articles[0]
        assert dto.title == "Climate Article 1"
        assert dto.summary_text == "Mocked summary text."
