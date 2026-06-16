from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.domain.entities.article import Article


class IArticleRepository(ABC):
    @abstractmethod
    def save(self, article: Article) -> Article:
        ...

    @abstractmethod
    def find_by_id(self, article_id: str) -> Optional[Article]:
        ...

    @abstractmethod
    def find_by_keyword(
        self, keyword: str, page: int, page_size: int
    ) -> Tuple[List[Article], int]:
        ...

    @abstractmethod
    def find_top_headlines(
        self, page: int, page_size: int
    ) -> Tuple[List[Article], int]:
        ...
