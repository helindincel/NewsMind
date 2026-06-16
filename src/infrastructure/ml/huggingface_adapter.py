from __future__ import annotations

import time

import structlog

from src.domain.exceptions import ContentTooShortException, SummarizationException
from src.domain.ports.i_summarizer import ISummarizer
from src.infrastructure.ml.model_loader import ModelRegistry

log = structlog.get_logger(__name__)

_MIN_WORDS = 10


class HuggingFaceAdapter(ISummarizer):
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    def summarize(self, text: str, max_length: int = 60, min_length: int = 15) -> str:
        words = text.split()
        if len(words) < _MIN_WORDS:
            raise ContentTooShortException(f"Text has {len(words)} words; minimum is {_MIN_WORDS}")

        adjusted_max = min(max_length, len(words) - 1)
        adjusted_min = min(min_length, max(5, adjusted_max // 2))

        model = ModelRegistry.get(self._model_name)
        start = time.perf_counter()
        try:
            result = model(
                text,
                max_length=adjusted_max,
                min_length=adjusted_min,
                do_sample=False,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            log.info(
                "summarization.completed",
                duration_ms=duration_ms,
                input_words=len(words),
            )
            return result[0]["summary_text"]
        except Exception as exc:
            log.error("summarization.failed", error=str(exc), words=len(words))
            raise SummarizationException(f"Model inference failed: {exc}") from exc
