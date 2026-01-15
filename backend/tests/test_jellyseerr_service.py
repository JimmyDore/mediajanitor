"""Unit tests for Jellyseerr service functions."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.jellyseerr import validate_jellyseerr_connection


class TestValidateJellyseerrConnection:
    """Tests for validate_jellyseerr_connection function."""

    @pytest.mark.asyncio
    async def test_uses_auth_me_endpoint_not_status(self) -> None:
        """
        Regression test: validation must use /auth/me endpoint, NOT /status.

        The /status endpoint does NOT require authentication, so any URL would
        pass validation. The /auth/me endpoint requires a valid API key.
        """
        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = await validate_jellyseerr_connection(
                "https://jellyseerr.example.com",
                "test-api-key",
            )

            # Verify the correct endpoint is called
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")

            # MUST use /auth/me (requires auth), NOT /status (no auth required)
            assert "/api/v1/auth/me" in url, (
                f"Expected /api/v1/auth/me endpoint, got {url}. "
                "The /status endpoint does NOT require authentication!"
            )
            assert "/status" not in url or "/auth/me" in url

            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Test that validation fails when API key is invalid (401)."""
        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await validate_jellyseerr_connection(
                "https://jellyseerr.example.com",
                "invalid-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_403_forbidden(self) -> None:
        """Test that validation fails when API key lacks permissions (403)."""
        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response

            result = await validate_jellyseerr_connection(
                "https://jellyseerr.example.com",
                "limited-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Test that validation fails gracefully on network errors."""
        import httpx

        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await validate_jellyseerr_connection(
                "https://nonexistent.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test that validation fails gracefully on timeout."""
        import httpx

        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await validate_jellyseerr_connection(
                "https://slow.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Test that trailing slashes are removed from server URL."""
        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_jellyseerr_connection(
                "https://jellyseerr.example.com/",  # Trailing slash
                "test-api-key",
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            # Should not have double slashes
            assert "//api" not in url
            assert url == "https://jellyseerr.example.com/api/v1/auth/me"

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        """Test that X-Api-Key header is sent with request."""
        with patch("app.services.jellyseerr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_jellyseerr_connection(
                "https://jellyseerr.example.com",
                "my-secret-api-key",
            )

            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Api-Key") == "my-secret-api-key"
