from __future__ import annotations

from typing import List, Optional

import structlog

from src.application.dtos.news_dto import ArticleDTO, NewsListDTO
from src.domain.entities.article import Article
from src.domain.entities.summary import Summary, SummaryStatus
from src.domain.exceptions import ContentTooShortException, SummarizationException
from src.domain.ports.i_cache import ICache
from src.domain.ports.i_news_provider import INewsProvider
from src.domain.ports.i_summarizer import ISummarizer
from src.domain.repositories.i_article_repository import IArticleRepository
from src.domain.repositories.i_summary_repository import ISummaryRepository

log = structlog.get_logger(__name__)

_CACHE_TTL = 1800  # 30 minutes


class GetTopNewsUseCase:
    def __init__(
        self,
        news_provider: INewsProvider,
        article_repo: IArticleRepository,
        summary_repo: ISummaryRepository,
        summarizer: ISummarizer,
        cache: ICache,
        model_version: str,
    ) -> None:
        self._news_provider = news_provider
        self._article_repo = article_repo
        self._summary_repo = summary_repo
        self._summarizer = summarizer
        self._cache = cache
        self._model_version = model_version

    def execute(self, page: int = 1, page_size: int = 20) -> NewsListDTO:
        cache_key = f"news:top:{page}:{page_size}"
        cached: Optional[NewsListDTO] = self._cache.get(cache_key)
        if cached is not None:
            log.info("news.cache_hit", cache_key=cache_key)
            return cached

        log.info("news.cache_miss", cache_key=cache_key)
        articles, total = self._news_provider.fetch_top_headlines(page, page_size)
        saved = [self._article_repo.save(a) for a in articles]
        result = NewsListDTO(
            articles=self._build_article_dtos(saved),
            page=page,
            page_size=page_size,
            total=total,
        )
        self._cache.set(cache_key, result, ttl=_CACHE_TTL)
        return result

    # ── private ──────────────────────────────────────────────

    def _build_article_dtos(self, articles: List[Article]) -> List[ArticleDTO]:
        dtos: List[ArticleDTO] = []
        for article in articles:
            summary = self._summary_repo.find_by_article_id(
                article.id, self._model_version
            )
            if summary is None and article.has_sufficient_content():
                summary = self._run_summarizer(article)

            dtos.append(
                ArticleDTO(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    published_at=article.published_at,
                    image_url=article.image_url,
                    source=article.source,
                    summary_text=summary.text if summary else None,
                    summary_status=summary.status.value if summary else None,
                )
            )
        return dtos

    def _run_summarizer(self, article: Article) -> Optional[Summary]:
        try:
            text = self._summarizer.summarize(article.content)  # type: ignore[arg-type]
            summary = Summary(
                article_id=article.id,
                model_version=self._model_version,
                text=text,
                status=SummaryStatus.COMPLETED,
            )
            return self._summary_repo.save(summary)
        except (SummarizationException, ContentTooShortException) as exc:
            log.warning(
                "summarizer.skipped", article_id=article.id, reason=str(exc)
            )
            return None
