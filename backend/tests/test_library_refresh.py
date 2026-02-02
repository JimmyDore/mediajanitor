"""Tests for Jellyfin library refresh functionality (US-64.1)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.sync import trigger_jellyfin_library_refresh


class TestTriggerJellyfinLibraryRefresh:
    """Test triggering Jellyfin library refresh (US-64.1)."""

    @pytest.mark.asyncio
    async def test_returns_true_on_204_response(self) -> None:
        """Should return True when Jellyfin returns 204 No Content."""
        mock_response = AsyncMock()
        mock_response.status_code = 204

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is True
            mock_client.post.assert_called_once_with(
                "https://jellyfin.example.com/Library/Refresh",
                headers={"X-Emby-Token": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_returns_false_on_non_204_response(self) -> None:
        """Should return False when Jellyfin returns non-204 status."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Should return False when Jellyfin returns 401 Unauthorized."""
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com", "invalid-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False and log warning on connection error."""
        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            result = await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False and log warning on timeout."""
        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_client_class.return_value = mock_client

            result = await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_server_url(self) -> None:
        """Should strip trailing slash from server URL."""
        mock_response = AsyncMock()
        mock_response.status_code = 204

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            await trigger_jellyfin_library_refresh(
                "https://jellyfin.example.com/",  # Trailing slash
                "test-api-key",
            )

            # Should call without double slash
            mock_client.post.assert_called_once_with(
                "https://jellyfin.example.com/Library/Refresh",
                headers={"X-Emby-Token": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_logs_warning_on_failure(self) -> None:
        """Should log warning when refresh fails (not raise exception)."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.logger") as mock_logger:
                result = await trigger_jellyfin_library_refresh(
                    "https://jellyfin.example.com", "test-api-key"
                )

                assert result is False
                mock_logger.warning.assert_called()
