from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class ArticleDTO:
    id: str
    title: str
    url: str
    published_at: datetime
    image_url: Optional[str] = None
    source: Optional[str] = None
    summary_text: Optional[str] = None
    summary_status: Optional[str] = None


@dataclass
class NewsListDTO:
    articles: List[ArticleDTO]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)
