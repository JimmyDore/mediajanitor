"""Celery tasks for background processing."""

from typing import Any

from app.celery_app import celery_app


@celery_app.task(bind=True, name="test_task")  # type: ignore[untyped-decorator]
def test_task(self: Any, value: str) -> dict[str, str]:
    """Test task to verify Celery is working.

    Args:
        value: A test input value

    Returns:
        Dict with status and input value
    """
    return {"status": "success", "input": value}
