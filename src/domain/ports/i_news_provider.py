from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple

from src.domain.entities.article import Article


class INewsProvider(ABC):
    @abstractmethod
    def fetch_top_headlines(
        self, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Article], int]:
        ...

    @abstractmethod
    def fetch_by_keyword(
        self, keyword: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Article], int]:
        ...
