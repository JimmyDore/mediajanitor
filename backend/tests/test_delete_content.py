"""Tests for content deletion endpoints (US-15.4, US-15.5, US-15.6)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


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
