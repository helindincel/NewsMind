from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class SummaryStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Summary:
    article_id: str
    model_version: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: Optional[str] = None
    status: SummaryStatus = SummaryStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[int] = None
    error: Optional[str] = None
