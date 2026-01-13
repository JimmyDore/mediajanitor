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
