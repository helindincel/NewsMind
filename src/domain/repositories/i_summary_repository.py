from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.summary import Summary


class ISummaryRepository(ABC):
    @abstractmethod
    def save(self, summary: Summary) -> Summary: ...

    @abstractmethod
    def find_by_article_id(self, article_id: str, model_version: str) -> Summary | None: ...

    @abstractmethod
    def find_by_id(self, summary_id: str) -> Summary | None: ...

    @abstractmethod
    def update_status(
        self,
        summary_id: str,
        status: str,
        text: str | None = None,
        error: str | None = None,
    ) -> None: ...
