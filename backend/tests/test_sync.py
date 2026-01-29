"""Tests for data sync functionality (US-7.1)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import CachedJellyseerrRequest, CachedMediaItem, SyncStatus, User, UserSettings
from app.services.sync import (
    extract_french_title_from_request,
    extract_release_date_from_request,
    extract_title_from_request,
)
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


class TestExtractFrenchTitleFromRequest:
    """Test French title extraction from Jellyseerr request data (US-38.2)."""

    def test_extracts_title_fr_for_movies(self) -> None:
        """Movies should use 'title_fr' field."""
        request = {
            "media": {
                "mediaType": "movie",
                "title": "The Matrix",
                "title_fr": "Matrix",
                "tmdbId": 603,
            }
        }
        assert extract_french_title_from_request(request) == "Matrix"

    def test_extracts_name_fr_for_tv_shows(self) -> None:
        """TV shows should use 'name_fr' field."""
        request = {
            "media": {
                "mediaType": "tv",
                "name": "Breaking Bad",
                "name_fr": "Breaking Bad",
                "tmdbId": 1396,
            }
        }
        assert extract_french_title_from_request(request) == "Breaking Bad"

    def test_returns_none_when_no_french_title_for_movie(self) -> None:
        """Should return None if no French title available for movie."""
        request = {
            "media": {
                "mediaType": "movie",
                "title": "The Matrix",
                "tmdbId": 603,
            }
        }
        assert extract_french_title_from_request(request) is None

    def test_returns_none_when_no_french_title_for_tv(self) -> None:
        """Should return None if no French title available for TV."""
        request = {
            "media": {
                "mediaType": "tv",
                "name": "Breaking Bad",
                "tmdbId": 1396,
            }
        }
        assert extract_french_title_from_request(request) is None

    def test_returns_none_for_empty_media(self) -> None:
        """Should return None if media object is empty."""
        request = {"media": {}}
        assert extract_french_title_from_request(request) is None

    def test_returns_none_for_empty_request(self) -> None:
        """Should return None for empty request."""
        assert extract_french_title_from_request({}) is None

    def test_title_fr_takes_precedence_over_name_fr(self) -> None:
        """'title_fr' should take precedence over 'name_fr' (for edge cases)."""
        request = {
            "media": {
                "title_fr": "Titre Français",
                "name_fr": "Nom Français",
            }
        }
        assert extract_french_title_from_request(request) == "Titre Français"

    def test_handles_non_string_values(self) -> None:
        """Should convert non-string title values to strings."""
        request = {
            "media": {
                "title_fr": 123,  # Numeric title (edge case)
            }
        }
        assert extract_french_title_from_request(request) == "123"


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
    async def test_cached_jellyseerr_request_has_release_date_column(
        self, client: TestClient
    ) -> None:
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
    async def test_cached_jellyseerr_request_has_title_fr_column(self, client: TestClient) -> None:
        """CachedJellyseerrRequest should have title_fr column (US-38.2)."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=125,
                tmdb_id=890,
                media_type="movie",
                status=2,
                title="The Matrix",
                title_fr="Matrix",  # New French title column
                requested_by="TestUser",
                created_at_source="2024-01-01T10:00:00Z",
                raw_data={"full": "request"},
            )
            session.add(request)
            await session.commit()
            assert request.id is not None
            assert request.title == "The Matrix"
            assert request.title_fr == "Matrix"

    @pytest.mark.asyncio
    async def test_cached_jellyseerr_request_title_fr_can_be_null(self, client: TestClient) -> None:
        """CachedJellyseerrRequest.title_fr should allow null values (US-38.2)."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=126,
                tmdb_id=891,
                media_type="movie",
                status=2,
                title="Inception",
                title_fr=None,  # No French title available
                requested_by="TestUser",
                created_at_source="2024-01-01T10:00:00Z",
                raw_data={"full": "request"},
            )
            session.add(request)
            await session.commit()
            assert request.id is not None
            assert request.title == "Inception"
            assert request.title_fr is None

    @pytest.mark.asyncio
    async def test_sync_status_model_exists(self, client: TestClient) -> None:
        """SyncStatus model should track last sync time per user."""
        async with TestingAsyncSessionLocal() as session:
            status = SyncStatus(
                user_id=1,
                last_sync_started=datetime.now(UTC),
                last_sync_completed=datetime.now(UTC),
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

    @patch("app.routers.sync.sync_user")
    def test_trigger_sync_success(self, mock_sync_task: MagicMock, client: TestClient) -> None:
        """POST /api/sync should trigger a sync for authenticated user."""
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
        assert response.json()["status"] == "sync_started"
        # Verify Celery task was dispatched
        mock_sync_task.delay.assert_called_once()

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
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    async def test_run_user_sync_fetches_and_caches_data(
        self,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
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
        mock_jellyfin_users.return_value = []  # No users for nickname prefill
        mock_jellyseerr_users.return_value = []

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
    async def test_run_user_sync_handles_failed_api_calls(self, client: TestClient) -> None:
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
            with patch(
                "app.services.sync.fetch_jellyfin_media_with_progress",
                side_effect=Exception("API Error"),
            ):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    result = await run_user_sync(session, user.id)

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    async def test_sync_clears_old_cache_before_storing_new(
        self,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_jellyfin: AsyncMock,
        client: TestClient,
        mock_jellyfin_response: dict,
    ) -> None:
        """Sync should replace old cached data with new data."""
        from sqlalchemy import select

        from app.services.sync import run_user_sync

        mock_jellyfin.return_value = mock_jellyfin_response["Items"]
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

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

    @patch("app.routers.sync.sync_user")
    def test_sync_rate_limited_after_recent_sync(
        self, mock_sync_task: MagicMock, client: TestClient
    ) -> None:
        """POST /api/sync should return 429 if user synced within 5 minutes."""
        token = self._get_auth_token(client, "ratelimit1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # First sync should succeed (this updates DB sync status via update_sync_status)
        response1 = client.post("/api/sync", headers=headers)
        assert response1.status_code == 200

        # Second sync immediately after should be rate limited
        response2 = client.post("/api/sync", headers=headers)
        assert response2.status_code == 429
        assert (
            "rate" in response2.json()["detail"].lower()
            or "minute" in response2.json()["detail"].lower()
        )

    @patch("app.routers.sync.sync_user")
    @patch("app.routers.sync.get_sync_status")
    def test_sync_allowed_after_5_minutes(
        self, mock_get_status: AsyncMock, mock_sync_task: MagicMock, client: TestClient
    ) -> None:
        """POST /api/sync should succeed if last sync was >5 minutes ago."""
        from datetime import timedelta

        # Mock that last sync was 6 minutes ago
        old_sync_time = datetime.now(UTC) - timedelta(minutes=6)
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

    @patch("app.routers.sync.sync_user")
    def test_sync_rate_limit_response_includes_wait_time(
        self, mock_sync_task: MagicMock, client: TestClient
    ) -> None:
        """Rate limit response should include how long to wait."""
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

    @patch("app.routers.sync.sync_user")
    def test_rate_limit_is_per_user(self, mock_sync_task: MagicMock, client: TestClient) -> None:
        """Rate limit should be per-user, not global."""
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

    @patch("app.routers.sync.sync_user")
    @patch("app.routers.sync.get_sync_status")
    def test_force_bypasses_rate_limit_for_first_sync(
        self, mock_get_status: AsyncMock, mock_sync_task: MagicMock, client: TestClient
    ) -> None:
        """POST /api/sync with force=true should bypass rate limit for first sync (US-18.2)."""
        # Mock a sync status that was just started but never completed (first sync)
        from datetime import timedelta

        recent_sync_time = datetime.now(UTC) - timedelta(seconds=30)
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

    @patch("app.routers.sync.sync_user")
    @patch("app.routers.sync.get_sync_status")
    def test_force_does_not_bypass_rate_limit_for_subsequent_syncs(
        self, mock_get_status: AsyncMock, mock_sync_task: MagicMock, client: TestClient
    ) -> None:
        """POST /api/sync with force=true should NOT bypass rate limit if already synced before."""
        from datetime import timedelta

        # Mock a sync status where sync has COMPLETED (not first sync)
        recent_sync_time = datetime.now(UTC) - timedelta(seconds=30)
        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=recent_sync_time,
            last_sync_completed=recent_sync_time,  # Completed = not first sync
            last_sync_status="success",
        )
        mock_get_status.return_value = mock_status

        token = self._get_auth_token(client, "force2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Configure Jellyfin
        with patch("app.routers.settings.validate_jellyfin_connection", return_value=True):
            client.post(
                "/api/settings/jellyfin",
                json={"server_url": "http://jellyfin.local", "api_key": "test-key"},
                headers=headers,
            )

        # Sync with force=true should still be rate limited since user has synced before
        response = client.post(
            "/api/sync",
            json={"force": True},
            headers=headers,
        )
        assert response.status_code == 429


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
        import httpx

        from app.services.sync import fetch_jellyfin_users

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
                "UserData": {
                    "Played": True,
                    "PlayCount": 2,
                    "LastPlayedDate": "2024-01-10T10:00:00Z",
                },
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
                last_sync_started=datetime.now(UTC),
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
    async def test_update_sync_progress_updates_progress_fields(self, client: TestClient) -> None:
        """update_sync_progress should update only progress fields."""
        from app.services.sync import get_sync_status, update_sync_progress, update_sync_status

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="progress_test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create initial sync status
            await update_sync_status(
                session,
                user.id,
                "in_progress",
                started=True,
                current_step="syncing_media",
                total_steps=2,
            )

            # Update progress
            await update_sync_progress(
                session,
                user.id,
                current_step_progress=5,
                current_step_total=10,
                current_user_name="TestUser",
            )

            # Verify progress was updated
            status = await get_sync_status(session, user.id)
            assert status is not None
            assert status.current_step == "syncing_media"  # Unchanged
            assert status.current_step_progress == 5
            assert status.current_step_total == 10
            assert status.current_user_name == "TestUser"

    @pytest.mark.asyncio
    async def test_sync_completion_clears_progress_fields(self, client: TestClient) -> None:
        """When sync completes, progress fields should be cleared."""
        from app.services.sync import get_sync_status, update_sync_progress, update_sync_status

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="progress_clear@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Start sync with progress
            await update_sync_status(
                session,
                user.id,
                "in_progress",
                started=True,
                current_step="syncing_media",
                total_steps=2,
            )
            await update_sync_progress(
                session,
                user.id,
                current_step_progress=5,
                current_step_total=10,
                current_user_name="TestUser",
            )

            # Complete sync
            await update_sync_status(
                session, user.id, "success", media_count=100, requests_count=50
            )

            # Verify progress fields were cleared
            status = await get_sync_status(session, user.id)
            assert status is not None
            assert status.current_step is None
            assert status.total_steps is None
            assert status.current_step_progress is None
            assert status.current_step_total is None
            assert status.current_user_name is None

    def test_sync_status_returns_progress_when_syncing(self, client: TestClient) -> None:
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
            last_sync_started=datetime.now(UTC),
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
    async def test_calculate_season_sizes_updates_series_only(self, client: TestClient) -> None:
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
                if "series-456" in str(parent_id) or (
                    "Items" in str(url) and "Season" in str(params.get("IncludeItemTypes", ""))
                ):
                    if parent_id == "series-456":
                        return httpx.Response(
                            200, json=mock_seasons_response, request=httpx.Request("GET", url)
                        )
                # Episodes for season1
                if parent_id == "season1":
                    return httpx.Response(
                        200, json=mock_episodes_s1, request=httpx.Request("GET", url)
                    )
                # Episodes for season2
                if parent_id == "season2":
                    return httpx.Response(
                        200, json=mock_episodes_s2, request=httpx.Request("GET", url)
                    )
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            # Mock Jellyfin users (needed for episode watch data aggregation)
            mock_jellyfin_users = [
                {"Id": "user1", "Name": "Test User"},
            ]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    with patch(
                        "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                    ):
                        await calculate_season_sizes(
                            session, user.id, "http://jellyfin.local", "decrypted-key"
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

            # Series should also have total size (S1: 10 GB + S2: 15 GB = 25 GB)
            assert items["Test Series"].size_bytes == 25_000_000_000

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_stores_total_series_size(
        self, client: TestClient
    ) -> None:
        """calculate_season_sizes should store total series size in size_bytes."""
        from app.services.sync import calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            # Create a user with settings
            user = User(
                email="total_series_size@example.com",
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

            # Add a series with no initial size
            series = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="series-total-test",
                name="Test Series Total",
                media_type="Series",
                size_bytes=None,  # Initially unknown
            )
            session.add(series)
            await session.commit()

            # Mock API: 3 seasons with different sizes
            mock_seasons_response = {
                "Items": [
                    {"Id": "season1", "Name": "Season 1"},
                    {"Id": "season2", "Name": "Season 2"},
                    {"Id": "season3", "Name": "Season 3"},
                ]
            }
            # Season 1: 5 GB, Season 2: 10 GB, Season 3: 8 GB
            mock_episodes_by_season = {
                "season1": {
                    "Items": [
                        {"Id": "ep1", "MediaSources": [{"Size": 2_500_000_000}]},
                        {"Id": "ep2", "MediaSources": [{"Size": 2_500_000_000}]},
                    ]
                },  # 5 GB total
                "season2": {
                    "Items": [
                        {"Id": "ep3", "MediaSources": [{"Size": 5_000_000_000}]},
                        {"Id": "ep4", "MediaSources": [{"Size": 5_000_000_000}]},
                    ]
                },  # 10 GB total
                "season3": {
                    "Items": [
                        {"Id": "ep5", "MediaSources": [{"Size": 4_000_000_000}]},
                        {"Id": "ep6", "MediaSources": [{"Size": 4_000_000_000}]},
                    ]
                },  # 8 GB total
            }

            async def mock_get(self, url, **kwargs):
                import httpx

                params = kwargs.get("params", {})
                parent_id = params.get("ParentId", "")

                if parent_id == "series-total-test":
                    return httpx.Response(
                        200, json=mock_seasons_response, request=httpx.Request("GET", url)
                    )
                if parent_id in mock_episodes_by_season:
                    return httpx.Response(
                        200,
                        json=mock_episodes_by_season[parent_id],
                        request=httpx.Request("GET", url),
                    )
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            # Mock Jellyfin users (needed for episode watch data aggregation)
            mock_jellyfin_users = [
                {"Id": "user1", "Name": "Test User"},
            ]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                    with patch(
                        "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                    ):
                        await calculate_season_sizes(
                            session, user.id, "http://jellyfin.local", "decrypted-key"
                        )

            # Refresh from DB
            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            series_item = result.scalars().first()

            # Total series size should be 5 + 10 + 8 = 23 GB
            assert series_item.size_bytes == 23_000_000_000
            # Largest season should be Season 2 at 10 GB
            assert series_item.largest_season_size_bytes == 10_000_000_000

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_handles_api_errors(self, client: TestClient) -> None:
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
                    return httpx.Response(
                        200,
                        json={"Items": [{"Id": "s1-season1", "IndexNumber": 1}]},
                        request=httpx.Request("GET", url),
                    )
                elif parent_id == "s1-season1":
                    return httpx.Response(
                        200,
                        json={"Items": [{"Id": "ep1", "MediaSources": [{"Size": 5_000_000_000}]}]},
                        request=httpx.Request("GET", url),
                    )
                # Second series call fails
                elif parent_id == "series-2":
                    raise httpx.RequestError("Connection failed")

                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            # Mock Jellyfin users (needed for episode watch data aggregation)
            mock_jellyfin_users = [
                {"Id": "user1", "Name": "Test User"},
            ]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch(
                    "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                ):
                    # Should not raise, just log warning and continue
                    await calculate_season_sizes(
                        session, user.id, "http://jellyfin.local", "api-key"
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
    async def test_calculate_season_sizes_handles_empty_series(self, client: TestClient) -> None:
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
                await calculate_season_sizes(session, user.id, "http://jellyfin.local", "api-key")

            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            items = result.scalars().all()

            # Series with no seasons should have None
            assert items[0].largest_season_size_bytes is None

    @pytest.mark.asyncio
    async def test_fetch_season_episodes_uses_recursive_parameter(self, client: TestClient) -> None:
        """fetch_season_episodes should include Recursive=true to find episodes in nested folders.

        Regression test: Without Recursive=true, Jellyfin API returns empty episodes
        for many series where episodes are stored in subdirectories.
        """
        import httpx

        from app.services.sync import fetch_season_episodes

        captured_params: dict[str, str] = {}

        async def mock_get(url, **kwargs):
            # Capture the params from the request
            params = kwargs.get("params", {})
            captured_params.update(params)
            return httpx.Response(
                200,
                json={
                    "Items": [{"Id": "ep1", "Name": "Episode 1", "MediaSources": [{"Size": 1000}]}]
                },
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as real_client:
            with patch.object(real_client, "get", side_effect=mock_get):
                await fetch_season_episodes(
                    real_client,
                    "http://jellyfin.local",
                    "test-api-key",
                    "season-123",
                )

        # Verify Recursive parameter is included
        assert (
            "Recursive" in captured_params
        ), "Recursive parameter is required to find episodes in nested folders"
        assert captured_params["Recursive"] == "true"
        assert captured_params["ParentId"] == "season-123"
        assert captured_params["IncludeItemTypes"] == "Episode"
        assert captured_params["Fields"] == "MediaSources,UserData"

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
                await calculate_season_sizes(session, user.id, "http://jellyfin.local", "api-key")

            # Should have log message about calculating sizes
            assert any(
                "Calculating season sizes for 2 series" in record.message
                for record in caplog.records
            )

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

    @pytest.mark.asyncio
    async def test_calculate_season_sizes_optimized_api_calls(self, client: TestClient) -> None:
        """Optimization (US-59.4): Episode data should be fetched once and reused.

        The current unoptimized approach with 3 users and 2 seasons makes:
        - 1 season fetch (for size calc)
        - 2 episode fetches per season for size
        - 2 seasons * 3 users = 6 episode fetches for watch data
        - 1 season fetch (for language check)
        - 2 episode fetches for language check
        Total old: 1 + 2 + 6 + 1 + 2 = 12 calls

        The optimized approach should make:
        - 1 season fetch (reused for size + language)
        - 2 episode fetches (reused for size + language + watch aggregation)
        - 3 batched user episode fetches (1 per user, using series parent ID)
        Total new: 1 + 2 + 3 = 6 calls

        This test verifies we don't fetch episodes more than once per season
        for size/language, and that user watch data is batched per user.
        """
        from app.services.sync import calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="api_calls_test@example.com",
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

            series = CachedMediaItem(
                user_id=user.id,
                jellyfin_id="series-opt-test",
                name="Test Series Optimized",
                media_type="Series",
            )
            session.add(series)
            await session.commit()

            # Track API calls
            api_calls: list[str] = []

            mock_seasons_response = {
                "Items": [
                    {"Id": "season1", "Name": "Season 1"},
                    {"Id": "season2", "Name": "Season 2"},
                ]
            }
            # Episodes with MediaSources for size and MediaStreams for language check
            mock_episodes_response = {
                "Items": [
                    {
                        "Id": "ep1",
                        "ParentIndexNumber": 1,
                        "IndexNumber": 1,
                        "MediaSources": [
                            {
                                "Size": 1_000_000_000,
                                "MediaStreams": [
                                    {"Type": "Audio", "Language": "eng"},
                                    {"Type": "Audio", "Language": "fre"},
                                ],
                            }
                        ],
                        "UserData": {"LastPlayedDate": "2024-01-15T10:00:00Z"},
                    },
                ]
            }

            async def mock_get(self, url, **kwargs):
                params = kwargs.get("params", {})
                parent_id = params.get("ParentId", "")
                include_types = params.get("IncludeItemTypes", "")
                user_id = params.get("UserId", "none")
                api_calls.append(f"{include_types}|{parent_id}|{user_id}")

                if include_types == "Season":
                    return httpx.Response(
                        200, json=mock_seasons_response, request=httpx.Request("GET", url)
                    )
                if include_types == "Episode":
                    return httpx.Response(
                        200, json=mock_episodes_response, request=httpx.Request("GET", url)
                    )
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            # 3 Jellyfin users to test batched episode fetch
            mock_jellyfin_users = [
                {"Id": "jf_user1", "Name": "User 1"},
                {"Id": "jf_user2", "Name": "User 2"},
                {"Id": "jf_user3", "Name": "User 3"},
            ]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch(
                    "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                ):
                    await calculate_season_sizes(
                        session, user.id, "http://jellyfin.local", "decrypted-key"
                    )

            # Count different types of calls
            season_calls = [c for c in api_calls if "Season" in c]
            episode_calls_for_size = [c for c in api_calls if "Episode" in c and "|none" in c]
            episode_calls_for_users = [c for c in api_calls if "Episode" in c and "jf_user" in c]

            # Should have exactly 1 season fetch (not 2 - reused for language check)
            assert len(season_calls) == 1, (
                f"Expected 1 season fetch (reused for language), got {len(season_calls)}: "
                f"{season_calls}"
            )

            # Should have exactly 2 episode fetches for size/language (one per season)
            assert len(episode_calls_for_size) == 2, (
                f"Expected 2 episode fetches for size/language, got {len(episode_calls_for_size)}: "
                f"{episode_calls_for_size}"
            )

            # With optimization: 3 batched fetches (one per user for ALL episodes)
            # not 6 (2 seasons * 3 users)
            assert len(episode_calls_for_users) == 3, (
                f"Expected 3 batched user episode fetches (1 per user), got "
                f"{len(episode_calls_for_users)}: {episode_calls_for_users}"
            )


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
    async def test_sync_status_includes_calculating_sizes_step(self, client: TestClient) -> None:
        """Sync status should show calculating_sizes step after main sync."""
        async with TestingAsyncSessionLocal() as session:
            status = SyncStatus(
                user_id=999,
                last_sync_started=datetime.now(UTC),
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
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    async def test_sync_triggers_calculate_season_sizes_after_media_sync(
        self,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
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
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

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

    def test_sync_status_returns_calculating_sizes_in_progress(self, client: TestClient) -> None:
        """GET /api/sync/status should include calculating_sizes step."""
        token = self._get_auth_token(client, "calcsize1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        mock_status = SyncStatus(
            user_id=1,
            last_sync_started=datetime.now(UTC),
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
        from unittest.mock import patch

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
        from unittest.mock import patch

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
                            with patch("app.services.sync.fetch_jellyfin_users", return_value=[]):
                                with patch(
                                    "app.services.sync.fetch_jellyseerr_users", return_value=[]
                                ):
                                    with patch(
                                        "app.services.sync.send_sync_failure_notification"
                                    ) as mock_notify:
                                        result = await run_user_sync(session, user.id)

                                        # Sync partial (Jellyfin OK, Jellyseerr failed)
                                        assert result["status"] == "partial"
                                        assert "Jellyseerr" in result["error"]

                                        # Notification called for Jellyseerr failure
                                        mock_notify.assert_called_once()
                                        call_kwargs = mock_notify.call_args[1]
                                        assert (
                                            call_kwargs["user_email"]
                                            == "js_fail_notify@example.com"
                                        )
                                        assert call_kwargs["service"] == "Jellyseerr"
                                        assert (
                                            "Jellyseerr API error" in call_kwargs["error_message"]
                                        )

    @pytest.mark.asyncio
    async def test_sync_failure_notification_is_fire_and_forget(self, client: TestClient) -> None:
        """Notification failure should not affect sync error handling."""
        from unittest.mock import patch

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
    async def test_sync_failure_notification_without_webhook_configured(
        self, client: TestClient
    ) -> None:
        """Sync failure should work when Slack webhook is not configured."""
        from unittest.mock import patch

        from app.services.sync import run_user_sync

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
    async def test_sync_failure_notification_uses_block_kit_format(
        self, client: TestClient
    ) -> None:
        """Sync failure notification should use Slack Block Kit format."""
        from unittest.mock import AsyncMock, patch

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
                    error_message="Connection timed out",
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
        from unittest.mock import patch

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


class TestSyncRetryWithBackoff:
    """Test retry with exponential backoff on transient API failures (US-26.1)."""

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_jellyfin_users_retries_on_timeout(self, mock_sleep: AsyncMock) -> None:
        """fetch_jellyfin_users should retry on timeout errors."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Connection timed out")
            response = httpx.Response(200, json=[{"Id": "user1", "Name": "John"}])
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert len(users) == 1
        assert call_count == 3  # Failed twice, succeeded on third
        assert mock_sleep.call_count == 2  # Slept twice before retries

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_jellyfin_users_retries_on_500_error(self, mock_sleep: AsyncMock) -> None:
        """fetch_jellyfin_users should retry on 500 server errors."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Return 500 error
                request = httpx.Request("GET", args[1] if len(args) > 1 else "http://example.com")
                response = httpx.Response(500, request=request)

                def raise_error():
                    raise httpx.HTTPStatusError("Server error", request=request, response=response)

                response.raise_for_status = raise_error
                return response
            # Success on second attempt
            response = httpx.Response(200, json=[{"Id": "user1", "Name": "John"}])
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert len(users) == 1
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_jellyfin_users_does_not_retry_on_401(self) -> None:
        """fetch_jellyfin_users should NOT retry on 401 auth errors."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            request = httpx.Request("GET", "http://jellyfin.local/Users")
            response = httpx.Response(401, request=request)

            def raise_error():
                raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

            response.raise_for_status = raise_error
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert exc_info.value.response.status_code == 401
        assert call_count == 1  # Only one call - no retry

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_jellyfin_users_fails_after_max_retries(
        self, mock_sleep: AsyncMock
    ) -> None:
        """fetch_jellyfin_users should fail after 4 total attempts (1 + 3 retries)."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Persistent timeout")

        with patch("httpx.AsyncClient.get", new=mock_get):
            with pytest.raises(httpx.TimeoutException):
                await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert call_count == 4  # 1 initial + 3 retries
        assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_jellyseerr_requests_retries_on_transient_error(
        self, mock_sleep: AsyncMock
    ) -> None:
        """fetch_jellyseerr_requests should retry on transient errors."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        request_call_count = 0

        async def mock_get(self_or_url, url_or_headers=None, **kwargs):
            nonlocal request_call_count
            # Handle both (self, url, ...) and (url, ...) signatures
            url = (
                url_or_headers
                if url_or_headers and isinstance(url_or_headers, str)
                else str(self_or_url)
            )
            # Only count calls to /api/v1/request (not media detail fetches)
            if "/api/v1/request" in url:
                request_call_count += 1
                if request_call_count == 1:
                    raise httpx.ConnectError("Connection refused")
                # Success on second attempt
                response = httpx.Response(
                    200,
                    json={
                        "results": [{"id": 1, "media": {"tmdbId": 123, "mediaType": "movie"}}],
                        "pageInfo": {"pages": 1},
                    },
                )
                response.raise_for_status = lambda: None
                return response
            else:
                # Media detail calls - return empty (optional enrichment)
                response = httpx.Response(200, json={"title": "Test Movie"})
                response.raise_for_status = lambda: None
                return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            requests = await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        assert len(requests) == 1
        assert request_call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_exponential_backoff_delays_1_2_4_seconds(self, mock_sleep: AsyncMock) -> None:
        """Retry delays should follow exponential backoff: 1s, 2s, 4s."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise httpx.TimeoutException("Timeout")
            response = httpx.Response(200, json=[{"Id": "user1", "Name": "John"}])
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        assert mock_sleep.call_count == 3
        # Verify exponential backoff: 1, 2, 4 seconds
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @pytest.mark.asyncio
    @patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock)
    async def test_successful_retry_continues_sync_normally(self, mock_sleep: AsyncMock) -> None:
        """After successful retry, sync should continue normally (no partial state)."""
        import httpx

        from app.services.sync import fetch_jellyfin_users

        call_count = 0
        expected_users = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
        ]

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("First attempt failed")
            response = httpx.Response(200, json=expected_users)
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyfin_users("http://jellyfin.local", "api-key")

        # Should have complete data after retry
        assert len(users) == 2
        assert users[0]["Name"] == "John"
        assert users[1]["Name"] == "Jane"


class TestFetchMediaDetailsWithLanguage:
    """Test fetch_media_details with language parameter (US-38.2)."""

    @pytest.mark.asyncio
    async def test_fetch_media_details_uses_language_parameter(self) -> None:
        """fetch_media_details should pass language to API."""
        import httpx

        from app.services.sync import fetch_media_details

        captured_params: dict = {}

        async def mock_get(self, url, **kwargs):
            nonlocal captured_params
            captured_params = kwargs.get("params", {})
            response = httpx.Response(200, json={"title": "Test Movie"})
            return response

        async with httpx.AsyncClient() as client:
            with patch.object(
                client, "get", new=lambda url, **kwargs: mock_get(None, url, **kwargs)
            ):
                await fetch_media_details(
                    client, "http://jellyseerr.local", "api-key", 123, "movie", language="fr"
                )

        assert captured_params.get("language") == "fr"

    @pytest.mark.asyncio
    async def test_fetch_media_details_default_language_is_english(self) -> None:
        """fetch_media_details should default to English language."""
        import httpx

        from app.services.sync import fetch_media_details

        captured_params: dict = {}

        async def mock_get(self, url, **kwargs):
            nonlocal captured_params
            captured_params = kwargs.get("params", {})
            response = httpx.Response(200, json={"title": "Test Movie"})
            return response

        async with httpx.AsyncClient() as client:
            with patch.object(
                client, "get", new=lambda url, **kwargs: mock_get(None, url, **kwargs)
            ):
                await fetch_media_details(
                    client, "http://jellyseerr.local", "api-key", 123, "movie"
                )

        assert captured_params.get("language") == "en"

    @pytest.mark.asyncio
    async def test_fetch_media_details_returns_french_title_when_requested(self) -> None:
        """fetch_media_details should return French title when language=fr."""
        import httpx

        from app.services.sync import fetch_media_details

        async def mock_get(self, url, **kwargs):
            params = kwargs.get("params", {})
            if params.get("language") == "fr":
                return httpx.Response(200, json={"title": "Matrix"})  # French title
            return httpx.Response(200, json={"title": "The Matrix"})  # English title

        async with httpx.AsyncClient() as client:
            with patch.object(
                client, "get", new=lambda url, **kwargs: mock_get(None, url, **kwargs)
            ):
                result_en = await fetch_media_details(
                    client, "http://jellyseerr.local", "api-key", 123, "movie", language="en"
                )
                result_fr = await fetch_media_details(
                    client, "http://jellyseerr.local", "api-key", 123, "movie", language="fr"
                )

        assert result_en.get("title") == "The Matrix"
        assert result_fr.get("title") == "Matrix"

    @pytest.mark.asyncio
    async def test_fetch_media_details_handles_missing_french_title(self) -> None:
        """fetch_media_details should handle cases where French title is unavailable."""
        import httpx

        from app.services.sync import fetch_media_details

        async def mock_get(self, url, **kwargs):
            # Return 404 when French title not available
            return httpx.Response(404)

        async with httpx.AsyncClient() as client:
            with patch.object(
                client, "get", new=lambda url, **kwargs: mock_get(None, url, **kwargs)
            ):
                result = await fetch_media_details(
                    client, "http://jellyseerr.local", "api-key", 123, "movie", language="fr"
                )

        # Should return empty dict on failure
        assert result == {}


class TestGetMostRecentEpisodePlayedDate:
    """Tests for get_most_recent_episode_played_date function."""

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None when no episodes provided."""
        from app.services.sync import get_most_recent_episode_played_date

        result = get_most_recent_episode_played_date([])
        assert result is None

    def test_returns_none_when_no_episodes_watched(self) -> None:
        """Should return None when no episodes have been watched."""
        from app.services.sync import get_most_recent_episode_played_date

        episodes = [
            {"Id": "ep1", "UserData": {"Played": False, "LastPlayedDate": None}},
            {"Id": "ep2", "UserData": {"Played": False, "LastPlayedDate": None}},
            {"Id": "ep3", "UserData": {}},
        ]

        result = get_most_recent_episode_played_date(episodes)
        assert result is None

    def test_returns_single_date_when_one_episode_watched(self) -> None:
        """Should return the date when only one episode has been watched."""
        from app.services.sync import get_most_recent_episode_played_date

        episodes = [
            {"Id": "ep1", "UserData": {"Played": False, "LastPlayedDate": None}},
            {"Id": "ep2", "UserData": {"Played": True, "LastPlayedDate": "2025-01-15T10:00:00Z"}},
            {"Id": "ep3", "UserData": {"Played": False, "LastPlayedDate": None}},
        ]

        result = get_most_recent_episode_played_date(episodes)
        assert result == "2025-01-15T10:00:00Z"

    def test_returns_most_recent_date_across_episodes(self) -> None:
        """Should return the most recent LastPlayedDate across all episodes."""
        from app.services.sync import get_most_recent_episode_played_date

        episodes = [
            {"Id": "ep1", "UserData": {"Played": True, "LastPlayedDate": "2025-01-10T10:00:00Z"}},
            {"Id": "ep2", "UserData": {"Played": True, "LastPlayedDate": "2025-01-20T15:30:00Z"}},
            {"Id": "ep3", "UserData": {"Played": True, "LastPlayedDate": "2025-01-15T08:00:00Z"}},
        ]

        result = get_most_recent_episode_played_date(episodes)
        assert result == "2025-01-20T15:30:00Z"

    def test_handles_missing_user_data(self) -> None:
        """Should handle episodes without UserData gracefully."""
        from app.services.sync import get_most_recent_episode_played_date

        episodes = [
            {"Id": "ep1"},  # No UserData at all
            {"Id": "ep2", "UserData": {"Played": True, "LastPlayedDate": "2025-01-15T10:00:00Z"}},
            {"Id": "ep3", "UserData": {}},  # Empty UserData
        ]

        result = get_most_recent_episode_played_date(episodes)
        assert result == "2025-01-15T10:00:00Z"

    def test_handles_mixed_watched_and_unwatched_episodes(self) -> None:
        """Should correctly handle a mix of watched and unwatched episodes."""
        from app.services.sync import get_most_recent_episode_played_date

        episodes = [
            {"Id": "ep1", "UserData": {"Played": False, "LastPlayedDate": None}},
            {"Id": "ep2", "UserData": {"Played": True, "LastPlayedDate": "2025-01-05T10:00:00Z"}},
            {"Id": "ep3", "UserData": {"Played": False, "LastPlayedDate": None}},
            {"Id": "ep4", "UserData": {"Played": True, "LastPlayedDate": "2025-01-25T18:00:00Z"}},
            {"Id": "ep5", "UserData": {"Played": True, "LastPlayedDate": "2025-01-10T12:00:00Z"}},
        ]

        result = get_most_recent_episode_played_date(episodes)
        assert result == "2025-01-25T18:00:00Z"


