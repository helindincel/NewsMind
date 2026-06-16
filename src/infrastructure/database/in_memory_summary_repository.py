from __future__ import annotations

from src.domain.entities.summary import Summary, SummaryStatus
from src.domain.repositories.i_summary_repository import ISummaryRepository


class InMemorySummaryRepository(ISummaryRepository):
    def __init__(self) -> None:
        self._summaries: dict[str, Summary] = {}

    def save(self, summary: Summary) -> Summary:
        self._summaries[summary.id] = summary
        return summary

    def find_by_article_id(self, article_id: str, model_version: str) -> Summary | None:
        for s in self._summaries.values():
            if s.article_id == article_id and s.model_version == model_version:
                return s
        return None

    def find_by_id(self, summary_id: str) -> Summary | None:
        return self._summaries.get(summary_id)

    def update_status(
        self,
        summary_id: str,
        status: str,
        text: str | None = None,
        error: str | None = None,
    ) -> None:
        summary = self._summaries.get(summary_id)
        if summary is None:
            return
        summary.status = SummaryStatus(status)
        if text is not None:
            summary.text = text
        if error is not None:
            summary.error = error
