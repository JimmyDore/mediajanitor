"""Database setup and models using SQLAlchemy."""

from datetime import datetime
from typing import Any, AsyncGenerator

from sqlalchemy import Boolean, String, Integer, BigInteger, DateTime, Text, ForeignKey, create_engine, JSON, UniqueConstraint, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserSettings(Base):
    """Per-user settings for external service connections."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    # Jellyfin settings (API key is encrypted)
    jellyfin_server_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jellyfin_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Jellyseerr settings (API key is encrypted)
    jellyseerr_server_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jellyseerr_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Analysis preferences (thresholds)
    old_content_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    large_movie_size_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    large_season_size_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Display preferences
    show_unreleased_requests: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_preference: Mapped[str] = mapped_column(String(10), default="system")  # light, dark, system
    recently_available_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Default: 7
    # Radarr settings (API key is encrypted)
    radarr_server_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    radarr_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sonarr settings (API key is encrypted)
    sonarr_server_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sonarr_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CachedMediaItem(Base):
    """Cached media item from Jellyfin (movies and series)."""

    __tablename__ = "cached_media_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyfin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Movie" or "Series"
    production_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_created: Mapped[str | None] = mapped_column(String(50), nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    played: Mapped[bool] = mapped_column(Boolean, default=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_played_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    largest_season_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # For series only
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CachedJellyseerrRequest(Base):
    """Cached request from Jellyseerr."""

    __tablename__ = "cached_jellyseerr_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyseerr_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    jellyseerr_media_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # media.id for deletion
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "movie" or "tv"
    status: Mapped[int] = mapped_column(Integer, nullable=False)  # Jellyseerr status code
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Movie releaseDate or TV firstAirDate
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContentWhitelist(Base):
    """User's whitelist to protect content from deletion suggestions."""

    __tablename__ = "content_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyfin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Movie" or "Series"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # NULL = permanent


class FrenchOnlyWhitelist(Base):
    """User's whitelist for content that only needs French audio (no English required)."""

    __tablename__ = "french_only_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyfin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Movie" or "Series"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # NULL = permanent


class LanguageExemptWhitelist(Base):
    """User's whitelist for content exempt from all language checks."""

    __tablename__ = "language_exempt_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyfin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Movie" or "Series"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # NULL = permanent


class JellyseerrRequestWhitelist(Base):
    """User's whitelist to hide Jellyseerr requests from unavailable list."""

    __tablename__ = "jellyseerr_request_whitelist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyseerr_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "movie" or "tv"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # NULL = permanent


class SyncStatus(Base):
    """Track sync status per user."""

    __tablename__ = "sync_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    last_sync_started: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_completed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "success", "failed"
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_items_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requests_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Progress tracking (for UI feedback during sync)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "fetching_users", "syncing_media"
    total_steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_step_progress: Mapped[int | None] = mapped_column(Integer, nullable=True)  # e.g., user 3 of 10
    current_step_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RefreshToken(Base):
    """Refresh token for session management."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserNickname(Base):
    """User nickname mapping for Jellyseerr usernames."""

    __tablename__ = "user_nicknames"
    __table_args__ = (
        # Unique constraint: each jellyseerr_username maps once per user
        UniqueConstraint("user_id", "jellyseerr_username", name="uq_user_nickname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    jellyseerr_username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# Database engine and session
settings = get_settings()

# Use aiosqlite for async support
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Configure SQLite for better concurrency
connect_args = {}
if ASYNC_DATABASE_URL.startswith("sqlite"):
    # Enable WAL mode for concurrent read/write access
    # Set timeout to 30 seconds for lock acquisition
    connect_args = {
        "check_same_thread": False,
        "timeout": 30.0,
    }

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Max number of connections in pool
    max_overflow=20,  # Allow up to 20 additional connections beyond pool_size
)

async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine for migrations/seeding
sync_engine = create_engine(DATABASE_URL.replace("+aiosqlite", ""), echo=False)


async def init_db_settings() -> None:
    """Initialize database settings (e.g., WAL mode for SQLite)."""
    if ASYNC_DATABASE_URL.startswith("sqlite"):
        async with async_engine.begin() as conn:
            # Enable WAL mode for better concurrency
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            # Set busy timeout to 30 seconds
            await conn.execute(text("PRAGMA busy_timeout=30000;"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync() -> None:
    """Initialize database tables synchronously (for scripts)."""
    Base.metadata.create_all(sync_engine)