class TestFetchJellyseerrSeasonEpisodes:
    """Test fetching episode details from Jellyseerr API (US-51.1)."""

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_success(self) -> None:
        """Should fetch episode details from Jellyseerr API."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        mock_response = {
            "episodes": [
                {"episodeNumber": 1, "name": "Pilot", "airDate": "2024-01-15"},
                {"episodeNumber": 2, "name": "Second Episode", "airDate": "2024-01-22"},
                {"episodeNumber": 3, "name": "Third Episode", "airDate": "2024-01-29"},
            ]
        }

        captured_url: str = ""
        captured_headers: dict[str, str] = {}

        async def mock_get(url, **kwargs):
            nonlocal captured_url, captured_headers
            captured_url = url
            captured_headers = kwargs.get("headers", {})
            return httpx.Response(
                200,
                json=mock_response,
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        # Verify API call was correct
        assert "/api/v1/tv/12345/season/1" in captured_url
        assert captured_headers.get("X-Api-Key") == "test-api-key"

        # Verify result format
        assert len(result) == 3
        assert result[0] == {"episodeNumber": 1, "name": "Pilot", "airDate": "2024-01-15"}
        assert result[1] == {"episodeNumber": 2, "name": "Second Episode", "airDate": "2024-01-22"}
        assert result[2] == {"episodeNumber": 3, "name": "Third Episode", "airDate": "2024-01-29"}

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_api_error_returns_empty_list(self) -> None:
        """Should return empty list on API error (graceful failure)."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        async def mock_get(url, **kwargs):
            return httpx.Response(
                500,
                json={"error": "Internal Server Error"},
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        # Should return empty list, not raise exception
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_connection_error_returns_empty_list(
        self,
    ) -> None:
        """Should return empty list on connection error (graceful failure)."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        async def mock_get(url, **kwargs):
            raise httpx.RequestError("Connection refused")

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_timeout_returns_empty_list(self) -> None:
        """Should return empty list on timeout (graceful failure)."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        async def mock_get(url, **kwargs):
            raise httpx.TimeoutException("Request timed out")

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_empty_episodes_array(self) -> None:
        """Should handle empty episodes array from API."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200,
                json={"episodes": []},
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_missing_episodes_key(self) -> None:
        """Should handle missing 'episodes' key in response."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200,
                json={"name": "Season 1", "seasonNumber": 1},  # No 'episodes' key
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_extracts_required_fields(self) -> None:
        """Should extract only required fields from episode data."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        # Full Jellyseerr episode response with extra fields
        mock_response = {
            "episodes": [
                {
                    "episodeNumber": 1,
                    "name": "Pilot",
                    "airDate": "2024-01-15",
                    "overview": "The first episode...",  # Extra field
                    "runtime": 45,  # Extra field
                    "stillPath": "/path/to/still.jpg",  # Extra field
                },
            ]
        }

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200,
                json=mock_response,
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        # Should only contain the required fields
        assert len(result) == 1
        assert result[0] == {"episodeNumber": 1, "name": "Pilot", "airDate": "2024-01-15"}

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_season_episodes_handles_null_air_date(self) -> None:
        """Should handle episodes with null airDate (unannounced)."""
        import httpx

        from app.services.sync import fetch_jellyseerr_season_episodes

        mock_response = {
            "episodes": [
                {"episodeNumber": 1, "name": "Episode 1", "airDate": "2024-01-15"},
                {"episodeNumber": 2, "name": "Episode 2", "airDate": None},  # Unannounced
            ]
        }

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200,
                json=mock_response,
                request=httpx.Request("GET", url),
            )

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await fetch_jellyseerr_season_episodes(
                    client,
                    "http://jellyseerr.local",
                    "test-api-key",
                    tmdb_id=12345,
                    season_number=1,
                )

        # Should include episode with null airDate
        assert len(result) == 2
        assert result[1]["airDate"] is None


class TestFetchJellyseerrRequestsWithEpisodes:
    """Test integration of episode fetching into fetch_jellyseerr_requests (US-51.1)."""

    @pytest.mark.asyncio
    async def test_fetches_episodes_for_status_4_tv_shows(self) -> None:
        """Should fetch episode details for partially available (status 4) TV shows."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        # Mock requests list with one status 4 TV show
        mock_requests_response = {
            "results": [
                {
                    "id": 1,
                    "status": 2,  # Request status (approved)
                    "media": {
                        "tmdbId": 12345,
                        "mediaType": "tv",
                        "status": 4,  # Media status = partially available
                        "seasons": [
                            {"seasonNumber": 1, "status": 5},  # Available
                            {"seasonNumber": 2, "status": 4},  # Partially available
                        ],
                    },
                    "requestedBy": {"displayName": "TestUser"},
                },
            ],
            "pageInfo": {"pages": 1},
        }

        # Mock media details (English and French)
        mock_tv_details_en = {"name": "Breaking Bad", "firstAirDate": "2008-01-20"}
        mock_tv_details_fr = {"name": "Breaking Bad"}

        # Mock season episodes
        mock_season_1_episodes = {
            "episodes": [
                {"episodeNumber": 1, "name": "Pilot", "airDate": "2008-01-20"},
                {"episodeNumber": 2, "name": "Cat's in the Bag...", "airDate": "2008-01-27"},
            ]
        }
        mock_season_2_episodes = {
            "episodes": [
                {"episodeNumber": 1, "name": "Seven Thirty-Seven", "airDate": "2009-03-08"},
                {"episodeNumber": 2, "name": "Grilled", "airDate": "2009-03-15"},
                {"episodeNumber": 3, "name": "Bit by a Dead Bee", "airDate": "2009-03-22"},
            ]
        }

        call_log: list[str] = []

        async def mock_get(self, url, **kwargs):
            call_log.append(url)

            # Pagination endpoint
            if "/api/v1/request" in url:
                return httpx.Response(
                    200, json=mock_requests_response, request=httpx.Request("GET", url)
                )
            # Media details - English
            elif "/api/v1/tv/12345" in url and "language=en" in str(kwargs.get("params", {})):
                return httpx.Response(
                    200, json=mock_tv_details_en, request=httpx.Request("GET", url)
                )
            # Media details - French
            elif "/api/v1/tv/12345" in url and "language=fr" in str(kwargs.get("params", {})):
                return httpx.Response(
                    200, json=mock_tv_details_fr, request=httpx.Request("GET", url)
                )
            # Season 1 episodes
            elif "/api/v1/tv/12345/season/1" in url:
                return httpx.Response(
                    200, json=mock_season_1_episodes, request=httpx.Request("GET", url)
                )
            # Season 2 episodes
            elif "/api/v1/tv/12345/season/2" in url:
                return httpx.Response(
                    200, json=mock_season_2_episodes, request=httpx.Request("GET", url)
                )

            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("httpx.AsyncClient.get", new=mock_get):
            requests = await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        # Verify season episode calls were made
        season_calls = [c for c in call_log if "/season/" in c]
        assert len(season_calls) == 2  # Both seasons should be fetched

        # Verify episodes are stored in the raw_data
        assert len(requests) == 1
        media = requests[0].get("media", {})
        seasons = media.get("seasons", [])

        # Season 1 should have episodes
        season_1 = next(s for s in seasons if s["seasonNumber"] == 1)
        assert "episodes" in season_1
        assert len(season_1["episodes"]) == 2
        assert season_1["episodes"][0] == {
            "episodeNumber": 1,
            "name": "Pilot",
            "airDate": "2008-01-20",
        }

        # Season 2 should have episodes
        season_2 = next(s for s in seasons if s["seasonNumber"] == 2)
        assert "episodes" in season_2
        assert len(season_2["episodes"]) == 3

    @pytest.mark.asyncio
    async def test_skips_episode_fetch_for_status_5_tv_shows(self) -> None:
        """Should NOT fetch episodes for fully available (status 5) TV shows."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        mock_requests_response = {
            "results": [
                {
                    "id": 1,
                    "status": 2,
                    "media": {
                        "tmdbId": 11111,
                        "mediaType": "tv",
                        "status": 5,  # Fully available - should skip episode fetch
                        "seasons": [
                            {"seasonNumber": 1, "status": 5},
                            {"seasonNumber": 2, "status": 5},
                        ],
                    },
                    "requestedBy": {"displayName": "TestUser"},
                },
            ],
            "pageInfo": {"pages": 1},
        }

        mock_tv_details = {"name": "Complete Show", "firstAirDate": "2020-01-01"}

        call_log: list[str] = []

        async def mock_get(self, url, **kwargs):
            call_log.append(url)

            if "/api/v1/request" in url:
                return httpx.Response(
                    200, json=mock_requests_response, request=httpx.Request("GET", url)
                )
            elif "/api/v1/tv/11111" in url:
                return httpx.Response(200, json=mock_tv_details, request=httpx.Request("GET", url))

            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("httpx.AsyncClient.get", new=mock_get):
            await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        # Verify NO season episode calls were made
        season_calls = [c for c in call_log if "/season/" in c]
        assert len(season_calls) == 0

    @pytest.mark.asyncio
    async def test_skips_episode_fetch_for_movies(self) -> None:
        """Should NOT fetch episodes for movies."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        mock_requests_response = {
            "results": [
                {
                    "id": 1,
                    "status": 2,
                    "media": {
                        "tmdbId": 22222,
                        "mediaType": "movie",
                        "status": 4,  # Even with status 4, movies don't have episodes
                    },
                    "requestedBy": {"displayName": "TestUser"},
                },
            ],
            "pageInfo": {"pages": 1},
        }

        mock_movie_details = {"title": "Test Movie", "releaseDate": "2024-01-15"}

        call_log: list[str] = []

        async def mock_get(self, url, **kwargs):
            call_log.append(url)

            if "/api/v1/request" in url:
                return httpx.Response(
                    200, json=mock_requests_response, request=httpx.Request("GET", url)
                )
            elif "/api/v1/movie/22222" in url:
                return httpx.Response(
                    200, json=mock_movie_details, request=httpx.Request("GET", url)
                )

            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("httpx.AsyncClient.get", new=mock_get):
            await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        # Verify NO season episode calls were made
        season_calls = [c for c in call_log if "/season/" in c]
        assert len(season_calls) == 0

    @pytest.mark.asyncio
    async def test_handles_episode_fetch_failure_gracefully(self) -> None:
        """Should continue processing when episode fetch fails for a season."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        mock_requests_response = {
            "results": [
                {
                    "id": 1,
                    "status": 2,
                    "media": {
                        "tmdbId": 33333,
                        "mediaType": "tv",
                        "status": 4,
                        "seasons": [
                            {"seasonNumber": 1, "status": 5},
                            {"seasonNumber": 2, "status": 4},  # This fetch will fail
                        ],
                    },
                    "requestedBy": {"displayName": "TestUser"},
                },
            ],
            "pageInfo": {"pages": 1},
        }

        mock_tv_details = {"name": "Show with Error", "firstAirDate": "2020-01-01"}
        mock_season_1_episodes = {
            "episodes": [{"episodeNumber": 1, "name": "Pilot", "airDate": "2020-01-15"}]
        }

        async def mock_get(self, url, **kwargs):
            if "/api/v1/request" in url:
                return httpx.Response(
                    200, json=mock_requests_response, request=httpx.Request("GET", url)
                )
            elif "/api/v1/tv/33333" in url and "/season/" not in url:
                return httpx.Response(200, json=mock_tv_details, request=httpx.Request("GET", url))
            elif "/api/v1/tv/33333/season/1" in url:
                return httpx.Response(
                    200, json=mock_season_1_episodes, request=httpx.Request("GET", url)
                )
            elif "/api/v1/tv/33333/season/2" in url:
                # Simulate API error
                raise httpx.RequestError("Connection failed")

            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("httpx.AsyncClient.get", new=mock_get):
            requests = await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        # Should return the request without failing
        assert len(requests) == 1
        seasons = requests[0]["media"]["seasons"]

        # Season 1 should have episodes
        season_1 = next(s for s in seasons if s["seasonNumber"] == 1)
        assert "episodes" in season_1
        assert len(season_1["episodes"]) == 1

        # Season 2 should have empty episodes list (fetch failed)
        season_2 = next(s for s in seasons if s["seasonNumber"] == 2)
        assert season_2.get("episodes", []) == []

    @pytest.mark.asyncio
    async def test_skips_special_seasons(self) -> None:
        """Should skip fetching episodes for season 0 (specials)."""
        import httpx

        from app.services.sync import fetch_jellyseerr_requests

        mock_requests_response = {
            "results": [
                {
                    "id": 1,
                    "status": 2,
                    "media": {
                        "tmdbId": 44444,
                        "mediaType": "tv",
                        "status": 4,
                        "seasons": [
                            {"seasonNumber": 0, "status": 5},  # Specials - should skip
                            {"seasonNumber": 1, "status": 5},
                        ],
                    },
                    "requestedBy": {"displayName": "TestUser"},
                },
            ],
            "pageInfo": {"pages": 1},
        }

        mock_tv_details = {"name": "Show with Specials", "firstAirDate": "2020-01-01"}
        mock_season_1_episodes = {
            "episodes": [{"episodeNumber": 1, "name": "Pilot", "airDate": "2020-01-15"}]
        }

        call_log: list[str] = []

        async def mock_get(self, url, **kwargs):
            call_log.append(url)

            if "/api/v1/request" in url:
                return httpx.Response(
                    200, json=mock_requests_response, request=httpx.Request("GET", url)
                )
            elif "/api/v1/tv/44444" in url and "/season/" not in url:
                return httpx.Response(200, json=mock_tv_details, request=httpx.Request("GET", url))
            elif "/api/v1/tv/44444/season/1" in url:
                return httpx.Response(
                    200, json=mock_season_1_episodes, request=httpx.Request("GET", url)
                )

            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("httpx.AsyncClient.get", new=mock_get):
            await fetch_jellyseerr_requests("http://jellyseerr.local", "api-key")

        # Verify only season 1 was fetched (not season 0)
        season_calls = [c for c in call_log if "/season/" in c]
        assert len(season_calls) == 1
        assert "/season/1" in season_calls[0]
        assert "/season/0" not in str(season_calls)


class TestCheckEpisodeAudioLanguages:
    """Test episode audio language checking (US-52.1)."""

    def test_check_episode_with_english_and_french_audio(self) -> None:
        """Episode with both EN and FR audio should return both languages present."""
        from app.services.sync import check_episode_audio_languages

        episode = {
            "Id": "episode-123",
            "Name": "Test Episode",
            "MediaSources": [
                {
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "eng"},
                        {"Type": "Audio", "Language": "fre"},
                        {"Type": "Subtitle", "Language": "fre"},
                    ]
                }
            ],
        }

        result = check_episode_audio_languages(episode)

        assert result["has_english"] is True
        assert result["has_french"] is True
        assert result["has_french_subs"] is True
        assert result["missing_languages"] == []

    def test_check_episode_missing_english_audio(self) -> None:
        """Episode missing EN audio should report missing_en_audio."""
        from app.services.sync import check_episode_audio_languages

        episode = {
            "Id": "episode-123",
            "Name": "French Only Episode",
            "MediaSources": [
                {
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "fre"},
                    ]
                }
            ],
        }

        result = check_episode_audio_languages(episode)

        assert result["has_english"] is False
        assert result["has_french"] is True
        assert "missing_en_audio" in result["missing_languages"]

    def test_check_episode_missing_french_audio(self) -> None:
        """Episode missing FR audio should report missing_fr_audio."""
        from app.services.sync import check_episode_audio_languages

        episode = {
            "Id": "episode-123",
            "Name": "English Only Episode",
            "MediaSources": [
                {
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "eng"},
                    ]
                }
            ],
        }

        result = check_episode_audio_languages(episode)

        assert result["has_english"] is True
        assert result["has_french"] is False
        assert "missing_fr_audio" in result["missing_languages"]

    def test_check_episode_no_media_sources_returns_empty_result(self) -> None:
        """Episode without MediaSources should return empty result (no issues flagged)."""
        from app.services.sync import check_episode_audio_languages

        episode = {
            "Id": "episode-123",
            "Name": "No Sources Episode",
        }

        result = check_episode_audio_languages(episode)

        # When we can't check, assume no issues
        assert result["has_english"] is True
        assert result["has_french"] is True
        assert result["missing_languages"] == []

    def test_check_episode_handles_language_code_variants(self) -> None:
        """Should recognize language code variants (fra, en, fr, english, french)."""
        from app.services.sync import check_episode_audio_languages

        episode = {
            "Id": "episode-123",
            "Name": "Variant Codes Episode",
            "MediaSources": [
                {
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "english"},  # Full word
                        {"Type": "Audio", "Language": "fra"},  # Alternate French code
                    ]
                }
            ],
        }

        result = check_episode_audio_languages(episode)

        assert result["has_english"] is True
        assert result["has_french"] is True


class TestCheckSeriesEpisodesLanguages:
    """Test series episodes language checking (US-52.1)."""

    @pytest.mark.asyncio
    async def test_check_series_episodes_returns_aggregated_result(self) -> None:
        """Should aggregate language check results across all episodes."""
        import httpx

        from app.services.sync import check_series_episodes_languages

        # Mock episode responses - some with issues, some without
        mock_seasons_response = {"Items": [{"Id": "season1"}]}
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep1",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "Name": "Episode 1",
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                {"Type": "Audio", "Language": "fre"},
                            ]
                        }
                    ],
                },
                {
                    "Id": "ep2",
                    "IndexNumber": 2,
                    "ParentIndexNumber": 1,
                    "Name": "Episode 2",
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                # Missing French audio
                            ]
                        }
                    ],
                },
            ]
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "test-api-key",
                    series_id="series-123",
                    series_name="Test Series",
                )

        # Aggregated result: EN in all, but FR missing in at least one
        assert result["language_check_result"]["has_english"] is True
        assert result["language_check_result"]["has_french"] is False
        assert result["problematic_episodes"] is not None
        assert len(result["problematic_episodes"]) == 1
        assert result["problematic_episodes"][0]["episode"] == 2

    @pytest.mark.asyncio
    async def test_check_series_all_episodes_have_both_languages(self) -> None:
        """Series with all episodes having both languages should have empty problematic_episodes."""
        import httpx

        from app.services.sync import check_series_episodes_languages

        mock_seasons_response = {"Items": [{"Id": "season1"}]}
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep1",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "Name": "Episode 1",
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                {"Type": "Audio", "Language": "fre"},
                            ]
                        }
                    ],
                },
            ]
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "test-api-key",
                    series_id="series-123",
                    series_name="Test Series",
                )

        assert result["language_check_result"]["has_english"] is True
        assert result["language_check_result"]["has_french"] is True
        assert result["problematic_episodes"] == []

    @pytest.mark.asyncio
    async def test_check_series_no_seasons_returns_empty_result(self) -> None:
        """Series with no seasons should return empty result."""
        import httpx

        from app.services.sync import check_series_episodes_languages

        async def mock_get(url, **kwargs):
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "test-api-key",
                    series_id="series-123",
                    series_name="Test Series",
                )

        assert result["language_check_result"]["has_english"] is True
        assert result["language_check_result"]["has_french"] is True
        assert result["problematic_episodes"] == []

    @pytest.mark.asyncio
    async def test_problematic_episodes_include_correct_metadata(self) -> None:
        """Problematic episodes should include identifier, name, season, episode."""
        import httpx

        from app.services.sync import check_series_episodes_languages

        mock_seasons_response = {"Items": [{"Id": "season2"}]}
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep5",
                    "IndexNumber": 5,
                    "ParentIndexNumber": 2,
                    "Name": "The Big Reveal",
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "fre"},  # Missing English
                            ]
                        }
                    ],
                },
            ]
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        async with httpx.AsyncClient() as client:
            with patch.object(client, "get", side_effect=mock_get):
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "test-api-key",
                    series_id="series-123",
                    series_name="Test Series",
                )

        assert len(result["problematic_episodes"]) == 1
        ep = result["problematic_episodes"][0]
        assert ep["identifier"] == "S02E05"
        assert ep["name"] == "The Big Reveal"
        assert ep["season"] == 2
        assert ep["episode"] == 5
        assert "missing_en_audio" in ep["missing_languages"]


class TestCacheMediaItemLanguageFields:
    """Test caching language check results in CachedMediaItem (US-52.1)."""

    @pytest.mark.asyncio
    async def test_movie_language_check_stored_in_cache(self) -> None:
        """Movies should have language_check_result populated from raw_data.MediaSources."""
        from app.services.sync import cache_media_items

        async with TestingAsyncSessionLocal() as session:
            # Create user
            user = User(email="movielang@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            # Movie with MediaSources (will be checked during cache)
            movie_item = {
                "Id": "movie-123",
                "Name": "Test Movie",
                "Type": "Movie",
                "UserData": {"Played": False, "PlayCount": 0},
                "MediaSources": [
                    {
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "eng"},
                            {"Type": "Audio", "Language": "fre"},
                            {"Type": "Subtitle", "Language": "fre"},
                        ]
                    }
                ],
            }

            await cache_media_items(session, user.id, [movie_item])

            # Verify cached item has language_check_result
            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            cached = result.scalar_one()

            assert cached.language_check_result is not None
            assert cached.language_check_result["has_english"] is True
            assert cached.language_check_result["has_french"] is True
            assert cached.language_check_result["has_french_subs"] is True

    @pytest.mark.asyncio
    async def test_movie_missing_audio_stored_in_language_check_result(self) -> None:
        """Movies missing audio tracks should have issues recorded."""
        from app.services.sync import cache_media_items

        async with TestingAsyncSessionLocal() as session:
            user = User(email="movielang2@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            # Movie missing French audio
            movie_item = {
                "Id": "movie-456",
                "Name": "English Only Movie",
                "Type": "Movie",
                "UserData": {"Played": False, "PlayCount": 0},
                "MediaSources": [
                    {
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "eng"},
                        ]
                    }
                ],
            }

            await cache_media_items(session, user.id, [movie_item])

            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            cached = result.scalar_one()

            assert cached.language_check_result is not None
            assert cached.language_check_result["has_english"] is True
            assert cached.language_check_result["has_french"] is False
            assert "missing_fr_audio" in cached.language_check_result["missing_languages"]

    @pytest.mark.asyncio
    async def test_series_language_check_stored_after_season_calculation(self) -> None:
        """Series should have language_check_result populated after calculate_season_sizes."""
        from app.services.sync import cache_media_items, calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            user = User(email="serieslang@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)

            # Series item (language check happens during calculate_season_sizes)
            series_item = {
                "Id": "series-123",
                "Name": "Test Series",
                "Type": "Series",
                "UserData": {"Played": False, "PlayCount": 0},
            }

            await cache_media_items(session, user.id, [series_item])

            # Mock API calls for season/episode data
            import httpx

            mock_seasons_response = {"Items": [{"Id": "season1"}]}
            mock_episodes_response = {
                "Items": [
                    {
                        "Id": "ep1",
                        "IndexNumber": 1,
                        "ParentIndexNumber": 1,
                        "Name": "Episode 1",
                        "MediaSources": [
                            {
                                "Size": 1_000_000_000,
                                "MediaStreams": [
                                    {"Type": "Audio", "Language": "eng"},
                                    {"Type": "Audio", "Language": "fre"},
                                ],
                            }
                        ],
                        "UserData": {},
                    },
                ]
            }

            async def mock_get(self, url, **kwargs):
                params = kwargs.get("params", {})
                include_types = params.get("IncludeItemTypes", "")

                if "Season" in include_types:
                    return httpx.Response(
                        200, json=mock_seasons_response, request=httpx.Request("GET", url)
                    )
                elif "Episode" in include_types:
                    return httpx.Response(
                        200, json=mock_episodes_response, request=httpx.Request("GET", url)
                    )
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            mock_jellyfin_users = [{"Id": "user1", "Name": "Test User"}]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch(
                    "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                ):
                    await calculate_season_sizes(
                        session, user.id, "http://jellyfin.local", "decrypted-key"
                    )

            # Verify cached series has language_check_result
            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            cached = result.scalar_one()

            assert cached.language_check_result is not None
            assert cached.language_check_result["has_english"] is True
            assert cached.language_check_result["has_french"] is True
            assert cached.problematic_episodes == []

    @pytest.mark.asyncio
    async def test_series_with_problematic_episodes_stored(self) -> None:
        """Series with episodes missing audio should have problematic_episodes populated."""
        from app.services.sync import cache_media_items, calculate_season_sizes

        async with TestingAsyncSessionLocal() as session:
            user = User(email="serieslang2@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)

            series_item = {
                "Id": "series-456",
                "Name": "Partially French Series",
                "Type": "Series",
                "UserData": {"Played": False, "PlayCount": 0},
            }

            await cache_media_items(session, user.id, [series_item])

            import httpx

            mock_seasons_response = {"Items": [{"Id": "season1"}]}
            mock_episodes_response = {
                "Items": [
                    {
                        "Id": "ep1",
                        "IndexNumber": 1,
                        "ParentIndexNumber": 1,
                        "Name": "Good Episode",
                        "MediaSources": [
                            {
                                "Size": 1_000_000_000,
                                "MediaStreams": [
                                    {"Type": "Audio", "Language": "eng"},
                                    {"Type": "Audio", "Language": "fre"},
                                ],
                            }
                        ],
                        "UserData": {},
                    },
                    {
                        "Id": "ep2",
                        "IndexNumber": 2,
                        "ParentIndexNumber": 1,
                        "Name": "Bad Episode",
                        "MediaSources": [
                            {
                                "Size": 1_000_000_000,
                                "MediaStreams": [
                                    {"Type": "Audio", "Language": "eng"},
                                    # Missing French
                                ],
                            }
                        ],
                        "UserData": {},
                    },
                ]
            }

            async def mock_get(self, url, **kwargs):
                params = kwargs.get("params", {})
                include_types = params.get("IncludeItemTypes", "")

                if "Season" in include_types:
                    return httpx.Response(
                        200, json=mock_seasons_response, request=httpx.Request("GET", url)
                    )
                elif "Episode" in include_types:
                    return httpx.Response(
                        200, json=mock_episodes_response, request=httpx.Request("GET", url)
                    )
                return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

            mock_jellyfin_users = [{"Id": "user1", "Name": "Test User"}]

            with patch("httpx.AsyncClient.get", new=mock_get):
                with patch(
                    "app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users
                ):
                    await calculate_season_sizes(
                        session, user.id, "http://jellyfin.local", "decrypted-key"
                    )

            from sqlalchemy import select

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == user.id)
            )
            cached = result.scalar_one()

            assert cached.language_check_result is not None
            assert cached.language_check_result["has_french"] is False
            assert len(cached.problematic_episodes) == 1
            assert cached.problematic_episodes[0]["identifier"] == "S01E02"
            assert cached.problematic_episodes[0]["name"] == "Bad Episode"


class TestCheckSeriesEpisodesLanguagesWithExemptions:
    """Tests for check_series_episodes_languages with exempt episodes (US-52.3)."""

    @pytest.mark.asyncio
    async def test_exempt_episodes_are_skipped(self) -> None:
        """Episodes in exempt set should be skipped from language checking."""
        from app.services.sync import check_series_episodes_languages

        mock_seasons_response = {
            "Items": [
                {"Id": "season-1", "IndexNumber": 1},
            ]
        }

        # Two episodes - one with missing French (S01E05), one OK (S01E01)
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep-1",
                    "Name": "Good Episode",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                {"Type": "Audio", "Language": "fre"},
                            ]
                        }
                    ],
                    "UserData": {},
                },
                {
                    "Id": "ep-5",
                    "Name": "Bad Episode",
                    "IndexNumber": 5,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                # Missing French!
                            ]
                        }
                    ],
                    "UserData": {},
                },
            ]
        }

        async def mock_get(self, url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        # Without exemption - episode should appear as problematic
        with patch("httpx.AsyncClient.get", new=mock_get):
            async with httpx.AsyncClient() as client:
                result = await check_series_episodes_languages(
                    client, "http://jellyfin.local", "api-key", "series-123", "Test Series"
                )
                # Without exemption, S01E05 should be problematic
                assert len(result["problematic_episodes"]) == 1
                assert result["problematic_episodes"][0]["identifier"] == "S01E05"
                assert result["language_check_result"]["has_french"] is False

        # With exemption for S01E05 - episode should be skipped
        exempt_episodes = {("series-123", 1, 5)}
        with patch("httpx.AsyncClient.get", new=mock_get):
            async with httpx.AsyncClient() as client:
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "api-key",
                    "series-123",
                    "Test Series",
                    exempt_episodes=exempt_episodes,
                )
                # With exemption, S01E05 should be skipped - no problematic episodes
                assert len(result["problematic_episodes"]) == 0
                # The series should show as having all languages (since only the good ep is checked)
                assert result["language_check_result"]["has_french"] is True
                assert result["language_check_result"]["has_english"] is True

    @pytest.mark.asyncio
    async def test_exempt_only_affects_specified_episode(self) -> None:
        """Exemption for one episode should not affect other episodes."""
        from app.services.sync import check_series_episodes_languages

        mock_seasons_response = {
            "Items": [
                {"Id": "season-1", "IndexNumber": 1},
            ]
        }

        # Three episodes - two with missing French (S01E02, S01E03), one OK (S01E01)
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep-1",
                    "Name": "Good Episode",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                {"Type": "Audio", "Language": "fre"},
                            ]
                        }
                    ],
                    "UserData": {},
                },
                {
                    "Id": "ep-2",
                    "Name": "Bad Episode 2",
                    "IndexNumber": 2,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                # Missing French!
                            ]
                        }
                    ],
                    "UserData": {},
                },
                {
                    "Id": "ep-3",
                    "Name": "Bad Episode 3",
                    "IndexNumber": 3,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                # Missing French!
                            ]
                        }
                    ],
                    "UserData": {},
                },
            ]
        }

        async def mock_get(self, url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        # Exempt only S01E02
        exempt_episodes = {("series-456", 1, 2)}
        with patch("httpx.AsyncClient.get", new=mock_get):
            async with httpx.AsyncClient() as client:
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "api-key",
                    "series-456",
                    "Test Series",
                    exempt_episodes=exempt_episodes,
                )
                # S01E02 exempted, S01E03 should still be problematic
                assert len(result["problematic_episodes"]) == 1
                assert result["problematic_episodes"][0]["identifier"] == "S01E03"
                # Series still has French issues (from S01E03)
                assert result["language_check_result"]["has_french"] is False

    @pytest.mark.asyncio
    async def test_exempt_different_series_id_does_not_affect(self) -> None:
        """Exemption for a different series ID should not affect this series."""
        from app.services.sync import check_series_episodes_languages

        mock_seasons_response = {"Items": [{"Id": "season-1", "IndexNumber": 1}]}
        mock_episodes_response = {
            "Items": [
                {
                    "Id": "ep-1",
                    "Name": "Bad Episode",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "MediaSources": [
                        {
                            "MediaStreams": [
                                {"Type": "Audio", "Language": "eng"},
                                # Missing French!
                            ]
                        }
                    ],
                    "UserData": {},
                },
            ]
        }

        async def mock_get(self, url, **kwargs):
            params = kwargs.get("params", {})
            include_types = params.get("IncludeItemTypes", "")

            if "Season" in include_types:
                return httpx.Response(
                    200, json=mock_seasons_response, request=httpx.Request("GET", url)
                )
            elif "Episode" in include_types:
                return httpx.Response(
                    200, json=mock_episodes_response, request=httpx.Request("GET", url)
                )
            return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

        # Exempt S01E01 but for a DIFFERENT series
        exempt_episodes = {("different-series", 1, 1)}
        with patch("httpx.AsyncClient.get", new=mock_get):
            async with httpx.AsyncClient() as client:
                result = await check_series_episodes_languages(
                    client,
                    "http://jellyfin.local",
                    "api-key",
                    "series-789",
                    "Test Series",
                    exempt_episodes=exempt_episodes,
                )
                # Exemption is for different series, so S01E01 should still be problematic
                assert len(result["problematic_episodes"]) == 1
                assert result["problematic_episodes"][0]["identifier"] == "S01E01"


class TestSonarrHistoryIntegration:
    """Tests for Sonarr history integration during sync (US-63.1)."""

    @pytest.mark.asyncio
    async def test_cache_jellyseerr_requests_with_sonarr_history(self) -> None:
        """Should store sonarr_history in raw_data for TV requests."""
        from app.services.sync import cache_jellyseerr_requests

        async with TestingAsyncSessionLocal() as session:
            # Create a test user
            user = User(
                email="test@example.com",
                hashed_password="hashed",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Jellyseerr requests data (TV show with TMDB ID 12345)
            requests_data = [
                {
                    "id": 1,
                    "status": 4,  # Partially available
                    "media": {
                        "id": 100,
                        "tmdbId": 12345,
                        "mediaType": "tv",
                        "name": "Breaking Bad",
                    },
                    "requestedBy": {"displayName": "john"},
                },
                {
                    "id": 2,
                    "status": 2,  # Pending
                    "media": {
                        "id": 101,
                        "tmdbId": 67890,
                        "mediaType": "movie",
                        "title": "Inception",
                    },
                    "requestedBy": {"displayName": "jane"},
                },
            ]

            # Sonarr history for TMDB ID 12345
            sonarr_history = {
                12345: [
                    {
                        "season": 2,
                        "episode": 5,
                        "title": "Breakage",
                        "added_at": "2026-01-15T10:30:00Z",
                    },
                    {
                        "season": 2,
                        "episode": 6,
                        "title": "Peekaboo",
                        "added_at": "2026-01-15T10:30:00Z",
                    },
                ],
            }

            # Cache with Sonarr history
            count = await cache_jellyseerr_requests(
                session, user.id, requests_data, sonarr_history=sonarr_history
            )
            assert count == 2

            # Verify the TV show has sonarr_history in raw_data
            from sqlalchemy import select

            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 12345,
                )
            )
            cached_tv = result.scalar_one()
            assert cached_tv.raw_data is not None
            assert "sonarr_history" in cached_tv.raw_data
            assert len(cached_tv.raw_data["sonarr_history"]) == 2
            assert cached_tv.raw_data["sonarr_history"][0]["season"] == 2
            assert cached_tv.raw_data["sonarr_history"][0]["episode"] == 5

            # Verify the movie does NOT have sonarr_history (it's not a TV show)
            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 67890,
                )
            )
            cached_movie = result.scalar_one()
            assert cached_movie.raw_data is not None
            assert "sonarr_history" not in cached_movie.raw_data

    @pytest.mark.asyncio
    async def test_cache_jellyseerr_requests_without_sonarr_history(self) -> None:
        """Should work without sonarr_history (graceful degradation)."""
        from app.services.sync import cache_jellyseerr_requests

        async with TestingAsyncSessionLocal() as session:
            # Create a test user
            user = User(
                email="test2@example.com",
                hashed_password="hashed",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Jellyseerr requests data
            requests_data = [
                {
                    "id": 1,
                    "status": 4,
                    "media": {
                        "id": 100,
                        "tmdbId": 12345,
                        "mediaType": "tv",
                        "name": "Breaking Bad",
                    },
                    "requestedBy": {"displayName": "john"},
                },
            ]

            # Cache without Sonarr history
            count = await cache_jellyseerr_requests(session, user.id, requests_data)
            assert count == 1

            # Verify the request is cached but without sonarr_history
            from sqlalchemy import select

            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 12345,
                )
            )
            cached_tv = result.scalar_one()
            assert cached_tv.raw_data is not None
            # raw_data contains original request but no sonarr_history
            assert "sonarr_history" not in cached_tv.raw_data

    @pytest.mark.asyncio
    async def test_cache_jellyseerr_requests_empty_sonarr_history(self) -> None:
        """Should handle empty sonarr_history dict."""
        from app.services.sync import cache_jellyseerr_requests

        async with TestingAsyncSessionLocal() as session:
            # Create a test user
            user = User(
                email="test3@example.com",
                hashed_password="hashed",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Jellyseerr requests data
            requests_data = [
                {
                    "id": 1,
                    "status": 4,
                    "media": {
                        "id": 100,
                        "tmdbId": 12345,
                        "mediaType": "tv",
                        "name": "Breaking Bad",
                    },
                    "requestedBy": {"displayName": "john"},
                },
            ]

            # Cache with empty Sonarr history
            count = await cache_jellyseerr_requests(
                session, user.id, requests_data, sonarr_history={}
            )
            assert count == 1

            # Verify request is cached without sonarr_history (no matching TMDB ID)
            from sqlalchemy import select

            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 12345,
                )
            )
            cached_tv = result.scalar_one()
            assert cached_tv.raw_data is not None
            assert "sonarr_history" not in cached_tv.raw_data

    @pytest.mark.asyncio
    async def test_sonarr_history_only_for_matching_tmdb_ids(self) -> None:
        """Should only add sonarr_history for requests with matching TMDB IDs."""
        from app.services.sync import cache_jellyseerr_requests

        async with TestingAsyncSessionLocal() as session:
            # Create a test user
            user = User(
                email="test4@example.com",
                hashed_password="hashed",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Multiple TV shows
            requests_data = [
                {
                    "id": 1,
                    "status": 4,
                    "media": {
                        "id": 100,
                        "tmdbId": 12345,
                        "mediaType": "tv",
                        "name": "Breaking Bad",
                    },
                    "requestedBy": {"displayName": "john"},
                },
                {
                    "id": 2,
                    "status": 4,
                    "media": {
                        "id": 101,
                        "tmdbId": 99999,
                        "mediaType": "tv",
                        "name": "Game of Thrones",
                    },
                    "requestedBy": {"displayName": "jane"},
                },
            ]

            # Sonarr history only for TMDB ID 12345
            sonarr_history = {
                12345: [
                    {
                        "season": 1,
                        "episode": 1,
                        "title": "Pilot",
                        "added_at": "2026-01-15T10:30:00Z",
                    },
                ],
            }

            count = await cache_jellyseerr_requests(
                session, user.id, requests_data, sonarr_history=sonarr_history
            )
            assert count == 2

            # Verify Breaking Bad has sonarr_history
            from sqlalchemy import select

            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 12345,
                )
            )
            cached_bb = result.scalar_one()
            assert "sonarr_history" in cached_bb.raw_data

            # Verify Game of Thrones does NOT have sonarr_history
            result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user.id,
                    CachedJellyseerrRequest.tmdb_id == 99999,
                )
            )
            cached_got = result.scalar_one()
            assert "sonarr_history" not in cached_got.raw_data
