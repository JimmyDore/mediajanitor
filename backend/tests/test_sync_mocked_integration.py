"""
Integration tests for sync with mocked Jellyfin/Jellyseerr APIs (US-27.2).

These tests verify sync behavior with realistic mocked API responses,
running without network access (fully offline).
"""

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from app.database import (
    CachedJellyseerrRequest,
    CachedMediaItem,
    SyncStatus,
    User,
    UserSettings,
)
from app.services.encryption import encrypt_value
from app.services.sync import (
    run_user_sync,
)
from tests.conftest import TestingAsyncSessionLocal

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


class TestSuccessfulSyncStoresData:
    """Test: successful sync stores correct data in database."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_jellyfin_sync_stores_media_items(self) -> None:
        """Sync should store Jellyfin media items correctly in database."""
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
