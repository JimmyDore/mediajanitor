"""Service functions for user nickname mappings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserNickname
from app.models.settings import NicknameItem, NicknameListResponse


async def create_nickname(
    db: AsyncSession,
    user_id: int,
    jellyseerr_username: str,
    display_name: str,
) -> UserNickname:
    """Create a new nickname mapping.

    Args:
        db: Database session
        user_id: User ID
        jellyseerr_username: The Jellyseerr username to map
        display_name: The friendly display name

    Raises:
        ValueError: If the username already has a mapping for this user
    """
    # Check for duplicate
    result = await db.execute(
        select(UserNickname).where(
            UserNickname.user_id == user_id,
            UserNickname.jellyseerr_username == jellyseerr_username,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Nickname mapping for '{jellyseerr_username}' already exists")

    # Create new mapping
    entry = UserNickname(
        user_id=user_id,
        jellyseerr_username=jellyseerr_username,
        display_name=display_name,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_nicknames(
    db: AsyncSession,
    user_id: int,
) -> NicknameListResponse:
    """Get all nickname mappings for a user."""
    result = await db.execute(
        select(UserNickname)
        .where(UserNickname.user_id == user_id)
        .order_by(UserNickname.jellyseerr_username)
    )
    entries = result.scalars().all()

    items = [
        NicknameItem(
            id=entry.id,
            jellyseerr_username=entry.jellyseerr_username,
            display_name=entry.display_name,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in entries
    ]

    return NicknameListResponse(
        items=items,
        total_count=len(items),
    )


async def update_nickname(
    db: AsyncSession,
    user_id: int,
    nickname_id: int,
    display_name: str,
) -> bool:
    """Update a nickname mapping's display name.

    Returns True if found and updated, False otherwise.
    Only updates items that belong to the specified user.
    """
    result = await db.execute(
        select(UserNickname).where(
            UserNickname.id == nickname_id,
            UserNickname.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    entry.display_name = display_name
    await db.flush()
    return True


async def delete_nickname(
    db: AsyncSession,
    user_id: int,
    nickname_id: int,
) -> bool:
    """Delete a nickname mapping.

    Returns True if found and deleted, False otherwise.
    Only deletes items that belong to the specified user.
    """
    result = await db.execute(
        select(UserNickname).where(
            UserNickname.id == nickname_id,
            UserNickname.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True
