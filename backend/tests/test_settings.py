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
