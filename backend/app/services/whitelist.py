"""Whitelist CRUD operations for all whitelist types.

Uses BaseWhitelistService generic classes to eliminate duplication.
EpisodeLanguageExempt remains custom due to different field structure.
"""

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    ContentWhitelist,
    EpisodeLanguageExempt,
    FrenchOnlyWhitelist,
    JellyseerrRequestWhitelist,
    LanguageExemptWhitelist,
    LargeContentWhitelist,
)
from app.models.content import (
    EpisodeExemptItem,
    EpisodeExemptListResponse,
    RequestWhitelistListResponse,
    WhitelistListResponse,
)
from app.services.whitelist_base import (
    BaseJellyfinIdWhitelistService,
    BaseJellyseerrIdWhitelistService,
)

# ============================================================================
# Service class instances using generic base classes
# ============================================================================


class _ContentWhitelistService(BaseJellyfinIdWhitelistService[ContentWhitelist]):
    model = ContentWhitelist
    duplicate_error = "Content is already in whitelist"
    order_by_name = False  # Order by created_at desc


class _FrenchOnlyWhitelistService(BaseJellyfinIdWhitelistService[FrenchOnlyWhitelist]):
    model = FrenchOnlyWhitelist
    duplicate_error = "Item already in french-only whitelist"


class _LanguageExemptWhitelistService(BaseJellyfinIdWhitelistService[LanguageExemptWhitelist]):
    model = LanguageExemptWhitelist
    duplicate_error = "Item already in language-exempt whitelist"


class _LargeWhitelistService(BaseJellyfinIdWhitelistService[LargeContentWhitelist]):
    model = LargeContentWhitelist
    duplicate_error = "Item already in large content whitelist"


class _RequestWhitelistService(BaseJellyseerrIdWhitelistService[JellyseerrRequestWhitelist]):
    model = JellyseerrRequestWhitelist
    duplicate_error = "Request already in whitelist"


# Singleton instances
_content_whitelist = _ContentWhitelistService()
_french_only_whitelist = _FrenchOnlyWhitelistService()
_language_exempt_whitelist = _LanguageExemptWhitelistService()
_large_whitelist = _LargeWhitelistService()
_request_whitelist = _RequestWhitelistService()


# ============================================================================
# Content Whitelist (old/unwatched content protection)
# ============================================================================


async def add_to_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> ContentWhitelist:
    """Add content to user's whitelist.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if the content is already in the whitelist.
    """
    result: ContentWhitelist = await _content_whitelist.add(
        db, user_id, jellyfin_id, name, media_type, expires_at
    )
    return result


async def get_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all whitelist entries for a user."""
    return await _content_whitelist.get_list(db, user_id)


async def remove_from_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's whitelist.

    Returns True if item was found and deleted, False otherwise.
    Only deletes items that belong to the specified user.
    """
    return await _content_whitelist.remove(db, user_id, whitelist_id)


async def get_whitelist_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's content whitelist (non-expired only)."""
    return await _content_whitelist.get_ids(db, user_id)


# ============================================================================
# French-Only Whitelist (exempt from missing English audio checks)
# ============================================================================


async def add_to_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> None:
    """Add an item to the user's french-only whitelist.

    Items in this whitelist are exempt from missing English audio checks.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if item already exists.
    """
    await _french_only_whitelist.add(db, user_id, jellyfin_id, name, media_type, expires_at)


async def get_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's french-only whitelist."""
    return await _french_only_whitelist.get_list(db, user_id)


async def remove_from_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's french-only whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    return await _french_only_whitelist.remove(db, user_id, whitelist_id)


async def get_french_only_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's french-only whitelist (non-expired only)."""
    return await _french_only_whitelist.get_ids(db, user_id)


# ============================================================================
# Language-Exempt Whitelist (exempt from ALL language checks)
# ============================================================================


async def add_to_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> None:
    """Add an item to the user's language-exempt whitelist.

    Items in this whitelist are exempt from ALL language checks.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if item already exists.
    """
    await _language_exempt_whitelist.add(db, user_id, jellyfin_id, name, media_type, expires_at)


async def get_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's language-exempt whitelist."""
    return await _language_exempt_whitelist.get_list(db, user_id)


async def remove_from_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's language-exempt whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    return await _language_exempt_whitelist.remove(db, user_id, whitelist_id)


async def get_language_exempt_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's language-exempt whitelist (non-expired only)."""
    return await _language_exempt_whitelist.get_ids(db, user_id)


# ============================================================================
# Episode Language Exempt (specific episodes exempt from language checks)
# NOTE: This type has different fields and cannot use the generic base class
# ============================================================================


