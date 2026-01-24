"""Content cache management service.

Functions for managing cached media items and Jellyseerr requests.
"""

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedJellyseerrRequest, CachedMediaItem, UserSettings

logger = logging.getLogger(__name__)


async def get_user_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user settings from database.

    Args:
        db: Database session
        user_id: User ID to get settings for

    Returns:
        UserSettings if found, None otherwise
    """
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalar_one_or_none()


async def lookup_jellyseerr_media_by_tmdb(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str
) -> int | None:
    """Look up Jellyseerr media ID by TMDB ID and media type.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to search for
        media_type: "movie" or "tv" (lowercase)

    Returns:
        Jellyseerr media ID if found, None otherwise.
        Note: This returns media.id (for deletion), NOT request.id.
    """
    result = await db.execute(
        select(CachedJellyseerrRequest.jellyseerr_media_id)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.tmdb_id == tmdb_id)
        .where(CachedJellyseerrRequest.media_type == media_type)
        .distinct()
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def lookup_jellyseerr_media_by_request_id(
    db: AsyncSession, user_id: int, jellyseerr_id: int
) -> int | None:
    """Look up Jellyseerr media ID by request ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        jellyseerr_id: Jellyseerr request ID

    Returns:
        Jellyseerr media ID if found, None otherwise.
    """
    result = await db.execute(
        select(CachedJellyseerrRequest.jellyseerr_media_id)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.jellyseerr_id == jellyseerr_id)
    )
    row = result.scalar_one_or_none()
    return row


async def delete_cached_media_by_tmdb_id(db: AsyncSession, user_id: int, tmdb_id: int) -> int:
    """Delete CachedMediaItem by TMDB ID stored in raw_data.ProviderIds.Tmdb.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to match in raw_data.ProviderIds.Tmdb

    Returns:
        Number of items deleted
    """
    # First, find all matching media items (TMDB ID is stored as string in JSON)
    tmdb_id_str = str(tmdb_id)
    result = await db.execute(
        select(CachedMediaItem)
        .where(CachedMediaItem.user_id == user_id)
        .where(CachedMediaItem.raw_data.isnot(None))
    )
    items = result.scalars().all()

    # Filter items by TMDB ID in raw_data
    items_to_delete = []
    for item in items:
        raw_data = item.raw_data or {}
        provider_ids = raw_data.get("ProviderIds", {})
        if provider_ids.get("Tmdb") == tmdb_id_str:
            items_to_delete.append(item.id)

    if not items_to_delete:
        logger.debug(f"No CachedMediaItem found for TMDB ID {tmdb_id}")
        return 0

    # Delete the matching items
    await db.execute(delete(CachedMediaItem).where(CachedMediaItem.id.in_(items_to_delete)))

    logger.info(f"Deleted {len(items_to_delete)} CachedMediaItem(s) for TMDB ID {tmdb_id}")
    return len(items_to_delete)


async def delete_cached_jellyseerr_request_by_tmdb_id(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str
) -> None:
    """Delete CachedJellyseerrRequest by TMDB ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to match
        media_type: "movie" or "tv" (lowercase)
    """
    await db.execute(
        delete(CachedJellyseerrRequest)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.tmdb_id == tmdb_id)
        .where(CachedJellyseerrRequest.media_type == media_type)
    )
    logger.debug(f"Deleted CachedJellyseerrRequest(s) for TMDB ID {tmdb_id}")


async def delete_cached_jellyseerr_request_by_id(
    db: AsyncSession, user_id: int, jellyseerr_id: int
) -> None:
    """Delete CachedJellyseerrRequest by Jellyseerr ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        jellyseerr_id: Jellyseerr request ID to match
    """
    await db.execute(
        delete(CachedJellyseerrRequest)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.jellyseerr_id == jellyseerr_id)
    )
    logger.debug(f"Deleted CachedJellyseerrRequest for Jellyseerr ID {jellyseerr_id}")
