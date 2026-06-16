from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SummaryResponseDTO:
    id: str
    article_id: str
    model_version: str
    status: str
    text: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
