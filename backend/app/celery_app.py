"""Celery application configuration."""

from celery import Celery

from app.config import get_settings

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
)
