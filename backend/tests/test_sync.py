"""Tests for data sync functionality (US-7.1)."""

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import User, UserSettings, CachedMediaItem, CachedJellyseerrRequest, SyncStatus
from tests.conftest import TestingAsyncSessionLocal


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
