from __future__ import annotations

from typing import Optional

import structlog

from src.domain.entities.summary import Summary, SummaryStatus
from src.domain.repositories.i_summary_repository import ISummaryRepository
from src.infrastructure.database.models import SummaryModel
from src.infrastructure.database.session import get_session

log = structlog.get_logger(__name__)


class PostgresSummaryRepository(ISummaryRepository):
    def save(self, summary: Summary) -> Summary:
        with get_session() as session:
            row = SummaryModel(
                id=summary.id,
                article_id=summary.article_id,
                model_version=summary.model_version,
                summary_text=summary.text,
                status=summary.status.value,
                duration_ms=summary.duration_ms,
                error=summary.error,
                created_at=summary.created_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._to_entity(row)

    def find_by_article_id(
        self, article_id: str, model_version: str
    ) -> Optional[Summary]:
        with get_session() as session:
            row = (
                session.query(SummaryModel)
                .filter_by(article_id=article_id, model_version=model_version)
                .first()
            )
            return self._to_entity(row) if row else None

    def find_by_id(self, summary_id: str) -> Optional[Summary]:
        with get_session() as session:
            row = session.query(SummaryModel).filter_by(id=summary_id).first()
            return self._to_entity(row) if row else None

    def update_status(
        self,
        summary_id: str,
        status: str,
        text: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        with get_session() as session:
            row = session.query(SummaryModel).filter_by(id=summary_id).first()
            if row is None:
                log.warning("summary.update_status.not_found", summary_id=summary_id)
                return
            row.status = status
            if text is not None:
                row.summary_text = text
            if error is not None:
                row.error = error
            session.commit()

    # ── private ──────────────────────────────────────────────

    @staticmethod
    def _to_entity(row: SummaryModel) -> Summary:
        return Summary(
            id=row.id,
            article_id=row.article_id,
            model_version=row.model_version,
            text=row.summary_text,
            status=SummaryStatus(row.status),
            duration_ms=row.duration_ms,
            error=row.error,
            created_at=row.created_at,
        )
