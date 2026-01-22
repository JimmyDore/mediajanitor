"""Tests for content deletion endpoints (US-15.4, US-15.5, US-15.6)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TestingAsyncSessionLocal


class TestDeleteMovie:
    """Tests for DELETE /api/content/movie/{tmdb_id} endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "delete_movie@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        return login_response.json()["access_token"]

    def _setup_radarr_settings(
        self, client: TestClient, token: str, mock_validate: AsyncMock
    ) -> None:
        """Helper to configure Radarr settings for a user."""
        mock_validate.return_value = True
        client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_delete_movie_requires_auth(self, client: TestClient) -> None:
        """Test that deleting a movie requires authentication."""
        response = client.delete("/api/content/movie/12345")
        assert response.status_code == 401

    def test_delete_movie_requires_radarr_config(self, client: TestClient) -> None:
        """Test that deleting a movie requires Radarr to be configured."""
        token = self._get_auth_token(client)

        response = client.delete(
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "radarr" in response.json()["detail"].lower()

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    def test_delete_movie_success(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test successful movie deletion from Radarr."""
        mock_delete.return_value = (True, "Movie deleted successfully from Radarr")
        token = self._get_auth_token(client)
        self._setup_radarr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    def test_delete_movie_not_found(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test movie deletion when movie not found in Radarr."""
        mock_delete.return_value = (False, "Movie with TMDB ID 12345 not found in Radarr")
        token = self._get_auth_token(client, "delete_movie_404@example.com")
        self._setup_radarr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["arr_deleted"] is False
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_with_jellyseerr_request(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test movie deletion that also deletes Jellyseerr media entry."""
        from app.database import CachedJellyseerrRequest
        from tests.conftest import TestingAsyncSessionLocal

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_media.return_value = (True, "Media deleted successfully from Jellyseerr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "delete_movie_with_media@example.com")

        # Get user ID for creating cached request
        user_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_id = user_response.json()["id"]

        # Setup Radarr
        client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
                "api_key": "radarr-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Setup Jellyseerr
        client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
                "api_key": "jellyseerr-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached Jellyseerr request with media_id for lookup
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=999,
                jellyseerr_media_id=228,  # Media ID used for deletion
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # TestClient.delete doesn't support json parameter, use request method instead
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True
        # Verify media ID was used (not request ID)
        mock_delete_media.assert_called_once()
        call_args = mock_delete_media.call_args
        assert call_args[0][2] == 228  # media_id, not request_id


class TestDeleteSeries:
    """Tests for DELETE /api/content/series/{tmdb_id} endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "delete_series@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        return login_response.json()["access_token"]

    def _setup_sonarr_settings(
        self, client: TestClient, token: str, mock_validate: AsyncMock
    ) -> None:
        """Helper to configure Sonarr settings for a user."""
        mock_validate.return_value = True
        client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://sonarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_delete_series_requires_auth(self, client: TestClient) -> None:
        """Test that deleting a series requires authentication."""
        response = client.delete("/api/content/series/12345")
        assert response.status_code == 401

    def test_delete_series_requires_sonarr_config(self, client: TestClient) -> None:
        """Test that deleting a series requires Sonarr to be configured."""
        token = self._get_auth_token(client)

        response = client.delete(
            "/api/content/series/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "sonarr" in response.json()["detail"].lower()

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_series_by_tmdb_id", new_callable=AsyncMock)
    def test_delete_series_success(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test successful series deletion from Sonarr."""
        mock_delete.return_value = (True, "Series deleted successfully from Sonarr")
        token = self._get_auth_token(client)
        self._setup_sonarr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/series/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_series_by_tmdb_id", new_callable=AsyncMock)
    def test_delete_series_not_found(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test series deletion when series not found in Sonarr."""
        mock_delete.return_value = (False, "Series with TMDB ID 12345 not found in Sonarr")
        token = self._get_auth_token(client, "delete_series_404@example.com")
        self._setup_sonarr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/series/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["arr_deleted"] is False
        assert "not found" in data["message"].lower()


class TestDeleteRequest:
    """Tests for DELETE /api/content/request/{jellyseerr_id} endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "delete_request@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        return login_response.json()["access_token"]

    def _setup_jellyseerr_settings(
        self, client: TestClient, token: str, mock_validate: AsyncMock
    ) -> None:
        """Helper to configure Jellyseerr settings for a user."""
        mock_validate.return_value = True
        client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_delete_request_requires_auth(self, client: TestClient) -> None:
        """Test that deleting a request requires authentication."""
        response = client.delete("/api/content/request/12345")
        assert response.status_code == 401

    def test_delete_request_requires_jellyseerr_config(self, client: TestClient) -> None:
        """Test that deleting a request requires Jellyseerr to be configured."""
        token = self._get_auth_token(client)

        response = client.delete(
            "/api/content/request/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "jellyseerr" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_request_success(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test successful request deletion from Jellyseerr (via media deletion)."""
        from app.database import CachedJellyseerrRequest
        from tests.conftest import TestingAsyncSessionLocal

        mock_delete.return_value = (True, "Media deleted successfully from Jellyseerr")
        token = self._get_auth_token(client)
        self._setup_jellyseerr_settings(client, token, mock_validate)

        # Get user ID for creating cached request
        user_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        user_id = user_response.json()["id"]

        # Create a cached request with media_id
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=12345,
                jellyseerr_media_id=500,  # Media ID used for deletion
                tmdb_id=99999,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        response = client.delete(
            "/api/content/request/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()
        # Verify media ID was used
        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert call_args[0][2] == 500  # media_id

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_request_not_found(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test request deletion when no media ID found in cache."""
        mock_delete.return_value = (False, "Media not found in Jellyseerr")
        token = self._get_auth_token(client, "delete_request_404@example.com")
        self._setup_jellyseerr_settings(client, token, mock_validate)

        # No cached request exists, so media_id lookup will fail
        response = client.delete(
            "/api/content/request/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "no media found" in response.json()["detail"].lower()


class TestDeleteServiceFunctions:
    """Tests for the service-level delete functions."""

    @pytest.mark.asyncio
    @patch("app.services.radarr.httpx.AsyncClient")
    async def test_get_radarr_movie_by_tmdb_id_success(self, mock_client_class: AsyncMock) -> None:
        """Test finding a Radarr movie by TMDB ID."""
        from unittest.mock import MagicMock

        from app.services.radarr import get_radarr_movie_by_tmdb_id

        # Use MagicMock for non-async methods like json()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 42, "tmdbId": 12345, "title": "Test Movie"}]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await get_radarr_movie_by_tmdb_id("https://radarr.example.com", "api-key", 12345)
        assert result == 42

    @pytest.mark.asyncio
    @patch("app.services.radarr.httpx.AsyncClient")
    async def test_get_radarr_movie_by_tmdb_id_not_found(
        self, mock_client_class: AsyncMock
    ) -> None:
        """Test finding a Radarr movie when not found."""
        from unittest.mock import MagicMock

        from app.services.radarr import get_radarr_movie_by_tmdb_id

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await get_radarr_movie_by_tmdb_id("https://radarr.example.com", "api-key", 99999)
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.radarr.httpx.AsyncClient")
    async def test_delete_radarr_movie_success(self, mock_client_class: AsyncMock) -> None:
        """Test deleting a movie from Radarr."""
        from unittest.mock import MagicMock

        from app.services.radarr import delete_radarr_movie

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await delete_radarr_movie("https://radarr.example.com", "api-key", 42)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.sonarr.httpx.AsyncClient")
    async def test_get_sonarr_series_by_tmdb_id_success(self, mock_client_class: AsyncMock) -> None:
        """Test finding a Sonarr series by TMDB ID."""
        from unittest.mock import MagicMock

        from app.services.sonarr import get_sonarr_series_by_tmdb_id

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 10, "tmdbId": 11111, "title": "Other Show"},
            {"id": 20, "tmdbId": 12345, "title": "Test Show"},
        ]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await get_sonarr_series_by_tmdb_id("https://sonarr.example.com", "api-key", 12345)
        assert result == 20

    @pytest.mark.asyncio
    @patch("app.services.sonarr.httpx.AsyncClient")
    async def test_delete_sonarr_series_success(self, mock_client_class: AsyncMock) -> None:
        """Test deleting a series from Sonarr."""
        from unittest.mock import MagicMock

        from app.services.sonarr import delete_sonarr_series

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await delete_sonarr_series("https://sonarr.example.com", "api-key", 20)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.jellyseerr.httpx.AsyncClient")
    async def test_delete_jellyseerr_request_success(self, mock_client_class: AsyncMock) -> None:
        """Test deleting a request from Jellyseerr."""
        from unittest.mock import MagicMock

        from app.services.jellyseerr import delete_jellyseerr_request

        mock_response = MagicMock()
        mock_response.status_code = 204  # No Content

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        success, message = await delete_jellyseerr_request(
            "https://jellyseerr.example.com", "api-key", 123
        )
        assert success is True
        assert "deleted" in message.lower()

    @pytest.mark.asyncio
    @patch("app.services.jellyseerr.httpx.AsyncClient")
    async def test_delete_jellyseerr_request_not_found(self, mock_client_class: AsyncMock) -> None:
        """Test deleting a request that doesn't exist in Jellyseerr."""
        from unittest.mock import MagicMock

        from app.services.jellyseerr import delete_jellyseerr_request

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.delete.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        success, message = await delete_jellyseerr_request(
            "https://jellyseerr.example.com", "api-key", 999
        )
        assert success is False
        assert "not found" in message.lower()


class TestJellyseerrRequestLookupByTmdbId:
    """Tests for US-15.10: Lookup Jellyseerr request by TMDB ID when deleting content."""

    def _get_auth_token(self, client: TestClient, email: str = "lookup_tmdb@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        return login_response.json()["access_token"]

    def _get_user_id(self, client: TestClient, token: str) -> int:
        """Helper to get user ID from token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_looks_up_jellyseerr_request_by_tmdb_id(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that delete movie looks up Jellyseerr media by TMDB ID."""
        from app.database import CachedJellyseerrRequest

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_media.return_value = (True, "Media deleted successfully from Jellyseerr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "lookup_movie_tmdb@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr and Jellyseerr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached Jellyseerr request for this TMDB ID with media_id
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=999,
                jellyseerr_media_id=555,  # Media ID used for deletion
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # Delete movie - media_id should be looked up by TMDB ID
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True
        # Verify the lookup was used - mock should have been called with media ID 555
        mock_delete_media.assert_called_once()
        call_args = mock_delete_media.call_args
        assert call_args[0][2] == 555  # media_id

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_series_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_series_looks_up_jellyseerr_request_by_tmdb_id(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_series: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_sonarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that delete series looks up Jellyseerr media by TMDB ID."""
        from app.database import CachedJellyseerrRequest

        mock_delete_series.return_value = (True, "Series deleted successfully from Sonarr")
        mock_delete_media.return_value = (True, "Media deleted successfully from Jellyseerr")
        mock_validate_sonarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "lookup_series_tmdb@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Sonarr and Jellyseerr
        client.post(
            "/api/settings/sonarr",
            json={"server_url": "https://sonarr.example.com", "api_key": "sonarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached Jellyseerr request for this TMDB ID with media_id
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=888,
                jellyseerr_media_id=666,  # Media ID used for deletion
                tmdb_id=67890,
                media_type="tv",
                status=1,
                title="Test Series",
            )
            session.add(cached_request)
            await session.commit()

        # Delete series - media_id should be looked up by TMDB ID
        response = client.request(
            "DELETE",
            "/api/content/series/67890",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 67890,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True
        mock_delete_media.assert_called_once()
        call_args = mock_delete_media.call_args
        assert call_args[0][2] == 666  # media_id

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_no_jellyseerr_media_found_skips_gracefully(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that when no matching Jellyseerr media found, deletion skips gracefully."""
        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "lookup_not_found@example.com")

        # Setup Radarr and Jellyseerr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Delete movie with no matching media in cache
        response = client.request(
            "DELETE",
            "/api/content/movie/99999",  # No cached request for this TMDB ID
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 99999,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True  # Still success since movie was deleted
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is False  # No media to delete
        # Delete media should NOT have been called
        mock_delete_media.assert_not_called()
        assert "no media found" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_skips_lookup_when_jellyseerr_unchecked(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that lookup is skipped when delete_from_jellyseerr=false."""
        from app.database import CachedJellyseerrRequest

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "skip_lookup@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached Jellyseerr request
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=777,
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # Delete movie with delete_from_jellyseerr=false
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": False,  # Unchecked - should NOT lookup
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is False
        # Delete media should NOT have been called
        mock_delete_media.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_always_looks_up_media_id(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that media_id is always looked up from cache, regardless of request body params."""
        from app.database import CachedJellyseerrRequest

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_media.return_value = (True, "Media deleted successfully from Jellyseerr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "always_lookup_media@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr and Jellyseerr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached Jellyseerr request with media_id
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=111,
                jellyseerr_media_id=333,  # This is what should be used
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # Delete movie - media_id should be looked up by TMDB ID
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
                # Note: jellyseerr_request_id is ignored - media_id is always looked up
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["jellyseerr_deleted"] is True
        # Should use the cached media_id (333)
        mock_delete_media.assert_called_once()
        call_args = mock_delete_media.call_args
        assert call_args[0][2] == 333

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_series_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_series_handles_multiple_cached_requests_same_tmdb_id(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_series: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_sonarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Regression: delete_series handles multiple requests for same TMDB ID.

        This test verifies the fix for the bug where deleting a series would fail with
        'MultipleResultsFound' when the same TMDB ID had multiple Jellyseerr requests
        (e.g., the same show requested multiple times by different users).
        """
        from app.database import CachedJellyseerrRequest

        mock_delete_series.return_value = (True, "Series deleted successfully from Sonarr")
        mock_delete_media.return_value = (True, "Media deleted successfully from Jellyseerr")
        mock_validate_sonarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "multiple_requests_tmdb@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Sonarr and Jellyseerr
        client.post(
            "/api/settings/sonarr",
            json={"server_url": "https://sonarr.example.com", "api_key": "sonarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create MULTIPLE cached Jellyseerr requests for the same TMDB ID
        # This is the scenario that previously caused MultipleResultsFound error
        async with TestingAsyncSessionLocal() as session:
            # First request for this TMDB ID
            cached_request_1 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=100,
                jellyseerr_media_id=1425,  # All have same media_id since same media
                tmdb_id=1425,
                media_type="tv",
                status=1,
                title="Prison Break",
            )
            # Second request for the same TMDB ID (maybe requested again after deletion)
            cached_request_2 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=101,
                jellyseerr_media_id=1425,  # Same media_id
                tmdb_id=1425,
                media_type="tv",
                status=2,
                title="Prison Break",
            )
            # Third request with the same TMDB ID
            cached_request_3 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=102,
                jellyseerr_media_id=1425,  # Same media_id
                tmdb_id=1425,
                media_type="tv",
                status=1,
                title="Prison Break",
            )
            session.add_all([cached_request_1, cached_request_2, cached_request_3])
            await session.commit()

        # Delete series - should NOT fail with MultipleResultsFound
        response = client.request(
            "DELETE",
            "/api/content/series/1425",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 1425,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
                "jellyseerr_request_id": 59,  # Original request ID (ignored)
            },
        )

        # The key assertion: request should succeed, not 500 error
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True
        # Verify media deletion was called with the correct media_id
        mock_delete_media.assert_called_once()
        call_args = mock_delete_media.call_args
        assert call_args[0][2] == 1425  # media_id


class TestDeleteMovieCachePersistence:
    """Tests for US-49.1: Delete movies from cache after deletion."""

    def _get_auth_token(self, client: TestClient, email: str = "cache_delete@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "SecurePassword123!",
            },
        )
        return login_response.json()["access_token"]

    def _get_user_id(self, client: TestClient, token: str) -> int:
        """Helper to get user ID from token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["id"]

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    async def test_delete_movie_removes_cached_media_item(
        self,
        mock_delete_movie: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that successful Radarr deletion removes CachedMediaItem from DB."""
        from app.database import CachedMediaItem

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_validate_radarr.return_value = True

        token = self._get_auth_token(client, "cache_delete_movie@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create a cached media item with TMDB ID in raw_data
        async with TestingAsyncSessionLocal() as session:
            cached_item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="jellyfin-movie-123",
                name="Test Movie",
                media_type="Movie",
                production_year=2023,
                size_bytes=5000000000,
                raw_data={"ProviderIds": {"Tmdb": "12345", "Imdb": "tt1234567"}},
            )
            session.add(cached_item)
            await session.commit()

        # Verify item exists before deletion
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(CachedMediaItem).where(
                    CachedMediaItem.user_id == user_id,
                    CachedMediaItem.jellyfin_id == "jellyfin-movie-123",
                )
            )
            assert result.scalar_one_or_none() is not None

        # Delete movie via API (no body needed - defaults work)
        response = client.delete(
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True

        # Verify cached item was removed from database
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(CachedMediaItem).where(
                    CachedMediaItem.user_id == user_id,
                    CachedMediaItem.jellyfin_id == "jellyfin-movie-123",
                )
            )
            assert result.scalar_one_or_none() is None, "CachedMediaItem should be deleted"

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    async def test_delete_movie_removes_cached_jellyseerr_request(
        self,
        mock_delete_movie: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that successful Radarr deletion also removes CachedJellyseerrRequest."""
        from app.database import CachedJellyseerrRequest, CachedMediaItem

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_validate_radarr.return_value = True

        token = self._get_auth_token(client, "cache_delete_both@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create cached media item and jellyseerr request with same TMDB ID
        async with TestingAsyncSessionLocal() as session:
            cached_item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="jellyfin-movie-456",
                name="Test Movie 2",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "67890"}},
            )
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=999,
                jellyseerr_media_id=555,
                tmdb_id=67890,
                media_type="movie",
                status=1,
                title="Test Movie 2",
            )
            session.add(cached_item)
            session.add(cached_request)
            await session.commit()

        # Delete movie via API
        response = client.delete(
            "/api/content/movie/67890",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["arr_deleted"] is True

        # Verify both cached items were removed
        async with TestingAsyncSessionLocal() as session:
            media_result = await session.execute(
                select(CachedMediaItem).where(
                    CachedMediaItem.user_id == user_id,
                    CachedMediaItem.jellyfin_id == "jellyfin-movie-456",
                )
            )
            assert media_result.scalar_one_or_none() is None, "CachedMediaItem should be deleted"

            request_result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user_id,
                    CachedJellyseerrRequest.tmdb_id == 67890,
                )
            )
            assert (
                request_result.scalar_one_or_none() is None
            ), "CachedJellyseerrRequest should be deleted"

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    async def test_delete_movie_keeps_cache_on_radarr_failure(
        self,
        mock_delete_movie: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that failed Radarr deletion does NOT remove cached items."""
        from app.database import CachedMediaItem

        mock_delete_movie.return_value = (False, "Movie not found in Radarr")
        mock_validate_radarr.return_value = True

        token = self._get_auth_token(client, "cache_keep_on_fail@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create cached media item
        async with TestingAsyncSessionLocal() as session:
            cached_item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="jellyfin-movie-789",
                name="Test Movie 3",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "11111"}},
            )
            session.add(cached_item)
            await session.commit()

        # Attempt delete (Radarr fails)
        response = client.delete(
            "/api/content/movie/11111",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["arr_deleted"] is False

        # Verify cached item was NOT removed (Radarr deletion failed)
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(CachedMediaItem).where(
                    CachedMediaItem.user_id == user_id,
                    CachedMediaItem.jellyfin_id == "jellyfin-movie-789",
                )
            )
            assert result.scalar_one_or_none() is not None, "CachedMediaItem should NOT be deleted"

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_media", new_callable=AsyncMock)
    async def test_delete_movie_removes_cache_even_if_jellyseerr_fails(
        self,
        mock_delete_media: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that cache is deleted if Radarr succeeds, even if Jellyseerr fails."""
        from app.database import CachedJellyseerrRequest, CachedMediaItem

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_media.return_value = (False, "Jellyseerr API error")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "cache_delete_on_jelly_fail@example.com")
        user_id = self._get_user_id(client, token)

        # Setup Radarr and Jellyseerr
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/jellyseerr",
            json={"server_url": "https://jellyseerr.example.com", "api_key": "jellyseerr-api-key"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create cached items
        async with TestingAsyncSessionLocal() as session:
            cached_item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="jellyfin-movie-999",
                name="Test Movie 4",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "22222"}},
            )
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=888,
                jellyseerr_media_id=777,
                tmdb_id=22222,
                media_type="movie",
                status=1,
                title="Test Movie 4",
            )
            session.add(cached_item)
            session.add(cached_request)
            await session.commit()

        # Delete movie via API (using request to send body with delete_from_jellyseerr)
        response = client.request(
            "DELETE",
            "/api/content/movie/22222",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 22222,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is False

        # Both cache items should still be deleted (Radarr succeeded)
        async with TestingAsyncSessionLocal() as session:
            media_result = await session.execute(
                select(CachedMediaItem).where(
                    CachedMediaItem.user_id == user_id,
                    CachedMediaItem.jellyfin_id == "jellyfin-movie-999",
                )
            )
            assert media_result.scalar_one_or_none() is None, "CachedMediaItem should be deleted"

            request_result = await session.execute(
                select(CachedJellyseerrRequest).where(
                    CachedJellyseerrRequest.user_id == user_id,
                    CachedJellyseerrRequest.tmdb_id == 22222,
                )
            )
            assert (
                request_result.scalar_one_or_none() is None
            ), "CachedJellyseerrRequest should be deleted"
