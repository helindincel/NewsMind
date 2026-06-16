from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class SummaryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Summary:
    article_id: str
    model_version: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str | None = None
    status: SummaryStatus = SummaryStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int | None = None
    error: str | None = None
