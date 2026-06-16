from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SummaryResponseDTO:
    id: str
    article_id: str
    model_version: str
    status: str
    text: str | None = None
    error: str | None = None
    duration_ms: int | None = None
