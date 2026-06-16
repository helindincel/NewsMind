from __future__ import annotations

from functools import lru_cache

import structlog

from src.application.use_cases.get_top_news import GetTopNewsUseCase
from src.application.use_cases.search_news import SearchNewsUseCase
from src.config.settings import Settings, get_settings
from src.domain.ports.i_cache import ICache
from src.domain.repositories.i_article_repository import IArticleRepository
from src.domain.repositories.i_summary_repository import ISummaryRepository
from src.infrastructure.cache.in_memory_adapter import InMemoryCacheAdapter
from src.infrastructure.database.in_memory_article_repository import (
    InMemoryArticleRepository,
)
from src.infrastructure.database.in_memory_summary_repository import (
    InMemorySummaryRepository,
)
from src.infrastructure.ml.huggingface_adapter import HuggingFaceAdapter
from src.infrastructure.news.newsapi_adapter import NewsAPIAdapter

log = structlog.get_logger(__name__)

# ── Singletons resolved once at startup ─────────────────────
_article_repo: IArticleRepository | None = None
_summary_repo: ISummaryRepository | None = None
_cache: ICache | None = None


def _resolve_repos(settings: Settings) -> None:
    global _article_repo, _summary_repo, _cache

    if settings.USE_REDIS and settings.DATABASE_URL:
        log.info("deps.using_postgres_and_redis")
        from src.infrastructure.cache.redis_adapter import RedisCacheAdapter
        from src.infrastructure.database.postgres_article_repository import (
            PostgresArticleRepository,
        )
        from src.infrastructure.database.postgres_summary_repository import (
            PostgresSummaryRepository,
        )
        from src.infrastructure.database.session import init_db

        init_db(settings.DATABASE_URL)
        _article_repo = PostgresArticleRepository()
        _summary_repo = PostgresSummaryRepository()
        _cache = RedisCacheAdapter(settings.REDIS_URL)
    else:
        log.info("deps.using_in_memory_adapters")
        _article_repo = InMemoryArticleRepository()
        _summary_repo = InMemorySummaryRepository()
        _cache = InMemoryCacheAdapter(max_size=500)


def init_dependencies() -> None:
    """Call this once from the Flask app factory."""
    _resolve_repos(get_settings())


def get_article_repo() -> IArticleRepository:
    if _article_repo is None:
        init_dependencies()
    return _article_repo  # type: ignore[return-value]


def get_summary_repo() -> ISummaryRepository:
    if _summary_repo is None:
        init_dependencies()
    return _summary_repo  # type: ignore[return-value]


def get_cache() -> ICache:
    if _cache is None:
        init_dependencies()
    return _cache  # type: ignore[return-value]


@lru_cache
def _news_provider(settings: Settings) -> NewsAPIAdapter:
    return NewsAPIAdapter(
        api_key=settings.NEWS_API_KEY,
        base_url=settings.NEWS_API_BASE_URL,
        timeout=settings.NEWS_API_TIMEOUT,
    )


@lru_cache
def _summarizer(settings: Settings) -> HuggingFaceAdapter:
    return HuggingFaceAdapter(model_name=settings.MODEL_NAME)


# ── Use-case factories ───────────────────────────────────────


def get_top_news_use_case() -> GetTopNewsUseCase:
    settings = get_settings()
    return GetTopNewsUseCase(
        news_provider=_news_provider(settings),
        article_repo=get_article_repo(),
        summary_repo=get_summary_repo(),
        summarizer=_summarizer(settings),
        cache=get_cache(),
        model_version=settings.MODEL_VERSION,
    )


def get_search_news_use_case() -> SearchNewsUseCase:
    settings = get_settings()
    return SearchNewsUseCase(
        news_provider=_news_provider(settings),
        article_repo=get_article_repo(),
        summary_repo=get_summary_repo(),
        summarizer=_summarizer(settings),
        cache=get_cache(),
        model_version=settings.MODEL_VERSION,
    )
