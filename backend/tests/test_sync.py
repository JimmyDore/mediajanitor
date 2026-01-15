"""Tests for data sync functionality (US-7.1)."""

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import User, UserSettings, CachedMediaItem, CachedJellyseerrRequest, SyncStatus
from app.services.sync import extract_title_from_request, extract_release_date_from_request
from tests.conftest import TestingAsyncSessionLocal


class TestExtractTitleFromRequest:
    """Test title extraction from Jellyseerr request data (US-13.1)."""

    def test_extracts_title_for_movies(self) -> None:
        """Movies should use 'title' field."""
        request = {
            "media": {
                "mediaType": "movie",
                "title": "The Matrix",
                "originalTitle": "The Matrix (Original)",
                "tmdbId": 603,
            }
        }
        assert extract_title_from_request(request) == "The Matrix"

    def test_extracts_name_for_tv_shows(self) -> None:
        """TV shows should use 'name' field."""
        request = {
            "media": {
                "mediaType": "tv",
                "name": "Breaking Bad",
                "originalName": "Breaking Bad (Original)",
                "tmdbId": 1396,
            }
        }
        assert extract_title_from_request(request) == "Breaking Bad"

    def test_fallback_to_original_title(self) -> None:
        """Should fall back to originalTitle if title/name missing."""
        request = {
            "media": {
                "mediaType": "movie",
                "originalTitle": "Amélie",
                "tmdbId": 194,
            }
        }
        assert extract_title_from_request(request) == "Amélie"

    def test_fallback_to_original_name(self) -> None:
        """Should fall back to originalName if other fields missing."""
        request = {
            "media": {
                "mediaType": "tv",
                "originalName": "La Casa de Papel",
                "tmdbId": 71446,
            }
        }
        assert extract_title_from_request(request) == "La Casa de Papel"

    def test_fallback_to_tmdb_id(self) -> None:
        """Should fall back to TMDB ID if no title fields available."""
        request = {
            "media": {
                "mediaType": "movie",
                "tmdbId": 12345,
            }
        }
        assert extract_title_from_request(request) == "TMDB-12345"

    def test_returns_unknown_if_no_data(self) -> None:
        """Should return 'Unknown' if no title or TMDB ID available."""
        request = {"media": {}}
        assert extract_title_from_request(request) == "Unknown"

    def test_handles_empty_request(self) -> None:
        """Should handle empty request gracefully."""
        assert extract_title_from_request({}) == "Unknown"

    def test_title_takes_precedence_over_name(self) -> None:
        """'title' should take precedence over 'name'."""
        request = {
            "media": {
                "title": "Title Value",
                "name": "Name Value",
            }
        }
        assert extract_title_from_request(request) == "Title Value"

    def test_name_takes_precedence_over_original_title(self) -> None:
        """'name' should take precedence over 'originalTitle'."""
        request = {
            "media": {
                "name": "Name Value",
                "originalTitle": "Original Title",
            }
        }
        assert extract_title_from_request(request) == "Name Value"

    def test_handles_non_string_values(self) -> None:
        """Should convert non-string title values to strings."""
        request = {
            "media": {
                "title": 123,  # Numeric title (edge case)
            }
        }
        assert extract_title_from_request(request) == "123"


class TestExtractReleaseDateFromRequest:
    """Test release date extraction from Jellyseerr request data (US-13.3)."""

    def test_extracts_release_date_for_movies(self) -> None:
        """Movies should use 'releaseDate' field."""
        request = {
            "media": {
                "mediaType": "movie",
                "releaseDate": "2026-07-15",
            }
        }
        assert extract_release_date_from_request(request) == "2026-07-15"

    def test_extracts_first_air_date_for_tv(self) -> None:
        """TV shows should use 'firstAirDate' field."""
        request = {
            "media": {
                "mediaType": "tv",
                "firstAirDate": "2023-10-01",
            }
        }
        assert extract_release_date_from_request(request) == "2023-10-01"

    def test_returns_none_for_missing_release_date_movie(self) -> None:
        """Should return None if releaseDate is missing for movie."""
        request = {
            "media": {
                "mediaType": "movie",
            }
        }
        assert extract_release_date_from_request(request) is None

    def test_returns_none_for_missing_first_air_date_tv(self) -> None:
        """Should return None if firstAirDate is missing for TV."""
        request = {
            "media": {
                "mediaType": "tv",
            }
        }
        assert extract_release_date_from_request(request) is None

    def test_returns_none_for_unknown_media_type(self) -> None:
        """Should return None if mediaType is unknown."""
        request = {
            "media": {
                "mediaType": "unknown",
                "releaseDate": "2026-01-01",
            }
        }
        assert extract_release_date_from_request(request) is None

    def test_returns_none_for_empty_media(self) -> None:
        """Should return None if media object is empty."""
        request = {"media": {}}
        assert extract_release_date_from_request(request) is None

    def test_returns_none_for_empty_request(self) -> None:
        """Should return None for empty request."""
        assert extract_release_date_from_request({}) is None

    def test_handles_iso_datetime_format(self) -> None:
        """Should handle ISO datetime format from API."""
        request = {
            "media": {
                "mediaType": "movie",
                "releaseDate": "2026-07-15T00:00:00.000Z",
            }
        }
        # Should return as-is (the API returns it this way sometimes)
        assert extract_release_date_from_request(request) == "2026-07-15T00:00:00.000Z"


