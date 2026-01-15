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
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
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
            with patch("app.services.sync.fetch_jellyfin_media_with_progress", side_effect=Exception("API Error")):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    result = await run_user_sync(session, user.id)

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
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

    @patch("app.routers.sync.run_user_sync")
    @patch("app.routers.sync.get_sync_status")
    def test_force_bypasses_rate_limit_for_first_sync(
        self, mock_get_status: AsyncMock, mock_run_sync: AsyncMock, client: TestClient
    ) -> None:
        """POST /api/sync with force=true should bypass rate limit for first sync (US-18.2)."""
        mock_run_sync.return_value = {
            "status": "success",
            "media_items_synced": 10,
            "requests_synced": 5,
        }

        # Mock a sync status that was just started but never completed (first sync)
        from datetime import timedelta
        recent_sync_time = datetime.now(timezone.utc) - timedelta(seconds=30)
        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=recent_sync_time,
            last_sync_completed=None,  # Never completed = first sync
            last_sync_status=None,
        )
        mock_get_status.return_value = mock_status

        token = self._get_auth_token(client, "force1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # With force=true and first sync, should succeed despite recent sync_started
        response = client.post(
            "/api/sync",
            json={"force": True},
            headers=headers,
        )
        assert response.status_code == 200

    @patch("app.services.sync.fetch_jellyfin_media")
    @patch("app.services.sync.decrypt_value")
    def test_force_does_not_bypass_rate_limit_for_subsequent_syncs(
        self, mock_decrypt: AsyncMock, mock_fetch: AsyncMock, client: TestClient
    ) -> None:
        """POST /api/sync with force=true should NOT bypass rate limit if already synced before."""
        mock_decrypt.return_value = "decrypted-key"
        mock_fetch.return_value = []

        token = self._get_auth_token(client, "force2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # First sync completes normally
        response1 = client.post("/api/sync", headers=headers)
        assert response1.status_code == 200

        # Second sync with force=true should still be rate limited since user has synced before
        response2 = client.post(
            "/api/sync",
            json={"force": True},
            headers=headers,
        )
        assert response2.status_code == 429


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


class TestSyncProgressTracking:
    """Test sync progress tracking (US-17.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "progress@example.com") -> str:
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

    def test_sync_status_includes_progress_fields(self, client: TestClient) -> None:
        """GET /api/sync/status should include is_syncing and progress fields."""
        token = self._get_auth_token(client, "progress1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/sync/status", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should have is_syncing field
        assert "is_syncing" in data
        assert data["is_syncing"] is False  # Not syncing yet

        # Should have progress field (null when not syncing)
        assert "progress" in data
        assert data["progress"] is None

    @pytest.mark.asyncio
    async def test_sync_status_model_has_progress_columns(self, client: TestClient) -> None:
        """SyncStatus model should have progress tracking columns."""
        async with TestingAsyncSessionLocal() as session:
            status = SyncStatus(
                user_id=999,
                last_sync_started=datetime.now(timezone.utc),
                last_sync_status="in_progress",
                current_step="syncing_media",
                total_steps=2,
                current_step_progress=3,
                current_step_total=10,
                current_user_name="John",
            )
            session.add(status)
            await session.commit()

            assert status.id is not None
            assert status.current_step == "syncing_media"
            assert status.total_steps == 2
            assert status.current_step_progress == 3
            assert status.current_step_total == 10
            assert status.current_user_name == "John"

    @pytest.mark.asyncio
    async def test_update_sync_progress_updates_progress_fields(
        self, client: TestClient
    ) -> None:
        """update_sync_progress should update only progress fields."""
        from app.services.sync import update_sync_status, update_sync_progress, get_sync_status

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="progress_test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create initial sync status
            await update_sync_status(
                session, user.id, "in_progress", started=True,
                current_step="syncing_media", total_steps=2
            )

            # Update progress
            await update_sync_progress(
                session, user.id,
                current_step_progress=5,
                current_step_total=10,
                current_user_name="TestUser"
            )

            # Verify progress was updated
            status = await get_sync_status(session, user.id)
            assert status is not None
            assert status.current_step == "syncing_media"  # Unchanged
            assert status.current_step_progress == 5
            assert status.current_step_total == 10
            assert status.current_user_name == "TestUser"

    @pytest.mark.asyncio
    async def test_sync_completion_clears_progress_fields(
        self, client: TestClient
    ) -> None:
        """When sync completes, progress fields should be cleared."""
        from app.services.sync import update_sync_status, update_sync_progress, get_sync_status

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="progress_clear@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Start sync with progress
            await update_sync_status(
                session, user.id, "in_progress", started=True,
                current_step="syncing_media", total_steps=2
            )
            await update_sync_progress(
                session, user.id,
                current_step_progress=5,
                current_step_total=10,
                current_user_name="TestUser"
            )

            # Complete sync
            await update_sync_status(
                session, user.id, "success",
                media_count=100, requests_count=50
            )

            # Verify progress fields were cleared
            status = await get_sync_status(session, user.id)
            assert status is not None
            assert status.current_step is None
            assert status.total_steps is None
            assert status.current_step_progress is None
            assert status.current_step_total is None
            assert status.current_user_name is None

    def test_sync_status_returns_progress_when_syncing(
        self, client: TestClient
    ) -> None:
        """GET /api/sync/status should return progress when sync is active."""
        # Register user via API (proper password hash)
        token = self._get_auth_token(client, "progress_api@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # First request creates sync status with null values
        response = client.get("/api/sync/status", headers=headers)
        assert response.status_code == 200

        # Now manually set progress in DB by mocking a sync in progress
        # We'll patch get_sync_status to return a mock with progress
        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=datetime.now(timezone.utc),
            current_step="syncing_media",
            total_steps=2,
            current_step_progress=3,
            current_step_total=10,
            current_user_name="John",
        )

        with patch("app.routers.sync.get_sync_status", return_value=mock_status):
            response = client.get("/api/sync/status", headers=headers)
            assert response.status_code == 200
            data = response.json()

            assert data["is_syncing"] is True
            assert data["progress"] is not None
            assert data["progress"]["current_step"] == "syncing_media"
            assert data["progress"]["total_steps"] == 2
            assert data["progress"]["current_step_progress"] == 3
            assert data["progress"]["current_step_total"] == 10
            assert data["progress"]["current_user_name"] == "John"


class TestCalculateSeasonSizes:
    """Test season size calculation (US-20.2)."""

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_updates_series_only(
        self, client: TestClient
    ) -> None:
        """calculate_season_sizes should only update Series items, not Movies."""
        from app.services.sync import calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            # Create a user with settings
            user = User(
                email="season_size1@example.com",
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

            # Add a movie and a series to cache
            movie = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="movie-123",
                name="Test Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,  # 5 GB
            )
            series = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="series-456",
                name="Test Series",
                media_type="Series",
            )
            session.add(movie)
            session.add(series)
            await session.commit()

            # Mock the Jellyfin API response for seasons
            mock_seasons_response = {
                "Items": [
                    {
                        "Id": "season1",
                        "Name": "Season 1",
                        "IndexNumber": 1,
                        "Type": "Season",
                    },
                    {
                        "Id": "season2",
                        "Name": "Season 2",
                        "IndexNumber": 2,
                        "Type": "Season",
                    },
                ]
            }
            # Season 1 episodes: 10 GB total, Season 2 episodes: 15 GB total
            mock_episodes_s1 = {
                "Items": [
                    {"Id": "ep1", "MediaSources": [{"Size": 5_000_000_000}]},  # 5 GB
                    {"Id": "ep2", "MediaSources": [{"Size": 5_000_000_000}]},  # 5 GB
                ]
            }
            mock_episodes_s2 = {
                "Items": [
                    {"Id": "ep3", "MediaSources": [{"Size": 8_000_000_000}]},  # 8 GB
                    {"Id": "ep4", "MediaSources": [{"Size": 7_000_000_000}]},  # 7 GB
                ]
            }

            async def mock_get(self, url, **kwargs):
                import httpx
                params = kwargs.get("params", {})
                parent_id = params.get("ParentId", "")

                # Seasons request for series-456
                if "series-456" in str(parent_id) or ("Items" in str(url) and "Season" in str(params.get("IncludeItemTypes", ""))):
                    if parent_id == "series-456":
                        return httpx.Response(200, json=mock_seasons_response, request=httpx.Request("GET", url))
                # Episodes for season1
                if parent_id == "season1":
                    return httpx.Response(200, json=mock_episodes_s1, request=httpx.Request("GET", url))
                # Episodes for season2
                if parent_id == "season2":
                    return httpx.Response(200, json=mock_episodes_s2, request=httpx.Request("GET", url))
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    await calculate_season_sizes(
                        session, user.id,
                        "http://jellyfin.local", "decrypted-key"
                    )

            # Refresh from DB
            from sqlalchemy import select
            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = {item.name: item for item in result.scalars().all()}

            # Movie should NOT have largest_season_size_bytes set
            assert items["Test Movie"].largest_season_size_bytes is None

            # Series should have largest season size (15 GB from Season 2)
            assert items["Test Series"].largest_season_size_bytes == 15_000_000_000

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_handles_api_errors(
        self, client: TestClient
    ) -> None:
        """calculate_season_sizes should continue if API fails for one series."""
        from app.services.sync import calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="season_size2@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Add two series
            series1 = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="series-1",
                name="Series 1",
                media_type="Series",
            )
            series2 = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="series-2",
                name="Series 2",
                media_type="Series",
            )
            session.add(series1)
            session.add(series2)
            await session.commit()

            call_count = {"count": 0}

            async def mock_get(self, url, **kwargs):
                import httpx
                call_count["count"] += 1
                params = kwargs.get("params", {})
                parent_id = params.get("ParentId", "")

                # First series call succeeds
                if parent_id == "series-1":
                    return httpx.Response(200, json={
                        "Items": [{"Id": "s1-season1", "IndexNumber": 1}]
                    }, request=httpx.Request("GET", url))
                elif parent_id == "s1-season1":
                    return httpx.Response(200, json={
                        "Items": [{"Id": "ep1", "MediaSources": [{"Size": 5_000_000_000}]}]
                    }, request=httpx.Request("GET", url))
                # Second series call fails
                elif parent_id == "series-2":
                    raise httpx.RequestError("Connection failed")

                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            with patch("httpx.AsyncClient.get", new=mock_get):
                # Should not raise, just log warning and continue
                await calculate_season_sizes(
                    session, user.id,
                    "http://jellyfin.local", "api-key"
                )

            from sqlalchemy import select
            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = {item.name: item for item in result.scalars().all()}

            # First series should have size calculated
            assert items["Series 1"].largest_season_size_bytes == 5_000_000_000

            # Second series should be None (API failed)
            assert items["Series 2"].largest_season_size_bytes is None

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_handles_empty_series(
        self, client: TestClient
    ) -> None:
        """calculate_season_sizes should handle series with no seasons."""
        from app.services.sync import calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="season_size3@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            series = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="empty-series",
                name="Empty Series",
                media_type="Series",
            )
            session.add(series)
            await session.commit()

            async def mock_get(self, url, **kwargs):
                import httpx
                # Return empty seasons list
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            with patch("httpx.AsyncClient.get", new=mock_get):
                await calculate_season_sizes(
                    session, user.id,
                    "http://jellyfin.local", "api-key"
                )

            from sqlalchemy import select
            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = result.scalars().all()

            # Series with no seasons should have None
            assert items[0].largest_season_size_bytes is None

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_progress_logging(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """calculate_season_sizes should log progress."""
        import logging
        from app.services.sync import calculate_season_sizes

        caplog.set_level(logging.INFO)

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="season_size4@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            series1 = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="s1",
                name="Series One",
                media_type="Series",
            )
            series2 = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="s2",
                name="Series Two",
                media_type="Series",
            )
            session.add(series1)
            session.add(series2)
            await session.commit()

            async def mock_get(self, url, **kwargs):
                import httpx
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            with patch("httpx.AsyncClient.get", new=mock_get):
                await calculate_season_sizes(
                    session, user.id,
                    "http://jellyfin.local", "api-key"
                )

            # Should have log message about calculating sizes
            assert any("Calculating season sizes for 2 series" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_cached_media_item_has_largest_season_size_column(
        self, client: TestClient
    ) -> None:
        """CachedMediaItem should have largest_season_size_bytes column."""
        async with TestingAsyncSessionLocal() as session:
            item = CachedMediaItem(
                user_id=1,
                jellyfin_id="test-series",
                name="Test Series",
                media_type="Series",
                largest_season_size_bytes=15_000_000_000,  # 15 GB
            )
            session.add(item)
            await session.commit()

            assert item.id is not None
            assert item.largest_season_size_bytes == 15_000_000_000


class TestSyncCalculatingSizesState:
    """Test calculating_sizes sync state (US-20.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "calcsize@example.com") -> str:
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

    @pytest.mark.asyncio
    async def test_sync_status_includes_calculating_sizes_step(
        self, client: TestClient
    ) -> None:
        """Sync status should show calculating_sizes step after main sync."""
        async with TestingAsyncSessionLocal() as session:
            status = SyncStatus(
                user_id=999,
                last_sync_started=datetime.now(timezone.utc),
                last_sync_status="in_progress",
                current_step="calculating_sizes",
                total_steps=2,
                current_step_progress=5,
                current_step_total=10,
            )
            session.add(status)
            await session.commit()

            assert status.current_step == "calculating_sizes"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.calculate_season_sizes")
    async def test_sync_triggers_calculate_season_sizes_after_media_sync(
        self,
        mock_calculate_sizes: AsyncMock,
        mock_jellyfin: AsyncMock,
        client: TestClient,
    ) -> None:
        """run_user_sync should call calculate_season_sizes after caching media."""
        from app.services.sync import run_user_sync

        mock_jellyfin.return_value = [
            {
                "Id": "series-1",
                "Name": "Test Series",
                "Type": "Series",
                "UserData": {"Played": False, "PlayCount": 0},
            }
        ]

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="calc_trigger@example.com",
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

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                await run_user_sync(session, user.id)

            # calculate_season_sizes should have been called
            mock_calculate_sizes.assert_called_once()
            call_args = mock_calculate_sizes.call_args
            assert call_args[0][1] == user.id  # user_id
            assert call_args[0][2] == "http://jellyfin.local"  # server_url
            assert call_args[0][3] == "decrypted-key"  # api_key

    def test_sync_status_returns_calculating_sizes_in_progress(
        self, client: TestClient
    ) -> None:
        """GET /api/sync/status should include calculating_sizes step."""
        token = self._get_auth_token(client, "calcsize1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=datetime.now(timezone.utc),
            current_step="calculating_sizes",
            total_steps=2,
            current_step_progress=5,
            current_step_total=20,
        )

        with patch("app.routers.sync.get_sync_status", return_value=mock_status):
            response = client.get("/api/sync/status", headers=headers)
            assert response.status_code == 200
            data = response.json()

            assert data["is_syncing"] is True
            assert data["progress"]["current_step"] == "calculating_sizes"


class TestSyncFailureNotifications:
    """Tests for Slack notifications on sync failures (US-21.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "syncfail@example.com") -> str:
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

    @pytest.mark.asyncio
    async def test_jellyfin_sync_failure_sends_notification(self, client: TestClient) -> None:
        """Jellyfin sync failure should trigger Slack notification."""
        from unittest.mock import patch, AsyncMock
        from app.services.sync import run_user_sync

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="jf_fail_notify@example.com",
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

            # Mock Jellyfin to fail
            with patch("app.services.sync.fetch_jellyfin_media_with_progress") as mock_fetch:
                mock_fetch.side_effect = Exception("Jellyfin connection failed")
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    with patch("app.services.sync.send_sync_failure_notification") as mock_notify:
                        result = await run_user_sync(session, user.id)

                        # Sync should have failed
                        assert result["status"] == "failed"
                        assert "Jellyfin" in result["error"]

                        # Notification should have been called
                        mock_notify.assert_called_once()
                        call_kwargs = mock_notify.call_args[1]
                        assert call_kwargs["user_email"] == "jf_fail_notify@example.com"
                        assert call_kwargs["service"] == "Jellyfin"
                        assert "Jellyfin connection failed" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_jellyseerr_sync_failure_sends_notification(self, client: TestClient) -> None:
        """Jellyseerr sync failure should trigger Slack notification."""
        from unittest.mock import patch, AsyncMock
        from app.services.sync import run_user_sync

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="js_fail_notify@example.com",
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

            # Mock Jellyfin to succeed, Jellyseerr to fail
            with patch("app.services.sync.fetch_jellyfin_media_with_progress") as mock_jf:
                mock_jf.return_value = []
                with patch("app.services.sync.fetch_jellyseerr_requests") as mock_js:
                    mock_js.side_effect = Exception("Jellyseerr API error")
                    with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                        with patch("app.services.sync.calculate_season_sizes"):
                            with patch("app.services.sync.send_sync_failure_notification") as mock_notify:
                                result = await run_user_sync(session, user.id)

                                # Sync should be partial (Jellyfin succeeded, Jellyseerr failed)
                                assert result["status"] == "partial"
                                assert "Jellyseerr" in result["error"]

                                # Notification should have been called for Jellyseerr failure
                                mock_notify.assert_called_once()
                                call_kwargs = mock_notify.call_args[1]
                                assert call_kwargs["user_email"] == "js_fail_notify@example.com"
                                assert call_kwargs["service"] == "Jellyseerr"
                                assert "Jellyseerr API error" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_sync_failure_notification_is_fire_and_forget(self, client: TestClient) -> None:
        """Notification failure should not affect sync error handling."""
        from unittest.mock import patch, AsyncMock
        from app.services.sync import run_user_sync

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="ff_fail_notify@example.com",
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

            # Mock Jellyfin to fail and notification to also fail
            with patch("app.services.sync.fetch_jellyfin_media_with_progress") as mock_fetch:
                mock_fetch.side_effect = Exception("Jellyfin connection failed")
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    with patch("app.services.sync.send_sync_failure_notification") as mock_notify:
                        mock_notify.side_effect = Exception("Slack webhook failed")

                        # Sync should complete (with failure) even if notification fails
                        result = await run_user_sync(session, user.id)

                        assert result["status"] == "failed"
                        assert "Jellyfin" in result["error"]

    @pytest.mark.asyncio
    async def test_sync_failure_notification_without_webhook_configured(self, client: TestClient) -> None:
        """Sync failure should work when Slack webhook is not configured."""
        from unittest.mock import patch
        from app.services.sync import run_user_sync, send_sync_failure_notification

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="no_webhook_fail@example.com",
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

            # Mock webhook not configured
            with patch("app.services.sync.get_settings") as mock_settings:
                mock_settings.return_value.slack_webhook_sync_failures = ""
                with patch("app.services.sync.fetch_jellyfin_media_with_progress") as mock_fetch:
                    mock_fetch.side_effect = Exception("Jellyfin connection failed")
                    with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                        result = await run_user_sync(session, user.id)

                        # Sync should complete even with no webhook
                        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_sync_failure_notification_uses_block_kit_format(self, client: TestClient) -> None:
        """Sync failure notification should use Slack Block Kit format."""
        from unittest.mock import patch, AsyncMock
        from app.services.sync import send_sync_failure_notification

        with patch("app.services.sync.send_slack_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch("app.services.sync.get_settings") as mock_settings_fn:
                from app.config import Settings
                mock_settings = Settings()
                mock_settings.slack_webhook_sync_failures = "https://hooks.slack.com/test"
                mock_settings_fn.return_value = mock_settings

                await send_sync_failure_notification(
                    user_email="test@example.com",
                    service="Jellyfin",
                    error_message="Connection timed out"
                )

                # Should have called send_slack_message with Block Kit format
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                message = call_args[0][1]  # Second positional arg is the message dict
                # Block Kit messages should have "blocks" key
                assert "blocks" in message
                assert "text" in message  # Fallback text

    def test_celery_sync_user_failure_sends_notification(self, client: TestClient) -> None:
        """Celery sync_user task failure should trigger Slack notification."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.celery_app import celery_app
        from app.tasks import sync_user

        # Set eager mode for testing
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            with patch("app.tasks._run_sync_for_user") as mock_run_sync:
                # Simulate sync failure
                mock_run_sync.side_effect = Exception("Sync failed with error")

                with patch("app.tasks.send_sync_failure_notification_for_celery") as mock_notify:
                    result = sync_user(123)  # user_id = 123

                    # Result should indicate failure
                    assert result["status"] == "failed"
                    assert "error" in result

                    # Notification should have been called
                    mock_notify.assert_called_once()
                    call_kwargs = mock_notify.call_args[1]
                    assert call_kwargs["user_id"] == 123
                    assert "Sync failed with error" in call_kwargs["error_message"]
        finally:
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False
