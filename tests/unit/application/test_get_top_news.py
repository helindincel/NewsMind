from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.application.use_cases.get_top_news import GetTopNewsUseCase
from src.domain.entities.article import Article
from src.domain.exceptions import NewsProviderException


def _make_use_case(
    news_provider, article_repo, summary_repo, summarizer, cache
) -> GetTopNewsUseCase:
    return GetTopNewsUseCase(
        news_provider=news_provider,
        article_repo=article_repo,
        summary_repo=summary_repo,
        summarizer=summarizer,
        cache=cache,
        model_version="test-model",
    )


def _make_article(idx: int = 1, words: int = 20) -> Article:
    return Article(
        id=f"article-{idx}",
        title=f"Article {idx}",
        url=f"https://example.com/article-{idx}",
        content=("word " * words).strip(),
        image_url=f"https://example.com/img-{idx}.jpg",
        published_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
    )


class TestGetTopNewsUseCase:
    def test_returns_cached_result_on_second_call(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(1)]
        mock_news_provider.fetch_top_headlines.return_value = (articles, 1)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        uc.execute(page=1, page_size=20)
        uc.execute(page=1, page_size=20)

        # NewsAPI should be called only once; second call hits cache
        assert mock_news_provider.fetch_top_headlines.call_count == 1

    def test_summarizer_called_for_articles_with_sufficient_content(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(1, words=20)]
        mock_news_provider.fetch_top_headlines.return_value = (articles, 1)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        result = uc.execute()

        mock_summarizer.summarize.assert_called_once()
        assert result.articles[0].summary_text == "Mocked summary text."

    def test_summarizer_not_called_for_short_content(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(1, words=3)]
        mock_news_provider.fetch_top_headlines.return_value = (articles, 1)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        result = uc.execute()

        mock_summarizer.summarize.assert_not_called()
        assert result.articles[0].summary_text is None

    def test_news_provider_exception_propagates(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        mock_news_provider.fetch_top_headlines.side_effect = NewsProviderException(
            "API down"
        )
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        with pytest.raises(NewsProviderException):
            uc.execute()

    def test_articles_are_deduplicated_in_repo(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        article = _make_article(1)
        mock_news_provider.fetch_top_headlines.return_value = ([article, article], 2)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        # Two pages with same article → repo deduplicates by URL
        uc.execute(page=1, page_size=20)
        assert len(article_repo._articles) == 1

    def test_total_pages_computed_correctly(
        self, mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
    ):
        articles = [_make_article(i) for i in range(5)]
        mock_news_provider.fetch_top_headlines.return_value = (articles, 105)
        uc = _make_use_case(
            mock_news_provider, article_repo, summary_repo, mock_summarizer, cache
        )

        result = uc.execute(page=1, page_size=20)

        assert result.total_pages == 6  # ceil(105/20)
