from __future__ import annotations

import structlog
from sqlalchemy.exc import IntegrityError

from src.domain.entities.article import Article
from src.domain.repositories.i_article_repository import IArticleRepository
from src.infrastructure.database.models import ArticleModel
from src.infrastructure.database.session import get_session

log = structlog.get_logger(__name__)


class PostgresArticleRepository(IArticleRepository):
    def save(self, article: Article) -> Article:
        with get_session() as session:
            existing = session.query(ArticleModel).filter_by(url=article.url).first()
            if existing:
                return self._to_entity(existing)

            row = ArticleModel(
                id=article.id,
                title=article.title,
                url=article.url,
                content=article.content,
                image_url=article.image_url,
                source=article.source,
                keyword=article.keyword,
                published_at=article.published_at,
                fetched_at=article.fetched_at,
            )
            try:
                session.add(row)
                session.commit()
                session.refresh(row)
                return self._to_entity(row)
            except IntegrityError:
                session.rollback()
                existing = session.query(ArticleModel).filter_by(url=article.url).first()
                return self._to_entity(existing) if existing else article

    def find_by_id(self, article_id: str) -> Article | None:
        with get_session() as session:
            row = session.query(ArticleModel).filter_by(id=article_id).first()
            return self._to_entity(row) if row else None

    def find_by_keyword(self, keyword: str, page: int, page_size: int) -> tuple[list[Article], int]:
        with get_session() as session:
            q = session.query(ArticleModel).filter(ArticleModel.keyword == keyword.lower())
            total = q.count()
            rows = (
                q.order_by(ArticleModel.published_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return [self._to_entity(r) for r in rows], total

    def find_top_headlines(self, page: int, page_size: int) -> tuple[list[Article], int]:
        with get_session() as session:
            q = session.query(ArticleModel)
            total = q.count()
            rows = (
                q.order_by(ArticleModel.published_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return [self._to_entity(r) for r in rows], total

    # ── private ──────────────────────────────────────────────

    @staticmethod
    def _to_entity(row: ArticleModel) -> Article:
        return Article(
            id=row.id,
            title=row.title,
            url=row.url,
            content=row.content,
            image_url=row.image_url,
            source=row.source,
            keyword=row.keyword,
            published_at=row.published_at,
            fetched_at=row.fetched_at,
        )
