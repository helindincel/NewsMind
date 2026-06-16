from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Article:
    title: str
    url: str
    published_at: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str | None = None
    image_url: str | None = None
    source: str | None = None
    keyword: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def has_sufficient_content(self, min_words: int = 10) -> bool:
        if not self.content:
            return False
        return len(self.content.split()) >= min_words
