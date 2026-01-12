"""Database setup and models using SQLAlchemy."""

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class WhitelistContent(Base):
    """Content allowlist - protected from deletion."""

    __tablename__ = "whitelist_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhitelistFrenchOnly(Base):
    """French-only content - doesn't need English audio."""

    __tablename__ = "whitelist_french_only"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhitelistFrenchSubsOnly(Base):
    """French subs only - only requires French subtitles."""

    __tablename__ = "whitelist_french_subs_only"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhitelistLanguageExempt(Base):
    """Globally exempt from language checking."""

    __tablename__ = "whitelist_language_exempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WhitelistEpisodeExempt(Base):
    """Specific episodes exempt from language checking."""

    __tablename__ = "whitelist_episode_exempt"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    show_name: Mapped[str] = mapped_column(String(500), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    episode: Mapped[int] = mapped_column(Integer, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    """Application settings stored in database."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Database engine and session
settings = get_settings()

# Use aiosqlite for async support
DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

# Sync engine for migrations/seeding
sync_engine = create_engine(DATABASE_URL.replace("+aiosqlite", ""), echo=False)


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
