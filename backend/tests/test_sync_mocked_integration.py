"""
Integration tests for sync with mocked Jellyfin/Jellyseerr APIs (US-27.2).

These tests verify sync behavior with realistic mocked API responses,
running without network access (fully offline), and what a sync reports to
the Hub at its end (App alerts, nightly ping).
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import respx
from httpx import Response
from sqlalchemy import select

from app.database import (
    CachedJellyseerrRequest,
    CachedMediaItem,
    ContentWhitelist,
    SyncStatus,
    User,
    UserSettings,
)
from app.services.encryption import encrypt_value
from app.services.sync import (
    run_user_sync,
)
from tests.conftest import (
    HUB_ALERTS_URL,
    HUB_APP_ALERT_TOKEN,
    HUB_FRONTEND,
    HUB_PING_TOKEN,
    HUB_PING_URL,
    HUB_USER_EMAIL,
    TestingAsyncSessionLocal,
)

# Realistic Jellyfin API responses based on actual API documentation
JELLYFIN_USERS_RESPONSE = [
    {"Id": "user-1", "Name": "Admin"},
    {"Id": "user-2", "Name": "Jane"},
]

JELLYFIN_ITEMS_USER1_RESPONSE = {
    "Items": [
        {
            "Id": "movie-123",
            "Name": "The Matrix",
            "Type": "Movie",
            "ProductionYear": 1999,
            "DateCreated": "2023-01-15T10:00:00Z",
            "Path": "/media/movies/The Matrix (1999)/movie.mkv",
            "UserData": {
                "Played": True,
                "LastPlayedDate": "2023-06-15T10:00:00Z",
                "PlayCount": 2,
            },
            "MediaSources": [
                {
                    "Size": 15000000000,  # 15GB
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "eng"},
                        {"Type": "Audio", "Language": "fre"},
                        {"Type": "Subtitle", "Language": "fre"},
                    ],
                }
            ],
            "ProviderIds": {"Tmdb": "603"},
        },
        {
            "Id": "series-456",
            "Name": "Breaking Bad",
            "Type": "Series",
            "ProductionYear": 2008,
            "DateCreated": "2022-06-01T10:00:00Z",
            "Path": "/media/tv/Breaking Bad",
            "UserData": {
                "Played": False,
                "PlayCount": 0,
            },
            "ProviderIds": {"Tmdb": "1396"},
        },
    ],
    "TotalRecordCount": 2,
}

# User 2 has watched Breaking Bad
JELLYFIN_ITEMS_USER2_RESPONSE = {
    "Items": [
        {
            "Id": "movie-123",
            "Name": "The Matrix",
            "Type": "Movie",
            "ProductionYear": 1999,
            "DateCreated": "2023-01-15T10:00:00Z",
            "Path": "/media/movies/The Matrix (1999)/movie.mkv",
            "UserData": {
                "Played": False,
                "PlayCount": 0,
            },
            "MediaSources": [{"Size": 15000000000}],
            "ProviderIds": {"Tmdb": "603"},
        },
        {
            "Id": "series-456",
            "Name": "Breaking Bad",
            "Type": "Series",
            "ProductionYear": 2008,
            "DateCreated": "2022-06-01T10:00:00Z",
            "Path": "/media/tv/Breaking Bad",
            "UserData": {
                "Played": True,
                "LastPlayedDate": "2024-01-01T10:00:00Z",
                "PlayCount": 5,
            },
            "ProviderIds": {"Tmdb": "1396"},
        },
    ],
    "TotalRecordCount": 2,
}

# Realistic Jellyseerr API response
JELLYSEERR_REQUESTS_RESPONSE = {
    "pageInfo": {"pages": 1, "results": 3},
    "results": [
        {
            "id": 1,
            "status": 2,  # Approved
            "createdAt": "2024-01-01T10:00:00Z",
            "media": {
                "id": 100,
                "tmdbId": 12345,
                "mediaType": "movie",
                "status": 5,  # Available
            },
            "requestedBy": {"displayName": "Admin"},
        },
        {
            "id": 2,
            "status": 1,  # Pending
            "createdAt": "2024-01-02T10:00:00Z",
            "media": {
                "id": 101,
                "tmdbId": 67890,
                "mediaType": "tv",
                "status": 4,  # Partially Available
            },
            "requestedBy": {"displayName": "Jane"},
        },
        {
            "id": 3,
            "status": 2,  # Approved
            "createdAt": "2024-01-03T10:00:00Z",
            "media": {
                "id": 102,
                "tmdbId": 11111,
                "mediaType": "movie",
                "status": 3,  # Processing
            },
            "requestedBy": {"displayName": "Admin"},
        },
    ],
}

# Media detail response for title enrichment
JELLYSEERR_MOVIE_DETAIL = {
    "id": 12345,
    "title": "Dune: Part Two",
    "originalTitle": "Dune: Part Two",
    "releaseDate": "2024-03-01",
}

JELLYSEERR_TV_DETAIL = {
    "id": 67890,
    "name": "The Last of Us",
    "originalName": "The Last of Us",
    "firstAirDate": "2023-01-15",
}

JELLYSEERR_MOVIE_DETAIL_2 = {
    "id": 11111,
    "title": "Oppenheimer",
    "originalTitle": "Oppenheimer",
    "releaseDate": "2023-07-21",
}

# Library refresh mock responses (US-64.5)
JELLYFIN_SCHEDULED_TASKS_IDLE = [
    {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
    {"Key": "CleanLibrary", "Name": "Clean Library", "State": "Idle"},
]

JELLYSEERR_SYNC_COMPLETE = {
    "running": False,
    "progress": 100,
    "total": 100,
}

JELLYSEERR_SYNC_STARTED = {
    "running": True,
    "progress": 0,
    "total": 100,
}


def mock_library_refresh_endpoints(
    jellyfin_base: str = "http://jellyfin.local",
    jellyseerr_base: str | None = None,
) -> None:
    """Add mock responses for library refresh endpoints (US-64.5).

    Call this at the start of any @respx.mock test that calls run_user_sync().
    """
    # Jellyfin library refresh - returns 204
    respx.post(f"{jellyfin_base}/Library/Refresh").mock(return_value=Response(204))
    # Jellyfin scheduled tasks - returns Idle state immediately (no polling needed)
    respx.get(f"{jellyfin_base}/ScheduledTasks").mock(
        return_value=Response(200, json=JELLYFIN_SCHEDULED_TASKS_IDLE)
    )

    # Jellyseerr library sync (if configured)
    if jellyseerr_base:
        # POST to trigger sync returns running: true
        respx.post(f"{jellyseerr_base}/api/v1/settings/jellyfin/sync").mock(
            return_value=Response(200, json=JELLYSEERR_SYNC_STARTED)
        )
        # GET to check status returns running: false (complete)
        respx.get(f"{jellyseerr_base}/api/v1/settings/jellyfin/sync").mock(
            return_value=Response(200, json=JELLYSEERR_SYNC_COMPLETE)
        )


class TestSuccessfulSyncStoresData:
    """Test: successful sync stores correct data in database."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_jellyfin_sync_stores_media_items(self) -> None:
        """Sync should store Jellyfin media items correctly in database."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        # Mock Jellyfin API
        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        # Mock season size calculation endpoints (return empty for simplicity)
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        async with TestingAsyncSessionLocal() as session:
            # Create user with Jellyfin settings
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            # Run sync
            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 2

            # Verify items stored correctly
            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = items_result.scalars().all()

            assert len(items) == 2

            # Find movie and series
            movie = next((i for i in items if i.media_type == "Movie"), None)
            series = next((i for i in items if i.media_type == "Series"), None)

            assert movie is not None
            assert movie.name == "The Matrix"
            assert movie.jellyfin_id == "movie-123"
            assert movie.production_year == 1999
            assert movie.size_bytes == 15000000000
            assert movie.played is True  # User 1 watched it
            assert movie.play_count == 2

            assert series is not None
            assert series.name == "Breaking Bad"
            assert series.jellyfin_id == "series-456"
            assert series.production_year == 2008
            # Aggregated: User 2 watched it
            assert series.played is True
            assert series.play_count == 5

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_full_sync_with_jellyseerr(self) -> None:
        """Full sync stores both Jellyfin and Jellyseerr data."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(
            jellyfin_base="http://jellyfin.local",
            jellyseerr_base="http://jellyseerr.local",
        )

        # Mock Jellyfin API
        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        # Mock Jellyseerr API
        respx.get("http://jellyseerr.local/api/v1/user").mock(
            return_value=Response(
                200,
                json={
                    "results": [{"id": 1, "displayName": "Admin"}, {"id": 2, "displayName": "Jane"}]
                },
            )
        )
        respx.get("http://jellyseerr.local/api/v1/request").mock(
            return_value=Response(200, json=JELLYSEERR_REQUESTS_RESPONSE)
        )
        respx.get("http://jellyseerr.local/api/v1/movie/12345").mock(
            return_value=Response(200, json=JELLYSEERR_MOVIE_DETAIL)
        )
        respx.get("http://jellyseerr.local/api/v1/tv/67890").mock(
            return_value=Response(200, json=JELLYSEERR_TV_DETAIL)
        )
        respx.get("http://jellyseerr.local/api/v1/movie/11111").mock(
            return_value=Response(200, json=JELLYSEERR_MOVIE_DETAIL_2)
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted=encrypt_value("jellyseerr-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 2
            assert result["requests_synced"] == 3

            # Verify Jellyseerr requests stored
            requests_result = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user.id)
            )
            requests = requests_result.scalars().all()

            assert len(requests) == 3

            # Check request data
            dune_request = next((r for r in requests if r.tmdb_id == 12345), None)
            assert dune_request is not None
            assert dune_request.title == "Dune: Part Two"
            assert dune_request.media_type == "movie"
            assert dune_request.requested_by == "Admin"

            last_of_us = next((r for r in requests if r.tmdb_id == 67890), None)
            assert last_of_us is not None
            assert last_of_us.title == "The Last of Us"
            assert last_of_us.media_type == "tv"

    @pytest.mark.asyncio
    @respx.mock
    async def test_sync_updates_sync_status(self) -> None:
        """Sync should update SyncStatus record in database."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            await run_user_sync(session, user.id)

            # Verify sync status updated
            status_result = await session.execute(
                select(SyncStatus).where(SyncStatus.user_id == user.id)
            )
            status = status_result.scalar_one_or_none()

            assert status is not None
            assert status.last_sync_status == "success"
            assert status.last_sync_completed is not None
            assert status.media_items_count == 2


class TestPartialJellyfinData:
    """Test: partial Jellyfin data is handled correctly (missing fields)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_missing_optional_fields(self) -> None:
        """Sync should handle items with missing optional fields."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        # Response with minimal data - missing many optional fields
        minimal_items = {
            "Items": [
                {
                    "Id": "movie-minimal",
                    "Name": "Minimal Movie",
                    "Type": "Movie",
                    # Missing: ProductionYear, DateCreated, Path, MediaSources, ProviderIds
                    "UserData": {},
                },
            ],
            "TotalRecordCount": 1,
        }

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=[{"Id": "user-1", "Name": "Admin"}])
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=minimal_items)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 1

            # Verify item stored with null values for missing fields
            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            item = items_result.scalar_one()

            assert item.name == "Minimal Movie"
            assert item.production_year is None
            assert item.date_created is None
            assert item.path is None
            assert item.size_bytes is None
            assert item.played is False
            assert item.play_count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_empty_media_sources(self) -> None:
        """Sync should handle empty MediaSources array."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        items_empty_sources = {
            "Items": [
                {
                    "Id": "movie-no-size",
                    "Name": "Movie Without Size",
                    "Type": "Movie",
                    "ProductionYear": 2023,
                    "MediaSources": [],  # Empty array
                    "UserData": {"Played": True, "PlayCount": 1},
                },
            ],
            "TotalRecordCount": 1,
        }

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=[{"Id": "user-1", "Name": "Admin"}])
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=items_empty_sources)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"

            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            item = items_result.scalar_one()

            assert item.size_bytes is None
            assert item.played is True


