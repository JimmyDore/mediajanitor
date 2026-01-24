"""Whitelist CRUD operations for all whitelist types."""

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
    RequestWhitelistItem,
    RequestWhitelistListResponse,
    WhitelistItem,
    WhitelistListResponse,
)

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
    # Check if already whitelisted
    result = await db.execute(
        select(ContentWhitelist).where(
            ContentWhitelist.user_id == user_id,
            ContentWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Content '{name}' is already in whitelist")

    # Create new whitelist entry
    entry = ContentWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)
    await db.flush()  # Get the ID assigned
    return entry


async def get_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all whitelist entries for a user."""
    result = await db.execute(
        select(ContentWhitelist)
        .where(ContentWhitelist.user_id == user_id)
        .order_by(ContentWhitelist.created_at.desc())
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's whitelist.

    Returns True if item was found and deleted, False otherwise.
    Only deletes items that belong to the specified user.
    """
    result = await db.execute(
        select(ContentWhitelist).where(
            ContentWhitelist.id == whitelist_id,
            ContentWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_whitelist_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's content whitelist (non-expired only)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(
            ContentWhitelist.user_id == user_id,
            or_(
                ContentWhitelist.expires_at.is_(None),
                ContentWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


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
    # Check if already whitelisted
    result = await db.execute(
        select(FrenchOnlyWhitelist).where(
            FrenchOnlyWhitelist.user_id == user_id,
            FrenchOnlyWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Item already in french-only whitelist")

    entry = FrenchOnlyWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's french-only whitelist."""
    result = await db.execute(
        select(FrenchOnlyWhitelist)
        .where(FrenchOnlyWhitelist.user_id == user_id)
        .order_by(FrenchOnlyWhitelist.name)
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's french-only whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    result = await db.execute(
        select(FrenchOnlyWhitelist).where(
            FrenchOnlyWhitelist.id == whitelist_id,
            FrenchOnlyWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_french_only_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's french-only whitelist (non-expired only)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(FrenchOnlyWhitelist.jellyfin_id).where(
            FrenchOnlyWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                FrenchOnlyWhitelist.expires_at.is_(None),
                FrenchOnlyWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


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
    # Check if already whitelisted
    result = await db.execute(
        select(LanguageExemptWhitelist).where(
            LanguageExemptWhitelist.user_id == user_id,
            LanguageExemptWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Item already in language-exempt whitelist")

    entry = LanguageExemptWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's language-exempt whitelist."""
    result = await db.execute(
        select(LanguageExemptWhitelist)
        .where(LanguageExemptWhitelist.user_id == user_id)
        .order_by(LanguageExemptWhitelist.name)
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's language-exempt whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    result = await db.execute(
        select(LanguageExemptWhitelist).where(
            LanguageExemptWhitelist.id == whitelist_id,
            LanguageExemptWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_language_exempt_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's language-exempt whitelist (non-expired only)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(LanguageExemptWhitelist.jellyfin_id).where(
            LanguageExemptWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                LanguageExemptWhitelist.expires_at.is_(None),
                LanguageExemptWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


# ============================================================================
# Episode Language Exempt (specific episodes exempt from language checks)
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
    # Check if already whitelisted
    result = await db.execute(
        select(LargeContentWhitelist).where(
            LargeContentWhitelist.user_id == user_id,
            LargeContentWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Item already in large content whitelist")

    entry = LargeContentWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_large_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's large content whitelist."""
    result = await db.execute(
        select(LargeContentWhitelist)
        .where(LargeContentWhitelist.user_id == user_id)
        .order_by(LargeContentWhitelist.name)
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_large_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's large content whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    result = await db.execute(
        select(LargeContentWhitelist).where(
            LargeContentWhitelist.id == whitelist_id,
            LargeContentWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_large_whitelist_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's large content whitelist (non-expired only)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(LargeContentWhitelist.jellyfin_id).where(
            LargeContentWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                LargeContentWhitelist.expires_at.is_(None),
                LargeContentWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


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
    # Check if already whitelisted
    result = await db.execute(
        select(JellyseerrRequestWhitelist).where(
            JellyseerrRequestWhitelist.user_id == user_id,
            JellyseerrRequestWhitelist.jellyseerr_id == jellyseerr_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Request already in whitelist")

    entry = JellyseerrRequestWhitelist(
        user_id=user_id,
        jellyseerr_id=jellyseerr_id,
        title=title,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_request_whitelist(
    db: AsyncSession,
    user_id: int,
) -> RequestWhitelistListResponse:
    """Get all items in the user's request whitelist."""
    result = await db.execute(
        select(JellyseerrRequestWhitelist)
        .where(JellyseerrRequestWhitelist.user_id == user_id)
        .order_by(JellyseerrRequestWhitelist.title)
    )
    entries = result.scalars().all()

    items = [
        RequestWhitelistItem(
            id=entry.id,
            jellyseerr_id=entry.jellyseerr_id,
            title=entry.title,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return RequestWhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_request_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's request whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    result = await db.execute(
        select(JellyseerrRequestWhitelist).where(
            JellyseerrRequestWhitelist.id == whitelist_id,
            JellyseerrRequestWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_request_whitelist_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Get set of jellyseerr_ids in user's request whitelist (non-expired only)."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(JellyseerrRequestWhitelist.jellyseerr_id).where(
            JellyseerrRequestWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                JellyseerrRequestWhitelist.expires_at.is_(None),
                JellyseerrRequestWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())
