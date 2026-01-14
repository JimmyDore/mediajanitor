"""Tests for content deletion endpoints (US-15.4, US-15.5, US-15.6)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

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

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    def test_delete_movie_with_jellyseerr_request(
        self,
        mock_delete_request: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test movie deletion that also deletes Jellyseerr request."""
        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_request.return_value = (True, "Request deleted successfully from Jellyseerr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "delete_movie_with_request@example.com")

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

        # TestClient.delete doesn't support json parameter, use request method instead
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
                "jellyseerr_request_id": 999,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True


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

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    def test_delete_request_success(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test successful request deletion from Jellyseerr."""
        mock_delete.return_value = (True, "Request deleted successfully from Jellyseerr")
        token = self._get_auth_token(client)
        self._setup_jellyseerr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/request/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    def test_delete_request_not_found(
        self,
        mock_delete: AsyncMock,
        mock_validate: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test request deletion when request not found in Jellyseerr."""
        mock_delete.return_value = (False, "Request 12345 not found in Jellyseerr")
        token = self._get_auth_token(client, "delete_request_404@example.com")
        self._setup_jellyseerr_settings(client, token, mock_validate)

        response = client.delete(
            "/api/content/request/12345",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


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

        result = await get_radarr_movie_by_tmdb_id(
            "https://radarr.example.com", "api-key", 12345
        )
        assert result == 42

    @pytest.mark.asyncio
    @patch("app.services.radarr.httpx.AsyncClient")
    async def test_get_radarr_movie_by_tmdb_id_not_found(self, mock_client_class: AsyncMock) -> None:
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

        result = await get_radarr_movie_by_tmdb_id(
            "https://radarr.example.com", "api-key", 99999
        )
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

        result = await delete_radarr_movie(
            "https://radarr.example.com", "api-key", 42
        )
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

        result = await get_sonarr_series_by_tmdb_id(
            "https://sonarr.example.com", "api-key", 12345
        )
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

        result = await delete_sonarr_series(
            "https://sonarr.example.com", "api-key", 20
        )
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
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    async def test_delete_movie_looks_up_jellyseerr_request_by_tmdb_id(
        self,
        mock_delete_request: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that delete movie looks up Jellyseerr request by TMDB ID when no request ID provided."""
        from app.database import CachedJellyseerrRequest

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_request.return_value = (True, "Request deleted successfully from Jellyseerr")
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

        # Create a cached Jellyseerr request for this TMDB ID
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=999,
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # Delete movie WITHOUT providing jellyseerr_request_id but WITH delete_from_jellyseerr=true
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
                # Note: NO jellyseerr_request_id provided - should be looked up
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["arr_deleted"] is True
        assert data["jellyseerr_deleted"] is True
        # Verify the lookup was used - mock should have been called with request ID 999
        mock_delete_request.assert_called_once()
        call_args = mock_delete_request.call_args
        # The third positional arg is the jellyseerr_id
        assert call_args[0][2] == 999

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_series_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    async def test_delete_series_looks_up_jellyseerr_request_by_tmdb_id(
        self,
        mock_delete_request: AsyncMock,
        mock_delete_series: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_sonarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that delete series looks up Jellyseerr request by TMDB ID when no request ID provided."""
        from app.database import CachedJellyseerrRequest

        mock_delete_series.return_value = (True, "Series deleted successfully from Sonarr")
        mock_delete_request.return_value = (True, "Request deleted successfully from Jellyseerr")
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

        # Create a cached Jellyseerr request for this TMDB ID
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=888,
                tmdb_id=67890,
                media_type="tv",
                status=1,
                title="Test Series",
            )
            session.add(cached_request)
            await session.commit()

        # Delete series WITHOUT providing jellyseerr_request_id
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
        mock_delete_request.assert_called_once()
        call_args = mock_delete_request.call_args
        assert call_args[0][2] == 888

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    async def test_delete_movie_no_jellyseerr_request_found_skips_gracefully(
        self,
        mock_delete_request: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that when no matching Jellyseerr request found, deletion skips gracefully."""
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

        # Delete movie with no matching request in cache
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
        assert data["jellyseerr_deleted"] is False  # No request to delete
        # Delete request should NOT have been called
        mock_delete_request.assert_not_called()
        assert "no request found" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    async def test_delete_movie_skips_lookup_when_jellyseerr_unchecked(
        self,
        mock_delete_request: AsyncMock,
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
        # Delete request should NOT have been called
        mock_delete_request.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    @patch("app.routers.content.delete_jellyseerr_request", new_callable=AsyncMock)
    async def test_delete_movie_uses_provided_request_id_over_lookup(
        self,
        mock_delete_request: AsyncMock,
        mock_delete_movie: AsyncMock,
        mock_validate_jellyseerr: AsyncMock,
        mock_validate_radarr: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test that explicitly provided jellyseerr_request_id is used, not looked up."""
        from app.database import CachedJellyseerrRequest

        mock_delete_movie.return_value = (True, "Movie deleted successfully from Radarr")
        mock_delete_request.return_value = (True, "Request deleted successfully from Jellyseerr")
        mock_validate_radarr.return_value = True
        mock_validate_jellyseerr.return_value = True

        token = self._get_auth_token(client, "explicit_request_id@example.com")
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

        # Create a cached Jellyseerr request with different ID
        async with TestingAsyncSessionLocal() as session:
            cached_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=111,  # This would be looked up
                tmdb_id=12345,
                media_type="movie",
                status=1,
                title="Test Movie",
            )
            session.add(cached_request)
            await session.commit()

        # Delete movie WITH explicit jellyseerr_request_id
        response = client.request(
            "DELETE",
            "/api/content/movie/12345",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tmdb_id": 12345,
                "delete_from_arr": True,
                "delete_from_jellyseerr": True,
                "jellyseerr_request_id": 222,  # Explicit ID, different from cached
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["jellyseerr_deleted"] is True
        # Should use the provided ID (222), not the cached one (111)
        mock_delete_request.assert_called_once()
        call_args = mock_delete_request.call_args
        assert call_args[0][2] == 222