class TestJellyseerrDownDoesntBreakSync:
    """Test: Jellyseerr down doesn't break Jellyfin sync."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_jellyseerr_500_error_allows_jellyfin_sync(self) -> None:
        """Jellyfin data syncs even if Jellyseerr returns 500."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(
            jellyfin_base="http://jellyfin.local",
            jellyseerr_base="http://jellyseerr.local",
        )

        # Jellyfin works
        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        # Jellyseerr users mock (needed for nickname prefill)
        respx.get("http://jellyseerr.local/api/v1/user").mock(
            return_value=Response(200, json={"results": []})
        )
        # Jellyseerr returns 500 (simulating server error)
        respx.get("http://jellyseerr.local/api/v1/request").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted=encrypt_value("jellyseerr-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            # Sync should be partial (Jellyseerr failed, Jellyfin succeeded)
            assert result["status"] == "partial"
            assert result["media_items_synced"] == 2
            assert result["requests_synced"] == 0
            assert "Jellyseerr" in result["error"]

            # Jellyfin items should still be stored
            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = items_result.scalars().all()
            assert len(items) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_jellyseerr_connection_error_allows_jellyfin_sync(self) -> None:
        """Jellyfin data syncs even if Jellyseerr is unreachable."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(
            jellyfin_base="http://jellyfin.local",
            jellyseerr_base="http://jellyseerr.local",
        )

        # Jellyfin works
        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        # Jellyseerr users mock (needed for nickname prefill)
        respx.get("http://jellyseerr.local/api/v1/user").mock(
            return_value=Response(200, json={"results": []})
        )
        # Jellyseerr is not mocked - will timeout/fail
        # Using side_effect to simulate connection error
        import httpx

        respx.get("http://jellyseerr.local/api/v1/request").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted=encrypt_value("jellyseerr-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "partial"
            assert result["media_items_synced"] == 2


class TestEmptyResultsCreateEmptyCache:
    """Test: API returning empty results creates empty cache (not error)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_jellyfin_library_syncs_successfully(self) -> None:
        """Empty Jellyfin library should not cause error."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=[{"Id": "user-1", "Name": "Admin"}])
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json={"Items": [], "TotalRecordCount": 0})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 0

            # Verify no items in database
            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = items_result.scalars().all()
            assert len(items) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_empty_jellyseerr_requests_syncs_successfully(self) -> None:
        """Empty Jellyseerr requests should not cause error."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(
            jellyfin_base="http://jellyfin.local",
            jellyseerr_base="http://jellyseerr.local",
        )

        # Jellyfin has data
        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=JELLYFIN_USERS_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER1_RESPONSE)
        )
        respx.get("http://jellyfin.local/Users/user-2/Items").mock(
            return_value=Response(200, json=JELLYFIN_ITEMS_USER2_RESPONSE)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        # Jellyseerr users mock (needed for nickname prefill)
        respx.get("http://jellyseerr.local/api/v1/user").mock(
            return_value=Response(200, json={"results": []})
        )
        # Jellyseerr returns empty results
        respx.get("http://jellyseerr.local/api/v1/request").mock(
            return_value=Response(200, json={"pageInfo": {"pages": 0, "results": 0}, "results": []})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted=encrypt_value("jellyseerr-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 2
            assert result["requests_synced"] == 0

            # Verify no requests in database
            requests_result = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user.id)
            )
            requests = requests_result.scalars().all()
            assert len(requests) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_jellyfin_users_syncs_empty(self) -> None:
        """No Jellyfin users should result in empty media cache."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=[])  # No users
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 0


class TestRealisticApiStructures:
    """Test with realistic API response structures from documentation."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_handles_real_jellyfin_response_structure(self) -> None:
        """Sync handles realistic Jellyfin API response format."""
        # Mock library refresh endpoints (US-64.5)
        mock_library_refresh_endpoints(jellyfin_base="http://jellyfin.local")

        # Very detailed response matching real Jellyfin API
        detailed_response = {
            "Items": [
                {
                    "Id": "abc123def456",
                    "Name": "Inception",
                    "Type": "Movie",
                    "OriginalTitle": "Inception",
                    "ServerId": "server123",
                    "Container": "mkv",
                    "IsFolder": False,
                    "ProductionYear": 2010,
                    "DateCreated": "2023-05-20T14:30:00.0000000Z",
                    "PremiereDate": "2010-07-16T00:00:00.0000000Z",
                    "CriticRating": 86,
                    "OfficialRating": "PG-13",
                    "Overview": "A thief who steals corporate secrets...",
                    "Taglines": ["Your mind is the scene of the crime"],
                    "Genres": ["Action", "Science Fiction", "Thriller"],
                    "CommunityRating": 8.3,
                    "RunTimeTicks": 88800000000,
                    "PlayAccess": "Full",
                    "AspectRatio": "2.39:1",
                    "ProductionLocations": ["United States"],
                    "Path": "/media/movies/Inception (2010)/Inception.2010.mkv",
                    "SortName": "inception",
                    "Studios": [{"Name": "Warner Bros. Pictures"}],
                    "GenreItems": [
                        {"Name": "Action", "Id": 1},
                        {"Name": "Science Fiction", "Id": 2},
                    ],
                    "Tags": [],
                    "PrimaryImageAspectRatio": 0.6666666666666666,
                    "SeriesStudio": None,
                    "ParentId": "movies-folder",
                    "People": [
                        {
                            "Name": "Christopher Nolan",
                            "Id": "director1",
                            "Role": "Director",
                            "Type": "Director",
                        }
                    ],
                    "UserData": {
                        "PlaybackPositionTicks": 0,
                        "PlayCount": 3,
                        "IsFavorite": True,
                        "Played": True,
                        "Key": "user-data-key",
                        "LastPlayedDate": "2024-01-10T20:00:00.0000000Z",
                    },
                    "ProviderIds": {
                        "Tmdb": "27205",
                        "Imdb": "tt1375666",
                        "TmdbCollection": "264",
                    },
                    "ImageTags": {"Primary": "abc123", "Logo": "def456"},
                    "MediaSources": [
                        {
                            "Protocol": "File",
                            "Id": "abc123def456",
                            "Path": "/media/movies/Inception (2010)/Inception.2010.mkv",
                            "Type": "Default",
                            "Container": "mkv",
                            "Size": 12500000000,
                            "Name": "Inception.2010.mkv",
                            "IsRemote": False,
                            "SupportsTranscoding": True,
                            "SupportsDirectStream": True,
                            "SupportsDirectPlay": True,
                            "Bitrate": 11305600,
                            "VideoType": "VideoFile",
                            "MediaStreams": [
                                {
                                    "Codec": "h264",
                                    "Language": "eng",
                                    "Type": "Video",
                                    "Width": 1920,
                                    "Height": 800,
                                },
                                {
                                    "Codec": "dts",
                                    "Language": "eng",
                                    "Type": "Audio",
                                    "Channels": 6,
                                },
                                {
                                    "Codec": "dts",
                                    "Language": "fra",
                                    "Type": "Audio",
                                    "Channels": 6,
                                },
                            ],
                        }
                    ],
                    "MediaType": "Video",
                    "LockedFields": [],
                    "LockData": False,
                    "Width": 1920,
                    "Height": 800,
                },
            ],
            "TotalRecordCount": 1,
            "StartIndex": 0,
        }

        respx.get("http://jellyfin.local/Users").mock(
            return_value=Response(200, json=[{"Id": "user-1", "Name": "Admin"}])
        )
        respx.get("http://jellyfin.local/Users/user-1/Items").mock(
            return_value=Response(200, json=detailed_response)
        )
        respx.get("http://jellyfin.local/Items").mock(
            return_value=Response(200, json={"Items": []})
        )

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=encrypt_value("test-api-key"),
            )
            session.add(settings)
            await session.commit()

            result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 1

            items_result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            item = items_result.scalar_one()

            assert item.name == "Inception"
            assert item.production_year == 2010
            assert item.size_bytes == 12500000000
            assert item.played is True
            assert item.play_count == 3
            assert item.last_played_date == "2024-01-10T20:00:00.0000000Z"