class TestSyncModels:
    """Test database models for caching."""

    @pytest.mark.asyncio
    async def test_cached_media_item_model_exists(self, client: TestClient) -> None:
        """CachedMediaItem model should exist with required fields."""
        async with TestingAsyncSessionLocal() as session:
            # Verify the model has expected columns
            item = CachedMediaItem(
                user_id=1,
                jellyfin_id="test-123",
                name="Test Movie",
                media_type="Movie",
                production_year=2023,
                date_created="2023-01-15T10:00:00Z",
                path="/media/movies/Test.mkv",
                size_bytes=5000000000,
                played=True,
                play_count=2,
                last_played_date="2023-06-15T10:00:00Z",
                raw_data={"extra": "data"},
            )
            session.add(item)
            await session.commit()
            assert item.id is not None

    @pytest.mark.asyncio
    async def test_cached_jellyseerr_request_model_exists(self, client: TestClient) -> None:
        """CachedJellyseerrRequest model should exist with required fields."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=123,
                tmdb_id=456,
                media_type="movie",
                status=2,
                title="Test Movie",
                requested_by="TestUser",
                created_at_source="2024-01-01T10:00:00Z",
                raw_data={"full": "request"},
            )
            session.add(request)
            await session.commit()
            assert request.id is not None

    @pytest.mark.asyncio
    async def test_cached_jellyseerr_request_has_release_date_column(self, client: TestClient) -> None:
        """CachedJellyseerrRequest should have release_date column (US-13.3)."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=124,
                tmdb_id=789,
                media_type="movie",
                status=2,
                title="Future Movie",
                requested_by="TestUser",
                created_at_source="2024-01-01T10:00:00Z",
                release_date="2026-07-15",  # New column
                raw_data={"full": "request"},
            )
            session.add(request)
            await session.commit()
            assert request.id is not None
            assert request.release_date == "2026-07-15"

    @pytest.mark.asyncio
    async def test_sync_status_model_exists(self, client: TestClient) -> None:
        """SyncStatus model should track last sync time per user."""
        async with TestingAsyncSessionLocal() as session:
            status = SyncStatus(
                user_id=1,
                last_sync_started=datetime.now(timezone.utc),
                last_sync_completed=datetime.now(timezone.utc),
                last_sync_status="success",
            )
            session.add(status)
            await session.commit()
            assert status.id is not None


