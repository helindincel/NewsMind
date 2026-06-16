from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Article:
    title: str
    url: str
    published_at: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Optional[str] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    keyword: Optional[str] = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def has_sufficient_content(self, min_words: int = 10) -> bool:
        if not self.content:
            return False
        return len(self.content.split()) >= min_words
