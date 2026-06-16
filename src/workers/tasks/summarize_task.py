"""
Summarization Celery task — Phase 3 implementation.

Flow:
  API  →  POST /summaries  →  enqueue summarize_article(article_id)
  Worker picks up the task, runs HuggingFace inference,
  writes result to PostgreSQL + Redis, logs outcome.
"""

from __future__ import annotations

import time

import structlog

from src.workers.celery_app import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(
    name="summarize_article",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def summarize_article(self, article_id: str, model_version: str) -> dict:
    """
    Asynchronously summarize an article and persist the result.

    Args:
        article_id:    UUID of the Article in the database.
        model_version: HuggingFace model name/version string.

    Returns:
        dict: {article_id, status, summary_text | error}
    """
    log.info(
        "summarize_task.started",
        article_id=article_id,
        model_version=model_version,
        task_id=self.request.id,
    )

    from src.config.settings import get_settings
    from src.domain.entities.summary import Summary, SummaryStatus
    from src.domain.exceptions import ContentTooShortException, SummarizationException
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

    settings = get_settings()

    # ── Resolve adapters (Phase 3: swap to Postgres/Redis when USE_REDIS=true) ─
    article_repo: IArticleRepository
    summary_repo: ISummaryRepository
    cache: ICache

    if settings.USE_REDIS and settings.DATABASE_URL:
        from src.infrastructure.cache.redis_adapter import RedisCacheAdapter
        from src.infrastructure.database.postgres_article_repository import (
            PostgresArticleRepository,
        )
        from src.infrastructure.database.postgres_summary_repository import (
            PostgresSummaryRepository,
        )
        from src.infrastructure.database.session import init_db

        init_db(settings.DATABASE_URL)
        article_repo = PostgresArticleRepository()
        summary_repo = PostgresSummaryRepository()
        cache = RedisCacheAdapter(settings.REDIS_URL)
    else:
        # Fallback for local dev without DB/Redis
        article_repo = InMemoryArticleRepository()
        summary_repo = InMemorySummaryRepository()
        cache = InMemoryCacheAdapter()

    # ── Load article ──────────────────────────────────────────
    article = article_repo.find_by_id(article_id)
    if article is None:
        log.error("summarize_task.article_not_found", article_id=article_id)
        return {"article_id": article_id, "status": "failed", "error": "Article not found"}

    # ── Check existing summary ────────────────────────────────
    existing = summary_repo.find_by_article_id(article_id, model_version)
    if existing and existing.status.value == "completed":
        log.info("summarize_task.already_done", article_id=article_id)
        return {"article_id": article_id, "status": "completed", "summary_text": existing.text}

    # ── Create pending summary record ─────────────────────────
    summary = Summary(
        article_id=article_id,
        model_version=model_version,
        status=SummaryStatus.PROCESSING,
    )
    summary = summary_repo.save(summary)

    # ── Run inference ─────────────────────────────────────────
    start = time.perf_counter()
    try:
        if not article.has_sufficient_content():
            raise ContentTooShortException("Article content too short")

        summarizer = HuggingFaceAdapter(model_name=model_version)
        assert article.content is not None  # guarded by has_sufficient_content() above
        summary_text = summarizer.summarize(article.content)
        duration_ms = int((time.perf_counter() - start) * 1000)

        summary_repo.update_status(
            summary.id,
            status="completed",
            text=summary_text,
        )

        # Write to cache so the API can return it instantly next request
        cache_key = f"summary:{article_id}:{model_version}"
        cache.set(cache_key, summary_text, ttl=86400)  # 24 hours

        log.info(
            "summarize_task.completed",
            article_id=article_id,
            duration_ms=duration_ms,
        )
        return {"article_id": article_id, "status": "completed", "summary_text": summary_text}

    except (SummarizationException, ContentTooShortException) as exc:
        summary_repo.update_status(summary.id, status="failed", error=str(exc))
        log.warning("summarize_task.failed", article_id=article_id, error=str(exc))
        return {"article_id": article_id, "status": "failed", "error": str(exc)}

    except Exception as exc:
        summary_repo.update_status(summary.id, status="failed", error=str(exc))
        log.error("summarize_task.unexpected_error", article_id=article_id, error=str(exc))
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"article_id": article_id, "status": "failed", "error": str(exc)}