class TestSyncEndpoints:
    """Test sync API endpoints."""

    def _get_auth_token(self, client: TestClient, email: str = "sync@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={"email": email, "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        return login_response.json()["access_token"]

    def test_trigger_sync_requires_auth(self, client: TestClient) -> None:
        """POST /api/sync should require authentication."""
        response = client.post("/api/sync")
        assert response.status_code == 401

    def test_trigger_sync_requires_jellyfin_settings(self, client: TestClient) -> None:
        """POST /api/sync should fail if no Jellyfin settings configured."""
        token = self._get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/api/sync", headers=headers)
        assert response.status_code == 400
        assert "Jellyfin" in response.json()["detail"]

    @patch("app.routers.sync.run_user_sync")
    def test_trigger_sync_success(
        self, mock_run_sync: AsyncMock, client: TestClient
    ) -> None:
        """POST /api/sync should trigger a sync for authenticated user."""
        mock_run_sync.return_value = {
            "status": "success",
            "media_items_synced": 10,
            "requests_synced": 5,
        }

        token = self._get_auth_token(client, "sync2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin (mock the validation)
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        response = client.post("/api/sync", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_get_sync_status_requires_auth(self, client: TestClient) -> None:
        """GET /api/sync/status should require authentication."""
        response = client.get("/api/sync/status")
        assert response.status_code == 401

    def test_get_sync_status_returns_null_if_never_synced(self, client: TestClient) -> None:
        """GET /api/sync/status should return null last_synced if never synced."""
        token = self._get_auth_token(client, "sync3@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/sync/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["last_synced"] is None
        assert data["status"] is None


class TestSyncService:
    """Test sync service functions."""

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media")
    @patch("app.services.sync.fetch_jellyseerr_requests")
    async def test_run_user_sync_fetches_and_caches_data(
        self,
        mock_jellyseerr: AsyncMock,
        mock_jellyfin: AsyncMock,
        client: TestClient,
        mock_jellyfin_response: dict,
        mock_jellyseerr_response: dict,
    ) -> None:
        """run_user_sync should fetch from APIs and cache in database."""
        from app.services.sync import run_user_sync

        mock_jellyfin.return_value = mock_jellyfin_response["Items"]
        mock_jellyseerr.return_value = mock_jellyseerr_response["results"]

        async with TestingAsyncSessionLocal() as session:
            # Create a user with settings
            user = User(
                email="test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            # Run sync with mocked decryption
            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                result = await run_user_sync(session, user.id)

            assert result["status"] == "success"
            assert result["media_items_synced"] == 2
            assert result["requests_synced"] == 2

    @pytest.mark.asyncio
    async def test_run_user_sync_handles_failed_api_calls(
        self, client: TestClient
    ) -> None:
        """run_user_sync should handle API failures gracefully."""
        from app.services.sync import run_user_sync

        async with TestingAsyncSessionLocal() as session:
            # Create a user with settings
            user = User(
                email="test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            # Mock API failure
            with patch("app.services.sync.fetch_jellyfin_media", side_effect=Exception("API Error")):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    result = await run_user_sync(session, user.id)

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media")
    async def test_sync_clears_old_cache_before_storing_new(
        self,
        mock_jellyfin: AsyncMock,
        client: TestClient,
        mock_jellyfin_response: dict,
    ) -> None:
        """Sync should replace old cached data with new data."""
        from sqlalchemy import select
        from app.services.sync import run_user_sync

        mock_jellyfin.return_value = mock_jellyfin_response["Items"]

        async with TestingAsyncSessionLocal() as session:
            # Create a user with settings
            user = User(
                email="test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)

            # Add old cached item
            old_item = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="old-item-123",
                name="Old Movie",
                media_type="Movie",
            )
            session.add(old_item)
            await session.commit()

            # Run sync
            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                await run_user_sync(session, user.id)

            # Old item should be gone, new items should exist
            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = result.scalars().all()

            item_ids = [item.jellyfin_id for item in items]
            assert "old-item-123" not in item_ids
            assert "test-movie-1" in item_ids


class TestSyncRateLimiting:
    """Test rate limiting for sync endpoint (US-7.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "ratelimit@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={"email": email, "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        return login_response.json()["access_token"]

    @patch("app.services.sync.fetch_jellyfin_media")
    @patch("app.services.sync.decrypt_value")
    def test_sync_rate_limited_after_recent_sync(
        self, mock_decrypt: AsyncMock, mock_fetch: AsyncMock, client: TestClient
    ) -> None:
        """POST /api/sync should return 429 if user synced within 5 minutes."""
        mock_decrypt.return_value = "decrypted-key"
        mock_fetch.return_value = []  # Empty response for simplicity

        token = self._get_auth_token(client, "ratelimit1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # First sync should succeed (this updates DB sync status)
        response1 = client.post("/api/sync", headers=headers)
        assert response1.status_code == 200

        # Second sync immediately after should be rate limited
        response2 = client.post("/api/sync", headers=headers)
        assert response2.status_code == 429
        assert "rate" in response2.json()["detail"].lower() or "minute" in response2.json()["detail"].lower()

    @patch("app.routers.sync.get_sync_status")
    @patch("app.routers.sync.run_user_sync")
    def test_sync_allowed_after_5_minutes(
        self, mock_run_sync: AsyncMock, mock_get_status: AsyncMock, client: TestClient
    ) -> None:
        """POST /api/sync should succeed if last sync was >5 minutes ago."""
        from datetime import timedelta

        mock_run_sync.return_value = {
            "status": "success",
            "media_items_synced": 10,
            "requests_synced": 5,
        }

        # Mock that last sync was 6 minutes ago
        old_sync_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=old_sync_time,
            last_sync_completed=old_sync_time,
            last_sync_status="success",
        )
        mock_get_status.return_value = mock_status

        token = self._get_auth_token(client, "ratelimit2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # Sync should succeed since last sync was >5 minutes ago
        response = client.post("/api/sync", headers=headers)
        assert response.status_code == 200

    @patch("app.services.sync.fetch_jellyfin_media")
    @patch("app.services.sync.decrypt_value")
    def test_sync_rate_limit_response_includes_wait_time(
        self, mock_decrypt: AsyncMock, mock_fetch: AsyncMock, client: TestClient
    ) -> None:
        """Rate limit response should include how long to wait."""
        mock_decrypt.return_value = "decrypted-key"
        mock_fetch.return_value = []

        token = self._get_auth_token(client, "ratelimit3@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # First sync
        client.post("/api/sync", headers=headers)

        # Second sync - should include wait time info
        response = client.post("/api/sync", headers=headers)
        assert response.status_code == 429
        # Should mention minutes or time remaining
        detail = response.json()["detail"]
        assert "minute" in detail.lower()

    @patch("app.services.sync.fetch_jellyfin_media")
    @patch("app.services.sync.decrypt_value")
    def test_rate_limit_is_per_user(
        self, mock_decrypt: AsyncMock, mock_fetch: AsyncMock, client: TestClient
    ) -> None:
        """Rate limit should be per-user, not global."""
        mock_decrypt.return_value = "decrypted-key"
        mock_fetch.return_value = []

        # User 1
        token1 = self._get_auth_token(client, "ratelimit4@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers1,
            )

        # User 2
        token2 = self._get_auth_token(client, "ratelimit5@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers2,
            )

        # User 1 syncs
        response1 = client.post("/api/sync", headers=headers1)
        assert response1.status_code == 200

        # User 2 should still be able to sync
        response2 = client.post("/api/sync", headers=headers2)
        assert response2.status_code == 200


class TestMultiUserWatchDataAggregation:
    """Test multi-user watch data aggregation (US-17.1)."""

    @pytest.mark.asyncio
    async def test_aggregate_watch_data_played_true_if_any_user_watched(
        self,
    ) -> None:
        """played should be True if ANY user has watched the content."""
        from app.services.sync import aggregate_user_watch_data

        # User 1 has not watched, User 2 has watched
        user_data_list = [
            {"Played": False, "PlayCount": 0, "LastPlayedDate": None},
            {"Played": True, "PlayCount": 2, "LastPlayedDate": "2024-01-15T10:00:00Z"},
        ]

        result = aggregate_user_watch_data(user_data_list)

        assert result["played"] is True

    @pytest.mark.asyncio
    async def test_aggregate_watch_data_last_played_uses_most_recent(
        self,
    ) -> None:
        """last_played_date should be the most recent date across all users."""
        from app.services.sync import aggregate_user_watch_data

        user_data_list = [
            {"Played": True, "PlayCount": 1, "LastPlayedDate": "2024-01-10T10:00:00Z"},
            {"Played": True, "PlayCount": 1, "LastPlayedDate": "2024-02-20T15:30:00Z"},
            {"Played": True, "PlayCount": 1, "LastPlayedDate": "2024-01-25T08:00:00Z"},
        ]

        result = aggregate_user_watch_data(user_data_list)

        assert result["last_played_date"] == "2024-02-20T15:30:00Z"

    @pytest.mark.asyncio
    async def test_aggregate_watch_data_play_count_sums_all_users(
        self,
    ) -> None:
        """play_count should sum all users' play counts."""
        from app.services.sync import aggregate_user_watch_data

        user_data_list = [
            {"Played": True, "PlayCount": 3, "LastPlayedDate": "2024-01-10T10:00:00Z"},
            {"Played": True, "PlayCount": 5, "LastPlayedDate": "2024-01-15T10:00:00Z"},
            {"Played": False, "PlayCount": 0, "LastPlayedDate": None},
        ]

        result = aggregate_user_watch_data(user_data_list)

        assert result["play_count"] == 8

    @pytest.mark.asyncio
    async def test_aggregate_watch_data_handles_no_watches(
        self,
    ) -> None:
        """Should return False/0/None if no user has watched."""
        from app.services.sync import aggregate_user_watch_data

        user_data_list = [
            {"Played": False, "PlayCount": 0, "LastPlayedDate": None},
            {"Played": False, "PlayCount": 0, "LastPlayedDate": None},
        ]

        result = aggregate_user_watch_data(user_data_list)

        assert result["played"] is False
        assert result["play_count"] == 0
        assert result["last_played_date"] is None

    @pytest.mark.asyncio
    async def test_aggregate_watch_data_handles_empty_list(
        self,
    ) -> None:
        """Should handle empty user data list gracefully."""
        from app.services.sync import aggregate_user_watch_data

        result = aggregate_user_watch_data([])

        assert result["played"] is False
        assert result["play_count"] == 0
        assert result["last_played_date"] is None

    @pytest.mark.asyncio
    async def test_fetch_all_users_returns_users_list(
        self,
    ) -> None:
        """fetch_jellyfin_users should return list of users from API."""
        from app.services.sync import fetch_jellyfin_users
        import httpx

        users_response = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
            {"Id": "user3", "Name": "Bob"},
        ]

        async def mock_get(*args, **kwargs):
            response = httpx.Response(200, json=users_response)
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert len(users) == 3
        assert users[0]["Name"] == "John"
        assert users[1]["Name"] == "Jane"
        assert users[2]["Name"] == "Bob"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_user_items")
    async def test_fetch_all_users_media_aggregates_watch_data(
        self,
        mock_fetch_user_items: AsyncMock,
        mock_fetch_users: AsyncMock,
    ) -> None:
        """fetch_all_users_media should aggregate watch data from all users."""
        from app.services.sync import fetch_all_users_media

        # Two users
        mock_fetch_users.return_value = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
        ]

        # Same movie seen by both users, different watch data
        # User 1: watched once 2 weeks ago
        # User 2: watched 3 times, most recent yesterday
        user1_items = [
            {
                "Id": "movie1",
                "Name": "Test Movie",
                "Type": "Movie",
                "ProductionYear": 2023,
                "UserData": {
                    "Played": True,
                    "PlayCount": 1,
                    "LastPlayedDate": "2024-01-01T10:00:00Z",
                },
            }
        ]
        user2_items = [
            {
                "Id": "movie1",
                "Name": "Test Movie",
                "Type": "Movie",
                "ProductionYear": 2023,
                "UserData": {
                    "Played": True,
                    "PlayCount": 3,
                    "LastPlayedDate": "2024-01-15T14:30:00Z",
                },
            }
        ]

        mock_fetch_user_items.side_effect = [user1_items, user2_items]

        items = await fetch_all_users_media("http://jellyfin.local", "api-key")

        # Should have one item with aggregated data
        assert len(items) == 1
        item = items[0]
        user_data = item["UserData"]

        # Aggregated: played=True, play_count=4, last_played_date=most recent
        assert user_data["Played"] is True
        assert user_data["PlayCount"] == 4
        assert user_data["LastPlayedDate"] == "2024-01-15T14:30:00Z"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_user_items")
    async def test_fetch_all_users_media_with_unmatched_items(
        self,
        mock_fetch_user_items: AsyncMock,
        mock_fetch_users: AsyncMock,
    ) -> None:
        """Items only in one user's library should still be included."""
        from app.services.sync import fetch_all_users_media

        mock_fetch_users.return_value = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
        ]

        # User 1 has Movie A, User 2 has Movie B (no overlap)
        user1_items = [
            {
                "Id": "movieA",
                "Name": "Movie A",
                "Type": "Movie",
                "UserData": {"Played": True, "PlayCount": 2, "LastPlayedDate": "2024-01-10T10:00:00Z"},
            }
        ]
        user2_items = [
            {
                "Id": "movieB",
                "Name": "Movie B",
                "Type": "Movie",
                "UserData": {"Played": False, "PlayCount": 0, "LastPlayedDate": None},
            }
        ]

        mock_fetch_user_items.side_effect = [user1_items, user2_items]

        items = await fetch_all_users_media("http://jellyfin.local", "api-key")

        # Should have both movies
        assert len(items) == 2
        movie_names = {item["Name"] for item in items}
        assert movie_names == {"Movie A", "Movie B"}
