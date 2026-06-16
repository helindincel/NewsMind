from __future__ import annotations

from celery import Celery

from src.config.settings import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "hubb",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=["src.workers.tasks.summarize_task"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,  # Re-queue on worker crash
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,  # Fair dispatch for slow ML tasks
        task_track_started=True,
    )
    return app


celery_app = create_celery_app()
