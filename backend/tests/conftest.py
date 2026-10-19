"""Pytest configuration and fixtures.

IMPORTANT: This file uses ASYNC sessions to match production behavior.
Using sync sessions here would mask async/await bugs that only appear
in production Docker. See CLAUDE.md "Async/Sync Consistency" section.
"""

import os
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient

# Set TESTING environment variable to adjust cookie settings
os.environ["TESTING"] = "1"
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# CRITICAL: Use async SQLite (aiosqlite) to match production's AsyncSession.
# Using sync sqlite:///:memory: will cause tests to pass but production to fail.
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingAsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db dependency for testing with async session."""
    async with TestingAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(scope="session", autouse=True)
async def dispose_engine() -> AsyncGenerator[None, None]:
    """Dispose the async engine after all tests to prevent hanging."""
    yield
    await async_engine.dispose()


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create fresh database tables for each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Each test runs in its own event loop: its connection must not outlive it,
    # or the next test waits on locks bound to this loop.
    await async_engine.dispose()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_jellyfin_response() -> dict:
    """Sample Jellyfin API response for testing."""
    return {
        "Items": [
            {
                "Id": "test-movie-1",
                "Name": "Test Movie",
                "Type": "Movie",
                "ProductionYear": 2023,
                "DateCreated": "2023-01-15T10:00:00Z",
                "Path": "/media/movies/Test Movie (2023)/movie.mkv",
                "UserData": {
                    "Played": True,
                    "LastPlayedDate": "2023-06-15T10:00:00Z",
                    "PlayCount": 1,
                },
                "MediaSources": [
                    {
                        "Size": 5000000000,  # 5GB
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "eng"},
                            {"Type": "Audio", "Language": "fre"},
                            {"Type": "Subtitle", "Language": "fre"},
                        ],
                    }
                ],
            },
            {
                "Id": "test-series-1",
                "Name": "Test Series",
                "Type": "Series",
                "ProductionYear": 2022,
                "DateCreated": "2022-06-01T10:00:00Z",
                "Path": "/media/tv/Test Series",
                "UserData": {
                    "Played": False,
                    "PlayCount": 0,
                },
            },
        ],
        "TotalRecordCount": 2,
    }


@pytest.fixture
def mock_jellyseerr_response() -> dict:
    """Sample Jellyseerr API response for testing."""
    return {
        "pageInfo": {"pages": 1, "results": 2},
        "results": [
            {
                "id": 1,
                "status": 2,  # Approved
                "createdAt": "2024-01-01T10:00:00Z",
                "media": {
                    "tmdbId": 12345,
                    "mediaType": "movie",
                    "status": 5,  # Available
                },
                "requestedBy": {"displayName": "TestUser"},
            },
            {
                "id": 2,
                "status": 1,  # Pending
                "createdAt": "2024-01-02T10:00:00Z",
                "media": {
                    "tmdbId": 67890,
                    "mediaType": "tv",
                    "status": 4,  # Partially Available
                    "seasons": [
                        {"seasonNumber": 1, "status": 5},
                        {"seasonNumber": 2, "status": 2},
                    ],
                },
                "requestedBy": {"displayName": "AnotherUser"},
            },
        ],
    }


# Hub App alerts (app.services.app_alerts): made-up settings for the reporting account.
HUB = "https://hub.example.test"
HUB_ALERTS_URL = f"{HUB}/api/app-alerts/mediajanitor"
HUB_PING_URL = f"{HUB}/api/ping/mediajanitor-sync"
HUB_APP_ALERT_TOKEN = "mj-test-token"
HUB_PING_TOKEN = "hub-ping-test-token"
HUB_USER_EMAIL = "me@example.com"
HUB_FRONTEND = "https://mj.example.test"


@pytest.fixture
def hub_configured(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Every Hub setting set, reporting for HUB_USER_EMAIL; Slack sync failures off."""
    from app.config import get_settings

    monkeypatch.setenv("HUB_BASE_URL", HUB)
    monkeypatch.setenv("HUB_APP_ALERT_TOKEN", HUB_APP_ALERT_TOKEN)
    monkeypatch.setenv("HUB_PING_TOKEN", HUB_PING_TOKEN)
    monkeypatch.setenv("HUB_ALERT_USER_EMAIL", HUB_USER_EMAIL)
    monkeypatch.setenv("FRONTEND_URL", HUB_FRONTEND)
    monkeypatch.setenv("SLACK_WEBHOOK_SYNC_FAILURES", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
