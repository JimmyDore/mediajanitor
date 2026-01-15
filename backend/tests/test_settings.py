"""Tests for user settings endpoints (Jellyfin/Jellyseerr configuration)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestJellyfinSettings:
    """Tests for POST /api/settings/jellyfin endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "settings@example.com") -> str:
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

    def test_save_jellyfin_settings_requires_auth(self, client: TestClient) -> None:
        """Test that saving Jellyfin settings requires authentication."""
        response = client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://jellyfin.example.com",
                "api_key": "test-api-key-12345",
            },
        )
        assert response.status_code == 401

    @patch("app.routers.settings.validate_jellyfin_connection", new_callable=AsyncMock)
    def test_save_jellyfin_settings_success(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test successful save of Jellyfin settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://jellyfin.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jellyfin" in data["message"].lower()

    @patch("app.routers.settings.validate_jellyfin_connection", new_callable=AsyncMock)
    def test_save_jellyfin_settings_invalid_connection(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test save fails when Jellyfin connection cannot be validated."""
        mock_validate.return_value = False
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://invalid.example.com",
                "api_key": "invalid-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "connection" in response.json()["detail"].lower()

    def test_save_jellyfin_settings_missing_url(self, client: TestClient) -> None:
        """Test save fails when server URL is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyfin",
            json={
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_jellyfin_settings_missing_api_key(self, client: TestClient) -> None:
        """Test save fails when API key is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://jellyfin.example.com",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_jellyfin_settings_invalid_url_format(
        self, client: TestClient
    ) -> None:
        """Test save fails when server URL has invalid format."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "not-a-valid-url",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("app.routers.settings.validate_jellyfin_connection", new_callable=AsyncMock)
    def test_get_jellyfin_settings(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test retrieving saved Jellyfin settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        # First save settings
        client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://jellyfin.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Then retrieve them
        response = client.get(
            "/api/settings/jellyfin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] == "https://jellyfin.example.com"
        # API key should be masked for security
        assert data["api_key_configured"] is True
        assert "api_key" not in data  # Full key should not be returned

    def test_get_jellyfin_settings_not_configured(self, client: TestClient) -> None:
        """Test retrieving Jellyfin settings when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/jellyfin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False

    @patch("app.routers.settings.validate_jellyfin_connection", new_callable=AsyncMock)
    def test_jellyfin_settings_per_user_isolation(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test that users can only see their own Jellyfin settings."""
        mock_validate.return_value = True

        # Create first user and save settings
        token1 = self._get_auth_token(client, "user1@example.com")

        client.post(
            "/api/settings/jellyfin",
            json={
                "server_url": "https://user1-jellyfin.example.com",
                "api_key": "user1-api-key",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user
        token2 = self._get_auth_token(client, "user2@example.com")

        # Second user should not see first user's settings
        response = client.get(
            "/api/settings/jellyfin",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False


class TestRadarrSettings:
    """Tests for Radarr settings endpoints."""

    def _get_auth_token(self, client: TestClient, email: str = "radarr@example.com") -> str:
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

    def test_save_radarr_settings_requires_auth(self, client: TestClient) -> None:
        """Test that saving Radarr settings requires authentication."""
        response = client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
                "api_key": "test-api-key-12345",
            },
        )
        assert response.status_code == 401

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    def test_save_radarr_settings_success(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test successful save of Radarr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "radarr" in data["message"].lower()

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    def test_save_radarr_settings_invalid_connection(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test save fails when Radarr connection cannot be validated."""
        mock_validate.return_value = False
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://invalid.example.com",
                "api_key": "invalid-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "connection" in response.json()["detail"].lower()

    def test_save_radarr_settings_missing_url(self, client: TestClient) -> None:
        """Test save fails when server URL is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/radarr",
            json={
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_radarr_settings_missing_api_key(self, client: TestClient) -> None:
        """Test save fails when API key is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_radarr_settings_invalid_url_format(
        self, client: TestClient
    ) -> None:
        """Test save fails when server URL has invalid format."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/radarr",
            json={
                "server_url": "not-a-valid-url",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    def test_get_radarr_settings(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test retrieving saved Radarr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        # First save settings
        client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://radarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Then retrieve them
        response = client.get(
            "/api/settings/radarr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] == "https://radarr.example.com"
        # API key should be masked for security
        assert data["api_key_configured"] is True
        assert "api_key" not in data  # Full key should not be returned

    def test_get_radarr_settings_not_configured(self, client: TestClient) -> None:
        """Test retrieving Radarr settings when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/radarr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False

    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    def test_radarr_settings_per_user_isolation(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test that users can only see their own Radarr settings."""
        mock_validate.return_value = True

        # Create first user and save settings
        token1 = self._get_auth_token(client, "radarr_user1@example.com")

        client.post(
            "/api/settings/radarr",
            json={
                "server_url": "https://user1-radarr.example.com",
                "api_key": "user1-api-key",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user
        token2 = self._get_auth_token(client, "radarr_user2@example.com")

        # Second user should not see first user's settings
        response = client.get(
            "/api/settings/radarr",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False


class TestSonarrSettings:
    """Tests for Sonarr settings endpoints."""

    def _get_auth_token(self, client: TestClient, email: str = "sonarr@example.com") -> str:
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

    def test_save_sonarr_settings_requires_auth(self, client: TestClient) -> None:
        """Test that saving Sonarr settings requires authentication."""
        response = client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://sonarr.example.com",
                "api_key": "test-api-key-12345",
            },
        )
        assert response.status_code == 401

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    def test_save_sonarr_settings_success(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test successful save of Sonarr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://sonarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sonarr" in data["message"].lower()

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    def test_save_sonarr_settings_invalid_connection(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test save fails when Sonarr connection cannot be validated."""
        mock_validate.return_value = False
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://invalid.example.com",
                "api_key": "invalid-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "connection" in response.json()["detail"].lower()

    def test_save_sonarr_settings_missing_url(self, client: TestClient) -> None:
        """Test save fails when server URL is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/sonarr",
            json={
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_sonarr_settings_missing_api_key(self, client: TestClient) -> None:
        """Test save fails when API key is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://sonarr.example.com",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_sonarr_settings_invalid_url_format(
        self, client: TestClient
    ) -> None:
        """Test save fails when server URL has invalid format."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "not-a-valid-url",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    def test_get_sonarr_settings(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test retrieving saved Sonarr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        # First save settings
        client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://sonarr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Then retrieve them
        response = client.get(
            "/api/settings/sonarr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] == "https://sonarr.example.com"
        # API key should be masked for security
        assert data["api_key_configured"] is True
        assert "api_key" not in data  # Full key should not be returned

    def test_get_sonarr_settings_not_configured(self, client: TestClient) -> None:
        """Test retrieving Sonarr settings when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/sonarr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False

    @patch("app.routers.settings.validate_sonarr_connection", new_callable=AsyncMock)
    def test_sonarr_settings_per_user_isolation(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test that users can only see their own Sonarr settings."""
        mock_validate.return_value = True

        # Create first user and save settings
        token1 = self._get_auth_token(client, "sonarr_user1@example.com")

        client.post(
            "/api/settings/sonarr",
            json={
                "server_url": "https://user1-sonarr.example.com",
                "api_key": "user1-api-key",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user
        token2 = self._get_auth_token(client, "sonarr_user2@example.com")

        # Second user should not see first user's settings
        response = client.get(
            "/api/settings/sonarr",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False


class TestJellyseerrSettings:
    """Tests for Jellyseerr settings endpoints."""

    def _get_auth_token(self, client: TestClient, email: str = "jellyseerr@example.com") -> str:
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

    def test_save_jellyseerr_settings_requires_auth(self, client: TestClient) -> None:
        """Test that saving Jellyseerr settings requires authentication."""
        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
                "api_key": "test-api-key-12345",
            },
        )
        assert response.status_code == 401

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    def test_save_jellyseerr_settings_success(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test successful save of Jellyseerr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "jellyseerr" in data["message"].lower()

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    def test_save_jellyseerr_settings_invalid_connection(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test save fails when Jellyseerr connection cannot be validated."""
        mock_validate.return_value = False
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://invalid.example.com",
                "api_key": "invalid-api-key",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400
        assert "connection" in response.json()["detail"].lower()

    def test_save_jellyseerr_settings_missing_url(self, client: TestClient) -> None:
        """Test save fails when server URL is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_jellyseerr_settings_missing_api_key(self, client: TestClient) -> None:
        """Test save fails when API key is missing."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_save_jellyseerr_settings_invalid_url_format(
        self, client: TestClient
    ) -> None:
        """Test save fails when server URL has invalid format."""
        token = self._get_auth_token(client)

        response = client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "not-a-valid-url",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    def test_get_jellyseerr_settings(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test retrieving saved Jellyseerr settings."""
        mock_validate.return_value = True
        token = self._get_auth_token(client)

        # First save settings
        client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://jellyseerr.example.com",
                "api_key": "test-api-key-12345",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Then retrieve them
        response = client.get(
            "/api/settings/jellyseerr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] == "https://jellyseerr.example.com"
        # API key should be masked for security
        assert data["api_key_configured"] is True
        assert "api_key" not in data  # Full key should not be returned

    def test_get_jellyseerr_settings_not_configured(self, client: TestClient) -> None:
        """Test retrieving Jellyseerr settings when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/jellyseerr",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False

    @patch("app.routers.settings.validate_jellyseerr_connection", new_callable=AsyncMock)
    def test_jellyseerr_settings_per_user_isolation(
        self, mock_validate: AsyncMock, client: TestClient
    ) -> None:
        """Test that users can only see their own Jellyseerr settings."""
        mock_validate.return_value = True

        # Create first user and save settings
        token1 = self._get_auth_token(client, "jseerr_user1@example.com")

        client.post(
            "/api/settings/jellyseerr",
            json={
                "server_url": "https://user1-jellyseerr.example.com",
                "api_key": "user1-api-key",
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user
        token2 = self._get_auth_token(client, "jseerr_user2@example.com")

        # Second user should not see first user's settings
        response = client.get(
            "/api/settings/jellyseerr",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server_url"] is None
        assert data["api_key_configured"] is False


class TestAnalysisPreferences:
    """Tests for analysis preferences endpoints (thresholds)."""

    def _get_auth_token(self, client: TestClient, email: str = "prefs@example.com") -> str:
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

    def test_get_analysis_preferences_defaults(self, client: TestClient) -> None:
        """Test retrieving analysis preferences returns defaults when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["old_content_months"] == 4
        assert data["min_age_months"] == 3
        assert data["large_movie_size_gb"] == 13

    def test_get_analysis_preferences_requires_auth(self, client: TestClient) -> None:
        """Test that getting analysis preferences requires authentication."""
        response = client.get("/api/settings/analysis")
        assert response.status_code == 401

    def test_save_analysis_preferences_success(self, client: TestClient) -> None:
        """Test successful save of analysis preferences."""
        token = self._get_auth_token(client, "prefs_save@example.com")

        response = client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 6,
                "min_age_months": 2,
                "large_movie_size_gb": 15,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_save_analysis_preferences_requires_auth(self, client: TestClient) -> None:
        """Test that saving analysis preferences requires authentication."""
        response = client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 6,
                "min_age_months": 2,
                "large_movie_size_gb": 15,
            },
        )
        assert response.status_code == 401

    def test_saved_analysis_preferences_are_returned(self, client: TestClient) -> None:
        """Test that saved analysis preferences are returned on GET."""
        token = self._get_auth_token(client, "prefs_verify@example.com")

        # Save custom preferences
        client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 8,
                "min_age_months": 1,
                "large_movie_size_gb": 20,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify they are returned
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["old_content_months"] == 8
        assert data["min_age_months"] == 1
        assert data["large_movie_size_gb"] == 20

    def test_analysis_preferences_per_user_isolation(self, client: TestClient) -> None:
        """Test that users can only see their own analysis preferences."""
        # Create first user and save preferences
        token1 = self._get_auth_token(client, "prefs_user1@example.com")

        client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 12,
                "min_age_months": 6,
                "large_movie_size_gb": 25,
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user - should get defaults, not first user's settings
        token2 = self._get_auth_token(client, "prefs_user2@example.com")

        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Second user should get defaults, not first user's settings
        assert data["old_content_months"] == 4
        assert data["min_age_months"] == 3
        assert data["large_movie_size_gb"] == 13

    def test_reset_analysis_preferences(self, client: TestClient) -> None:
        """Test resetting analysis preferences to defaults."""
        token = self._get_auth_token(client, "prefs_reset@example.com")

        # First save custom preferences
        client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 10,
                "min_age_months": 5,
                "large_movie_size_gb": 18,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Reset to defaults
        response = client.delete(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify defaults are returned
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert data["old_content_months"] == 4
        assert data["min_age_months"] == 3
        assert data["large_movie_size_gb"] == 13

    def test_save_analysis_preferences_partial_update(self, client: TestClient) -> None:
        """Test that partial update only changes specified fields."""
        token = self._get_auth_token(client, "prefs_partial@example.com")

        # Save only one preference
        response = client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": 10,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify: only old_content_months changed, others remain default
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert data["old_content_months"] == 10
        assert data["min_age_months"] == 3  # Default
        assert data["large_movie_size_gb"] == 13  # Default

    def test_save_analysis_preferences_validates_values(self, client: TestClient) -> None:
        """Test that analysis preferences validates input values."""
        token = self._get_auth_token(client, "prefs_validate@example.com")

        # Test negative value
        response = client.post(
            "/api/settings/analysis",
            json={
                "old_content_months": -1,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

        # Test zero value for size threshold
        response = client.post(
            "/api/settings/analysis",
            json={
                "large_movie_size_gb": 0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_get_analysis_preferences_large_season_default(
        self, client: TestClient
    ) -> None:
        """Test that default large_season_size_gb is 15."""
        token = self._get_auth_token(client, "large_season_default@example.com")

        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["large_season_size_gb"] == 15

    def test_save_large_season_size_gb_success(self, client: TestClient) -> None:
        """Test saving large_season_size_gb."""
        token = self._get_auth_token(client, "large_season_save@example.com")

        response = client.post(
            "/api/settings/analysis",
            json={"large_season_size_gb": 20},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify it's saved
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["large_season_size_gb"] == 20

    def test_large_season_size_gb_validates_min(self, client: TestClient) -> None:
        """Test that large_season_size_gb validates minimum of 1."""
        token = self._get_auth_token(client, "large_season_min@example.com")

        response = client.post(
            "/api/settings/analysis",
            json={"large_season_size_gb": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_large_season_size_gb_validates_max(self, client: TestClient) -> None:
        """Test that large_season_size_gb validates maximum of 100."""
        token = self._get_auth_token(client, "large_season_max@example.com")

        response = client.post(
            "/api/settings/analysis",
            json={"large_season_size_gb": 101},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_large_season_size_gb_accepts_boundary_values(
        self, client: TestClient
    ) -> None:
        """Test that large_season_size_gb accepts 1 and 100."""
        token = self._get_auth_token(client, "large_season_boundary@example.com")

        # Test min boundary (1)
        response = client.post(
            "/api/settings/analysis",
            json={"large_season_size_gb": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["large_season_size_gb"] == 1

        # Test max boundary (100)
        response = client.post(
            "/api/settings/analysis",
            json={"large_season_size_gb": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        response = client.get(
            "/api/settings/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["large_season_size_gb"] == 100


class TestDisplayPreferences:
    """Tests for display preferences endpoints (US-13.6)."""

    def _get_auth_token(self, client: TestClient, email: str = "display@example.com") -> str:
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

    def test_get_display_preferences_defaults(self, client: TestClient) -> None:
        """Test retrieving display preferences returns defaults when not configured."""
        token = self._get_auth_token(client)

        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["show_unreleased_requests"] is False
        assert data["theme_preference"] == "system"

    def test_get_display_preferences_requires_auth(self, client: TestClient) -> None:
        """Test that getting display preferences requires authentication."""
        response = client.get("/api/settings/display")
        assert response.status_code == 401

    def test_save_display_preferences_success(self, client: TestClient) -> None:
        """Test successful save of display preferences."""
        token = self._get_auth_token(client, "display_save@example.com")

        response = client.post(
            "/api/settings/display",
            json={
                "show_unreleased_requests": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_save_display_preferences_requires_auth(self, client: TestClient) -> None:
        """Test that saving display preferences requires authentication."""
        response = client.post(
            "/api/settings/display",
            json={
                "show_unreleased_requests": True,
            },
        )
        assert response.status_code == 401

    def test_saved_display_preferences_are_returned(self, client: TestClient) -> None:
        """Test that saved display preferences are returned on GET."""
        token = self._get_auth_token(client, "display_verify@example.com")

        # Save custom preferences
        client.post(
            "/api/settings/display",
            json={
                "show_unreleased_requests": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify they are returned
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["show_unreleased_requests"] is True

    def test_display_preferences_per_user_isolation(self, client: TestClient) -> None:
        """Test that users can only see their own display preferences."""
        # Create first user and save preferences
        token1 = self._get_auth_token(client, "display_user1@example.com")

        client.post(
            "/api/settings/display",
            json={
                "show_unreleased_requests": True,
            },
            headers={"Authorization": f"Bearer {token1}"},
        )

        # Create second user - should get defaults, not first user's settings
        token2 = self._get_auth_token(client, "display_user2@example.com")

        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Second user should get default (False), not first user's settings
        assert data["show_unreleased_requests"] is False

    def test_toggle_show_unreleased_requests(self, client: TestClient) -> None:
        """Test toggling show_unreleased_requests on and off."""
        token = self._get_auth_token(client, "display_toggle@example.com")

        # Turn on
        client.post(
            "/api/settings/display",
            json={"show_unreleased_requests": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["show_unreleased_requests"] is True

        # Turn off
        client.post(
            "/api/settings/display",
            json={"show_unreleased_requests": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["show_unreleased_requests"] is False

    def test_get_display_preferences_theme_default(self, client: TestClient) -> None:
        """Test that default theme_preference is 'system'."""
        token = self._get_auth_token(client, "theme_default@example.com")

        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["theme_preference"] == "system"

    def test_save_theme_preference_light(self, client: TestClient) -> None:
        """Test saving theme_preference to 'light'."""
        token = self._get_auth_token(client, "theme_light@example.com")

        response = client.post(
            "/api/settings/display",
            json={"theme_preference": "light"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify it's saved
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["theme_preference"] == "light"

    def test_save_theme_preference_dark(self, client: TestClient) -> None:
        """Test saving theme_preference to 'dark'."""
        token = self._get_auth_token(client, "theme_dark@example.com")

        client.post(
            "/api/settings/display",
            json={"theme_preference": "dark"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["theme_preference"] == "dark"

    def test_theme_preference_invalid_value_rejected(self, client: TestClient) -> None:
        """Test that invalid theme_preference values are rejected."""
        token = self._get_auth_token(client, "theme_invalid@example.com")

        response = client.post(
            "/api/settings/display",
            json={"theme_preference": "invalid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Pydantic should reject invalid literal values
        assert response.status_code == 422

    def test_get_display_preferences_recently_available_days_default(
        self, client: TestClient
    ) -> None:
        """Test that default recently_available_days is 7."""
        token = self._get_auth_token(client, "recent_days_default@example.com")

        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recently_available_days"] == 7

    def test_save_recently_available_days_success(self, client: TestClient) -> None:
        """Test saving recently_available_days."""
        token = self._get_auth_token(client, "recent_days_save@example.com")

        response = client.post(
            "/api/settings/display",
            json={"recently_available_days": 14},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify it's saved
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["recently_available_days"] == 14

    def test_recently_available_days_validates_min(self, client: TestClient) -> None:
        """Test that recently_available_days validates minimum of 1."""
        token = self._get_auth_token(client, "recent_days_min@example.com")

        response = client.post(
            "/api/settings/display",
            json={"recently_available_days": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_recently_available_days_validates_max(self, client: TestClient) -> None:
        """Test that recently_available_days validates maximum of 30."""
        token = self._get_auth_token(client, "recent_days_max@example.com")

        response = client.post(
            "/api/settings/display",
            json={"recently_available_days": 31},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_recently_available_days_accepts_boundary_values(
        self, client: TestClient
    ) -> None:
        """Test that recently_available_days accepts 1 and 30."""
        token = self._get_auth_token(client, "recent_days_boundary@example.com")

        # Test min boundary (1)
        response = client.post(
            "/api/settings/display",
            json={"recently_available_days": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["recently_available_days"] == 1

        # Test max boundary (30)
        response = client.post(
            "/api/settings/display",
            json={"recently_available_days": 30},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        response = client.get(
            "/api/settings/display",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.json()["recently_available_days"] == 30


class TestNicknameSettings:
    """Tests for nickname mapping endpoints (US-31.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "nickname@example.com") -> str:
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

    def test_list_nicknames_requires_auth(self, client: TestClient) -> None:
        """Test that listing nicknames requires authentication."""
        response = client.get("/api/settings/nicknames")
        assert response.status_code == 401

    def test_list_nicknames_returns_empty_list(self, client: TestClient) -> None:
        """Test that new user has empty nickname list."""
        token = self._get_auth_token(client, "nick_list_empty@example.com")

        response = client.get(
            "/api/settings/nicknames",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_create_nickname_requires_auth(self, client: TestClient) -> None:
        """Test that creating nickname requires authentication."""
        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "john_doe", "display_name": "John"},
        )
        assert response.status_code == 401

    def test_create_nickname_success(self, client: TestClient) -> None:
        """Test successful creation of nickname mapping."""
        token = self._get_auth_token(client, "nick_create@example.com")

        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "john_doe", "display_name": "John"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["jellyseerr_username"] == "john_doe"
        assert data["display_name"] == "John"
        assert "id" in data
        assert "created_at" in data

    def test_create_nickname_duplicate_returns_409(self, client: TestClient) -> None:
        """Test that creating duplicate mapping returns 409 Conflict."""
        token = self._get_auth_token(client, "nick_dup@example.com")

        # Create first mapping
        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "jane_doe", "display_name": "Jane"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201

        # Try to create duplicate
        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "jane_doe", "display_name": "Janet"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_list_nicknames_returns_all_mappings(self, client: TestClient) -> None:
        """Test that list returns all created mappings."""
        token = self._get_auth_token(client, "nick_list@example.com")

        # Create multiple mappings
        client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "alice", "display_name": "Alice"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "bob", "display_name": "Bobby"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.get(
            "/api/settings/nicknames",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        usernames = [item["jellyseerr_username"] for item in data["items"]]
        # Should be alphabetically sorted
        assert usernames == ["alice", "bob"]

    def test_update_nickname_success(self, client: TestClient) -> None:
        """Test successful update of nickname display name."""
        token = self._get_auth_token(client, "nick_update@example.com")

        # Create mapping
        create_response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "charlie", "display_name": "Charlie"},
            headers={"Authorization": f"Bearer {token}"},
        )
        nickname_id = create_response.json()["id"]

        # Update display name
        response = client.put(
            f"/api/settings/nicknames/{nickname_id}",
            json={"display_name": "Chuck"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Chuck"
        assert data["jellyseerr_username"] == "charlie"

    def test_update_nickname_not_found_returns_404(self, client: TestClient) -> None:
        """Test that updating non-existent nickname returns 404."""
        token = self._get_auth_token(client, "nick_update_404@example.com")

        response = client.put(
            "/api/settings/nicknames/99999",
            json={"display_name": "Nobody"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_nickname_success(self, client: TestClient) -> None:
        """Test successful deletion of nickname mapping."""
        token = self._get_auth_token(client, "nick_delete@example.com")

        # Create mapping
        create_response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "david", "display_name": "Dave"},
            headers={"Authorization": f"Bearer {token}"},
        )
        nickname_id = create_response.json()["id"]

        # Delete mapping
        response = client.delete(
            f"/api/settings/nicknames/{nickname_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        list_response = client.get(
            "/api/settings/nicknames",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.json()["total_count"] == 0

    def test_delete_nickname_not_found_returns_404(self, client: TestClient) -> None:
        """Test that deleting non-existent nickname returns 404."""
        token = self._get_auth_token(client, "nick_delete_404@example.com")

        response = client.delete(
            "/api/settings/nicknames/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_nickname_validates_empty_username(self, client: TestClient) -> None:
        """Test that empty username is rejected."""
        token = self._get_auth_token(client, "nick_valid_user@example.com")

        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "", "display_name": "Test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_create_nickname_validates_empty_display_name(self, client: TestClient) -> None:
        """Test that empty display name is rejected."""
        token = self._get_auth_token(client, "nick_valid_display@example.com")

        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "valid_user", "display_name": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_nicknames_are_user_isolated(self, client: TestClient) -> None:
        """Test that nicknames are isolated per user."""
        token1 = self._get_auth_token(client, "nick_user1@example.com")
        token2 = self._get_auth_token(client, "nick_user2@example.com")

        # User 1 creates a mapping
        client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "shared_name", "display_name": "User1's Friend"},
            headers={"Authorization": f"Bearer {token1}"},
        )

        # User 2 can create same username mapping (different user)
        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "shared_name", "display_name": "User2's Friend"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert response.status_code == 201

        # User 1 sees only their mapping
        list1 = client.get(
            "/api/settings/nicknames",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert list1.json()["total_count"] == 1
        assert list1.json()["items"][0]["display_name"] == "User1's Friend"

        # User 2 sees only their mapping
        list2 = client.get(
            "/api/settings/nicknames",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert list2.json()["total_count"] == 1
        assert list2.json()["items"][0]["display_name"] == "User2's Friend"