# --- Hub App alerts and the nightly ping, sent at the end of run_user_sync ---------------
#
# Drives run_user_sync end to end with respx mocking Jellyfin, Jellyseerr and the Hub,
# and checks only what is sent to the Hub (app.services.app_alerts).

HUB_JELLYFIN = "http://jellyfin.local"
HUB_JELLYSEERR = "http://jellyseerr.local"

GIB = 1024 * 1024 * 1024
BOTH_AUDIO = [
    {"Type": "Audio", "Language": "eng"},
    {"Type": "Audio", "Language": "fre"},
]
ENGLISH_ONLY = [{"Type": "Audio", "Language": "eng"}]
FRENCH_ONLY = [{"Type": "Audio", "Language": "fre"}]


def _movie(
    jellyfin_id: str,
    name: str,
    size_bytes: int,
    streams: list[dict[str, str]],
    last_played: str | None = None,
) -> dict[str, Any]:
    user_data: dict[str, Any] = {"Played": False, "PlayCount": 0}
    if last_played:
        user_data = {"Played": True, "PlayCount": 1, "LastPlayedDate": last_played}
    return {
        "Id": jellyfin_id,
        "Name": name,
        "Type": "Movie",
        "ProductionYear": 2000,
        "DateCreated": "2023-01-15T10:00:00Z",
        "Path": f"/media/movies/{name}/movie.mkv",
        "UserData": user_data,
        "MediaSources": [{"Size": size_bytes, "MediaStreams": streams}],
    }


