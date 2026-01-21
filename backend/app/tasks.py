"""Celery tasks for background processing."""

import asyncio
import logging
from typing import Any

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import User, UserSettings, async_session_maker
from app.services.sync import run_user_sync, send_sync_failure_notification

logger = logging.getLogger(__name__)


def get_configured_user_ids() -> list[int]:
    """Get list of user IDs that have Jellyfin configured.

    Runs synchronously for use in Celery tasks.
    """

    async def _get_users() -> list[int]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserSettings.user_id).where(
                    UserSettings.jellyfin_server_url.isnot(None),
                    UserSettings.jellyfin_api_key_encrypted.isnot(None),
                )
            )
            return [row[0] for row in result.fetchall()]

    return asyncio.get_event_loop().run_until_complete(_get_users())


async def _run_sync_for_user(user_id: int) -> dict[str, Any]:
    """Run sync for a single user (async helper)."""
    async with async_session_maker() as session:
        return await run_user_sync(session, user_id)


async def _get_user_email(user_id: int) -> str | None:
    """Get user email by ID (async helper)."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return user.email if user else None


def send_sync_failure_notification_for_celery(
    user_id: int,
    error_message: str,
) -> None:
    """
    Send sync failure notification from a Celery task.

    This is a synchronous wrapper that runs the async notification function
    in a new event loop. It's fire-and-forget - errors are logged but not raised.

    Args:
        user_id: The user ID whose sync failed
        error_message: The error message describing the failure
    """

    async def _send_notification() -> None:
        user_email = await _get_user_email(user_id)
        if not user_email:
            user_email = f"user_{user_id}"

        await send_sync_failure_notification(
            user_email=user_email,
            service="Scheduled Sync",
            error_message=error_message,
        )

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send_notification())
        finally:
            loop.close()
    except Exception as e:
        logger.warning(f"Failed to send sync failure notification for user {user_id}: {e}")


@celery_app.task(bind=True, name="test_task")  # type: ignore[untyped-decorator]
def test_task(self: Any, value: str) -> dict[str, str]:
    """Test task to verify Celery is working.

    Args:
        value: A test input value

    Returns:
        Dict with status and input value
    """
    return {"status": "success", "input": value}


@celery_app.task(bind=True, name="sync_all_users")  # type: ignore[untyped-decorator]
def sync_all_users(self: Any) -> dict[str, Any]:
    """Sync data for all users with configured Jellyfin settings.

    This task is scheduled to run daily at 3 AM UTC via Celery Beat.
    Each user's sync is run independently - failures don't block others.

    Returns:
        Dict with number of users synced and status
    """
    logger.info("Starting daily sync for all users")
    user_ids = get_configured_user_ids()
    logger.info(f"Found {len(user_ids)} users with configured Jellyfin settings")

    for user_id in user_ids:
        # Queue each user's sync as a separate task
        sync_user.delay(user_id)

    return {"users_synced": len(user_ids), "status": "completed"}


@celery_app.task(bind=True, name="sync_user")  # type: ignore[untyped-decorator]
def sync_user(self: Any, user_id: int) -> dict[str, Any]:
    """Sync data for a single user.

    Args:
        user_id: The user ID to sync data for

    Returns:
        Dict with sync status and results
    """
    logger.info(f"Starting sync for user {user_id}")
    try:
        # Run the async sync function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_run_sync_for_user(user_id))
        finally:
            loop.close()

        logger.info(f"Sync completed for user {user_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Sync failed for user {user_id}: {e}")
        # Send sync failure notification (fire-and-forget)
        send_sync_failure_notification_for_celery(
            user_id=user_id,
            error_message=str(e),
        )
        return {"status": "failed", "error": str(e), "user_id": user_id}