async def add_episode_language_exempt(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    series_name: str,
    season_number: int,
    episode_number: int,
    episode_name: str,
    expires_at: datetime | None = None,
) -> None:
    """Add an episode to the user's episode language exempt list.

    Exempts a specific episode from language checks during sync.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin series ID
        series_name: Name of the series
        season_number: Season number
        episode_number: Episode number
        episode_name: Name of the episode
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if episode already exempted.
    """
    # Check if already exempted
    result = await db.execute(
        select(EpisodeLanguageExempt).where(
            EpisodeLanguageExempt.user_id == user_id,
            EpisodeLanguageExempt.jellyfin_id == jellyfin_id,
            EpisodeLanguageExempt.season_number == season_number,
            EpisodeLanguageExempt.episode_number == episode_number,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Episode already exempted from language checks")

    entry = EpisodeLanguageExempt(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        series_name=series_name,
        season_number=season_number,
        episode_number=episode_number,
        episode_name=episode_name,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_episode_language_exempt(
    db: AsyncSession,
    user_id: int,
) -> EpisodeExemptListResponse:
    """Get all items in the user's episode language exempt list."""
    result = await db.execute(
        select(EpisodeLanguageExempt)
        .where(EpisodeLanguageExempt.user_id == user_id)
        .order_by(
            EpisodeLanguageExempt.series_name,
            EpisodeLanguageExempt.season_number,
            EpisodeLanguageExempt.episode_number,
        )
    )
    entries = result.scalars().all()

    items = [
        EpisodeExemptItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            series_name=entry.series_name,
            season_number=entry.season_number,
            episode_number=entry.episode_number,
            episode_name=entry.episode_name,
            identifier=f"S{entry.season_number:02d}E{entry.episode_number:02d}",
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return EpisodeExemptListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_episode_language_exempt(
    db: AsyncSession,
    user_id: int,
    exempt_id: int,
) -> bool:
    """Remove an episode from the user's episode language exempt list.

    Returns True if episode was found and deleted, False otherwise.
    """
    result = await db.execute(
        select(EpisodeLanguageExempt).where(
            EpisodeLanguageExempt.id == exempt_id,
            EpisodeLanguageExempt.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_episode_exempt_set(db: AsyncSession, user_id: int) -> set[tuple[str, int, int]]:
    """Get set of exempt episodes as (jellyfin_id, season, episode) tuples.

    Only returns non-expired entries for O(1) lookup during sync.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        select(
            EpisodeLanguageExempt.jellyfin_id,
            EpisodeLanguageExempt.season_number,
            EpisodeLanguageExempt.episode_number,
        ).where(
            EpisodeLanguageExempt.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                EpisodeLanguageExempt.expires_at.is_(None),
                EpisodeLanguageExempt.expires_at > now,
            ),
        )
    )
    # Convert Row objects to tuples for set membership checking
    return {(row[0], row[1], row[2]) for row in result.fetchall()}


# ============================================================================
# Large Content Whitelist (exempt from large content checks)
# ============================================================================


async def add_to_large_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> None:
    """Add an item to the user's large content whitelist.

    Items in this whitelist are exempt from large content checks.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if item already exists.
    """
    await _large_whitelist.add(db, user_id, jellyfin_id, name, media_type, expires_at)


async def get_large_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's large content whitelist."""
    return await _large_whitelist.get_list(db, user_id)


async def remove_from_large_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's large content whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    return await _large_whitelist.remove(db, user_id, whitelist_id)


async def get_large_whitelist_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's large content whitelist (non-expired only)."""
    return await _large_whitelist.get_ids(db, user_id)


# ============================================================================
# Jellyseerr Request Whitelist (exempt requests from unavailable list)
# ============================================================================


async def add_to_request_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyseerr_id: int,
    title: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> None:
    """Add a Jellyseerr request to user's whitelist.

    Args:
        db: Database session
        user_id: User ID
        jellyseerr_id: Jellyseerr request ID
        title: Request title
        media_type: "movie" or "tv"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if the request is already in the whitelist.
    """
    await _request_whitelist.add(db, user_id, jellyseerr_id, title, media_type, expires_at)


async def get_request_whitelist(
    db: AsyncSession,
    user_id: int,
) -> RequestWhitelistListResponse:
    """Get all items in the user's request whitelist."""
    return await _request_whitelist.get_list(db, user_id)


async def remove_from_request_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's request whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    return await _request_whitelist.remove(db, user_id, whitelist_id)


async def get_request_whitelist_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Get set of jellyseerr_ids in user's request whitelist (non-expired only)."""
    return await _request_whitelist.get_ids(db, user_id)