def _recently() -> str:
    return (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")


def hub_library() -> list[dict[str, Any]]:
    """A library with 5 old, 1 large, 2 language-issue items and 1 clean one.

    Old (largest first): Dune 20, Heat 4, Alien 3, Arrival 2, Brazil 0.5 GiB = 29.5 GiB
    Large: Dune 20 GiB
    Language: Arrival 2 (EN only), Amelie 1 (FR only) = 3 GiB
    """
    return [
        _movie("dune", "Dune", 20 * GIB, BOTH_AUDIO, last_played="2023-06-15T10:00:00Z"),
        _movie("heat", "Heat", 4 * GIB, BOTH_AUDIO),
        _movie("alien", "Alien", 3 * GIB, BOTH_AUDIO),
        _movie("arrival", "Arrival", 2 * GIB, ENGLISH_ONLY),
        _movie("brazil", "Brazil", GIB // 2, BOTH_AUDIO),
        _movie("amelie", "Amelie", 1 * GIB, FRENCH_ONLY, last_played=_recently()),
        _movie("fresh", "Fresh", 1 * GIB, BOTH_AUDIO, last_played=_recently()),
    ]


CLEAN_LIBRARY = [
    _movie("fresh", "Fresh", 1 * GIB, BOTH_AUDIO, last_played=_recently()),
]


def mock_hub_jellyfin(items: list[dict[str, Any]]) -> None:
    mock_library_refresh_endpoints(jellyfin_base=HUB_JELLYFIN)
    respx.get(f"{HUB_JELLYFIN}/Users").mock(
        return_value=Response(200, json=[{"Id": "jf-user", "Name": "Admin"}])
    )
    respx.get(f"{HUB_JELLYFIN}/Users/jf-user/Items").mock(
        return_value=Response(200, json={"Items": items, "TotalRecordCount": len(items)})
    )
    respx.get(f"{HUB_JELLYFIN}/Items").mock(return_value=Response(200, json={"Items": []}))


def _request(request_id: int, tmdb_id: int, media_status: int) -> dict[str, Any]:
    return {
        "id": request_id,
        "status": 2,  # Approved
        "createdAt": f"2024-01-0{request_id}T10:00:00Z",
        "media": {
            "id": request_id,
            "tmdbId": tmdb_id,
            "mediaType": "movie",
            "status": media_status,
        },
        "requestedBy": {"displayName": "Admin"},
    }


# Unavailable: Solaris, Stalker, Ran, Ikiru (newest first). Available: Amadeus.
HUB_REQUESTS = [
    (1, 101, "Ikiru", 2),
    (2, 102, "Ran", 2),
    (3, 103, "Stalker", 2),
    (4, 104, "Solaris", 2),
    (5, 105, "Amadeus", 5),
]


def mock_hub_jellyseerr() -> None:
    mock_library_refresh_endpoints(jellyfin_base=HUB_JELLYFIN, jellyseerr_base=HUB_JELLYSEERR)
    respx.get(f"{HUB_JELLYSEERR}/api/v1/user").mock(
        return_value=Response(200, json={"results": []})
    )
    respx.get(f"{HUB_JELLYSEERR}/api/v1/request").mock(
        return_value=Response(
            200,
            json={
                "pageInfo": {"pages": 1, "results": len(HUB_REQUESTS)},
                "results": [_request(rid, tmdb, status) for rid, tmdb, _, status in HUB_REQUESTS],
            },
        )
    )
    for _, tmdb_id, title, _ in HUB_REQUESTS:
        respx.get(f"{HUB_JELLYSEERR}/api/v1/movie/{tmdb_id}").mock(
            return_value=Response(
                200, json={"id": tmdb_id, "title": title, "releaseDate": "2020-01-01"}
            )
        )


def mock_hub_jellyseerr_401() -> None:
    """Jellyseerr refuses the requests: the sync ends partial."""
    mock_library_refresh_endpoints(jellyfin_base=HUB_JELLYFIN, jellyseerr_base=HUB_JELLYSEERR)
    respx.get(f"{HUB_JELLYSEERR}/api/v1/user").mock(
        return_value=Response(200, json={"results": []})
    )
    respx.get(f"{HUB_JELLYSEERR}/api/v1/request").mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )


def mock_hub(
    alerts_response: Response | None = None, ping_response: Response | None = None
) -> tuple[respx.Route, respx.Route]:
    """The Hub's App alerts and ping endpoints: (alerts, ping) routes."""
    alerts = respx.put(HUB_ALERTS_URL).mock(return_value=alerts_response or Response(200))
    ping = respx.post(HUB_PING_URL).mock(return_value=ping_response or Response(200, text="OK"))
    return alerts, ping


def sent_snapshot(route: respx.Route) -> dict[str, Any]:
    assert route.call_count == 1, f"expected one snapshot, got {route.call_count}"
    request = route.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {HUB_APP_ALERT_TOKEN}"
    body: dict[str, Any] = json.loads(request.content)
    return body


def alerts_by_key(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {alert["key"]: alert for alert in snapshot["alerts"]}


def assert_pinged_once(ping: respx.Route) -> None:
    assert ping.call_count == 1, f"expected one ping, got {ping.call_count}"
    assert ping.calls.last.request.headers["Authorization"] == f"Bearer {HUB_PING_TOKEN}"


async def create_hub_user(email: str = HUB_USER_EMAIL, with_jellyseerr: bool = False) -> int:
    async with TestingAsyncSessionLocal() as session:
        user = User(email=email, hashed_password="fakehash")
        session.add(user)
        await session.flush()
        settings = UserSettings(
            user_id=user.id,
            jellyfin_server_url=HUB_JELLYFIN,
            jellyfin_api_key_encrypted=encrypt_value("jellyfin-key"),
        )
        if with_jellyseerr:
            settings.jellyseerr_server_url = HUB_JELLYSEERR
            settings.jellyseerr_api_key_encrypted = encrypt_value("jellyseerr-key")
        session.add(settings)
        await session.commit()
        return user.id


async def hub_sync(user_id: int, scheduled: bool = False) -> dict[str, Any]:
    async with TestingAsyncSessionLocal() as session:
        return await run_user_sync(session, user_id, scheduled=scheduled)


@pytest.mark.usefixtures("hub_configured")
class TestHubSnapshotAfterSync:
    @respx.mock
    async def test_sends_old_content_alert(self) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, _ = mock_hub()
        user_id = await create_hub_user()

        result = await hub_sync(user_id)

        assert result["status"] == "success"
        snapshot = sent_snapshot(alerts)
        assert snapshot["name"] == "Media Janitor"
        assert snapshot["url"] == f"{HUB_FRONTEND}/"
        assert snapshot["push"] is True
        assert alerts_by_key(snapshot)["old"] == {
            "key": "old",
            "title": "Old content · 5",
            "context": "29.5 GB · Dune, Heat, Alien, +2",
            "url": f"{HUB_FRONTEND}/issues?filter=old",
        }

    @respx.mock
    async def test_sends_large_and_language_alerts(self) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, _ = mock_hub()
        user_id = await create_hub_user()

        await hub_sync(user_id)

        by_key = alerts_by_key(sent_snapshot(alerts))
        assert set(by_key) == {"old", "large", "language"}
        assert by_key["large"] == {
            "key": "large",
            "title": "Large content · 1",
            "context": "20.0 GB · Dune",
            "url": f"{HUB_FRONTEND}/issues?filter=large",
        }
        assert by_key["language"] == {
            "key": "language",
            "title": "Language issues · 2",
            "context": "3.0 GB · Arrival, Amelie",
            "url": f"{HUB_FRONTEND}/issues?filter=language",
        }

    @respx.mock
    async def test_whitelisted_media_are_left_out(self) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, _ = mock_hub()
        user_id = await create_hub_user()
        async with TestingAsyncSessionLocal() as session:
            session.add(
                ContentWhitelist(
                    user_id=user_id, jellyfin_id="heat", name="Heat", media_type="Movie"
                )
            )
            await session.commit()

        await hub_sync(user_id)

        old = alerts_by_key(sent_snapshot(alerts))["old"]
        assert old["title"] == "Old content · 4"
        assert old["context"] == "25.5 GB · Dune, Alien, Arrival, +1"

    @respx.mock
    async def test_clean_sync_sends_an_empty_snapshot(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        alerts, _ = mock_hub()
        user_id = await create_hub_user()

        await hub_sync(user_id)

        assert sent_snapshot(alerts) == {
            "name": "Media Janitor",
            "url": f"{HUB_FRONTEND}/",
            "push": True,
            "alerts": [],
        }

    @respx.mock
    async def test_sends_unavailable_requests_with_titles_only(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        mock_hub_jellyseerr()
        alerts, _ = mock_hub()
        user_id = await create_hub_user(with_jellyseerr=True)

        result = await hub_sync(user_id)

        assert result["status"] == "success"
        assert sent_snapshot(alerts)["alerts"] == [
            {
                "key": "requests",
                "title": "Unavailable requests · 4",
                "context": "Solaris, Stalker, Ran, +1",
                "url": f"{HUB_FRONTEND}/issues?filter=requests",
            }
        ]


@pytest.mark.usefixtures("hub_configured")
class TestHubSyncFailedAlert:
    @respx.mock
    async def test_partial_sync_adds_sync_failed(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        mock_hub_jellyseerr_401()
        alerts, _ = mock_hub()
        user_id = await create_hub_user(with_jellyseerr=True)

        result = await hub_sync(user_id)

        assert result["status"] == "partial"
        sent = sent_snapshot(alerts)["alerts"]
        assert [a["key"] for a in sent] == ["sync-failed"]
        failed = sent[0]
        assert failed["title"] == "Media Janitor sync failed"
        assert failed["url"] == f"{HUB_FRONTEND}/"
        assert failed["context"].startswith("Jellyseerr: ")
        assert "401" in failed["context"]
        assert len(failed["context"]) <= 300

    @respx.mock
    async def test_failed_sync_still_sends_categories_from_the_cache(self) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, _ = mock_hub()
        user_id = await create_hub_user()
        await hub_sync(user_id)  # fills the cache
        respx.get(f"{HUB_JELLYFIN}/Users").mock(return_value=Response(401, json={"error": "no"}))

        result = await hub_sync(user_id)

        assert result["status"] == "failed"
        assert alerts.call_count == 2
        by_key = alerts_by_key(json.loads(alerts.calls.last.request.content))
        assert set(by_key) == {"old", "large", "language", "sync-failed"}
        assert by_key["old"]["title"] == "Old content · 5"
        assert by_key["sync-failed"]["context"].startswith("Jellyfin: ")
        assert "401" in by_key["sync-failed"]["context"]


@pytest.mark.usefixtures("hub_configured")
class TestHubOnlyMySyncsReport:
    @respx.mock
    async def test_another_users_sync_sends_nothing(self) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, ping = mock_hub()
        user_id = await create_hub_user(email="someone-else@example.com")

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert alerts.call_count == 0
        assert ping.call_count == 0

    @respx.mock
    async def test_jellyfin_not_configured_sends_nothing(self) -> None:
        alerts, ping = mock_hub()
        async with TestingAsyncSessionLocal() as session:
            user = User(email=HUB_USER_EMAIL, hashed_password="fakehash")
            session.add(user)
            await session.commit()
            user_id = user.id

        result = await hub_sync(user_id, scheduled=True)

        assert result["error"] == "Jellyfin not configured"
        assert alerts.call_count == 0
        assert ping.call_count == 0


@pytest.mark.usefixtures("hub_configured")
class TestHubNightlyPing:
    @respx.mock
    async def test_successful_scheduled_sync_pings_once(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        _, ping = mock_hub()
        user_id = await create_hub_user()

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert_pinged_once(ping)

    @respx.mock
    async def test_partial_scheduled_sync_pings_once(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        mock_hub_jellyseerr_401()
        _, ping = mock_hub()
        user_id = await create_hub_user(with_jellyseerr=True)

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "partial"
        assert_pinged_once(ping)

    @respx.mock
    async def test_failed_scheduled_sync_pings_once(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        respx.get(f"{HUB_JELLYFIN}/Users").mock(return_value=Response(401, json={"error": "no"}))
        _, ping = mock_hub()
        user_id = await create_hub_user()

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "failed"
        assert_pinged_once(ping)

    @respx.mock
    async def test_manual_sync_sends_no_ping(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        alerts, ping = mock_hub()
        user_id = await create_hub_user()

        result = await hub_sync(user_id, scheduled=False)

        assert result["status"] == "success"
        assert alerts.call_count == 1
        assert ping.call_count == 0


@pytest.mark.usefixtures("hub_configured")
class TestHubDownDoesntBreakSync:
    @respx.mock
    async def test_hub_500_is_logged_and_sync_ends_normally(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_hub_jellyfin(hub_library())
        alerts, _ = mock_hub(alerts_response=Response(500, json={"error": "boom"}))
        user_id = await create_hub_user()

        result = await hub_sync(user_id)

        assert result["status"] == "success"
        assert alerts.call_count == 1
        assert any("500" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_hub_timeout_is_logged_and_sync_ends_normally(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_hub_jellyfin(hub_library())
        alerts = respx.put(HUB_ALERTS_URL).mock(side_effect=httpx.ReadTimeout("too slow"))
        user_id = await create_hub_user()

        result = await hub_sync(user_id)

        assert result["status"] == "success"
        assert alerts.call_count == 1
        assert any("Hub" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_ping_error_does_not_change_the_outcome(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        _, ping = mock_hub(ping_response=Response(500, text="boom"))
        user_id = await create_hub_user()

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert ping.call_count == 1
        assert any("500" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_ping_timeout_does_not_change_the_outcome(self) -> None:
        mock_hub_jellyfin(CLEAN_LIBRARY)
        respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))
        ping = respx.post(HUB_PING_URL).mock(side_effect=httpx.ReadTimeout("too slow"))
        user_id = await create_hub_user()

        result = await hub_sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert ping.call_count == 1
