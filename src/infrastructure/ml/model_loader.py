from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger(__name__)


class ModelRegistry:
    """
    Lazy singleton for the HuggingFace pipeline.
    The model is loaded once per worker process on first use.
    """

    _instance: object | None = None
    _loaded_model_name: str | None = None

    @classmethod
    def get(cls, model_name: str) -> Any:
        if cls._instance is None or cls._loaded_model_name != model_name:
            from transformers import pipeline  # deferred import — heavy dependency

            log.info("model.loading", model_name=model_name)
            cls._instance = pipeline("summarization", model=model_name)
            cls._loaded_model_name = model_name
            log.info("model.loaded", model_name=model_name)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Used in tests to clear the cached model."""
        cls._instance = None
        cls._loaded_model_name = None
