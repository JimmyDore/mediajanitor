"""Generic base class for whitelist CRUD operations.

Provides DRY implementation for the 5 whitelist types that share identical patterns:
- ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist, LargeContentWhitelist
- JellyseerrRequestWhitelist (uses jellyseerr_id/title instead of jellyfin_id/name)

EpisodeLanguageExempt is NOT included here - it has different fields (season/episode numbers).
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import (
    RequestWhitelistItem,
    RequestWhitelistListResponse,
    WhitelistItem,
    WhitelistListResponse,
)

# Use Any bounds since SQLAlchemy models don't conform to simple Protocols
T = TypeVar("T")
R = TypeVar("R")


class BaseJellyfinIdWhitelistService(Generic[T]):
    """Generic service for whitelists that use jellyfin_id as the external identifier.

    Handles: ContentWhitelist, FrenchOnlyWhitelist, LanguageExemptWhitelist, LargeContentWhitelist

    Usage:
        class ContentWhitelistService(BaseJellyfinIdWhitelistService[ContentWhitelist]):
            model = ContentWhitelist
            duplicate_error = "Content is already in whitelist"
    """

    # Subclasses must set these
    model: type[Any]  # SQLAlchemy model class
    duplicate_error: str = "Item already in whitelist"
    order_by_name: bool = True  # If False, orders by created_at desc

    async def add(
        self,
        db: AsyncSession,
        user_id: int,
        jellyfin_id: str,
        name: str,
        media_type: str,
        expires_at: datetime | None = None,
    ) -> Any:
        """Add item to whitelist. Raises ValueError if duplicate."""
        model_class = self.model

        result = await db.execute(
            select(model_class).where(
                model_class.user_id == user_id,
                model_class.jellyfin_id == jellyfin_id,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError(self.duplicate_error)

        entry = model_class(
            user_id=user_id,
            jellyfin_id=jellyfin_id,
            name=name,
            media_type=media_type,
            expires_at=expires_at,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def get_list(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> WhitelistListResponse:
        """Get all whitelist entries for user."""
        model_class = self.model

        if self.order_by_name:
            order_col = model_class.name
        else:
            order_col = model_class.created_at.desc()

        result = await db.execute(
            select(model_class).where(model_class.user_id == user_id).order_by(order_col)
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

        return WhitelistListResponse(items=items, total_count=len(items))

    async def remove(
        self,
        db: AsyncSession,
        user_id: int,
        whitelist_id: int,
    ) -> bool:
        """Remove item from whitelist. Returns True if found and deleted."""
        model_class = self.model

        result = await db.execute(
            select(model_class).where(
                model_class.id == whitelist_id,
                model_class.user_id == user_id,
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return False

        await db.delete(entry)
        return True

    async def get_ids(self, db: AsyncSession, user_id: int) -> set[str]:
        """Get set of jellyfin_ids for non-expired entries."""
        model_class = self.model
        now = datetime.now(UTC)

        result = await db.execute(
            select(model_class.jellyfin_id).where(
                model_class.user_id == user_id,
                or_(
                    model_class.expires_at.is_(None),
                    model_class.expires_at > now,
                ),
            )
        )
        return set(result.scalars().all())


class BaseJellyseerrIdWhitelistService(Generic[R]):
    """Generic service for whitelists that use jellyseerr_id as the external identifier.

    Handles: JellyseerrRequestWhitelist

    Usage:
        class RequestWhitelistService(BaseJellyseerrIdWhitelistService[JellyseerrRequestWhitelist]):
            model = JellyseerrRequestWhitelist
            duplicate_error = "Request already in whitelist"
    """

    model: type[Any]  # SQLAlchemy model class
    duplicate_error: str = "Request already in whitelist"

    async def add(
        self,
        db: AsyncSession,
        user_id: int,
        jellyseerr_id: int,
        title: str,
        media_type: str,
        expires_at: datetime | None = None,
    ) -> Any:
        """Add request to whitelist. Raises ValueError if duplicate."""
        model_class = self.model

        result = await db.execute(
            select(model_class).where(
                model_class.user_id == user_id,
                model_class.jellyseerr_id == jellyseerr_id,
            )
        )
        if result.scalar_one_or_none():
            raise ValueError(self.duplicate_error)

        entry = model_class(
            user_id=user_id,
            jellyseerr_id=jellyseerr_id,
            title=title,
            media_type=media_type,
            expires_at=expires_at,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def get_list(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> RequestWhitelistListResponse:
        """Get all whitelist entries for user."""
        model_class = self.model

        result = await db.execute(
            select(model_class).where(model_class.user_id == user_id).order_by(model_class.title)
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

        return RequestWhitelistListResponse(items=items, total_count=len(items))

    async def remove(
        self,
        db: AsyncSession,
        user_id: int,
        whitelist_id: int,
    ) -> bool:
        """Remove item from whitelist. Returns True if found and deleted."""
        model_class = self.model

        result = await db.execute(
            select(model_class).where(
                model_class.id == whitelist_id,
                model_class.user_id == user_id,
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            return False

        await db.delete(entry)
        return True

    async def get_ids(self, db: AsyncSession, user_id: int) -> set[int]:
        """Get set of jellyseerr_ids for non-expired entries."""
        model_class = self.model
        now = datetime.now(UTC)

        result = await db.execute(
            select(model_class.jellyseerr_id).where(
                model_class.user_id == user_id,
                or_(
                    model_class.expires_at.is_(None),
                    model_class.expires_at > now,
                ),
            )
        )
        return set(result.scalars().all())
