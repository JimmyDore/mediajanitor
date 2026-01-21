"""Celery application configuration."""

import asyncio
import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Use celery_broker_url if set, otherwise fall back to redis_url
broker_url = settings.celery_broker_url or settings.redis_url
result_backend = settings.celery_result_backend or settings.redis_url

celery_app = Celery(
    "plex-dashboard",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"],
)


@worker_process_init.connect  # type: ignore[untyped-decorator]
def init_worker(**kwargs: object) -> None:
    """Initialize database settings when Celery worker starts.

    This ensures SQLite WAL mode and busy_timeout are set for Celery connections,
    matching the FastAPI backend configuration.
    """
    from app.database import init_db_settings

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(init_db_settings())
            logger.info("Celery worker: SQLite WAL mode and busy_timeout initialized")
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"Celery worker: Failed to initialize DB settings: {e}")

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    worker_prefetch_multiplier=1,  # One task at a time per worker
    # Celery Beat schedule for periodic tasks
    beat_schedule={
        "sync-all-users-daily": {
            "task": "sync_all_users",
            "schedule": crontab(hour=3, minute=0),  # 3 AM UTC daily
        },
    },
)
