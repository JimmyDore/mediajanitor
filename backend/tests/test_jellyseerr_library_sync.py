"""Tests for Jellyseerr library sync functionality (US-64.3)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sync import trigger_jellyseerr_library_sync


class TestTriggerJellyseerrLibrarySync:
    """Test triggering Jellyseerr library sync (US-64.3)."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_with_running_true(self) -> None:
        """Should return True when Jellyseerr returns 200 with running: true."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "running": True,
            "progress": 0,
            "total": 69,
            "libraries": [],
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is True
            mock_client.post.assert_called_once_with(
                "https://jellyseerr.example.com/api/v1/settings/jellyfin/sync",
                headers={
                    "X-Api-Key": "test-api-key",
                    "Content-Type": "application/json",
                },
                json={"start": True},
            )

    @pytest.mark.asyncio
    async def test_returns_false_on_200_with_running_false(self) -> None:
        """Should return False when Jellyseerr returns 200 but running: false."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "running": False,
            "progress": 0,
            "total": 0,
            "libraries": [],
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200_response(self) -> None:
        """Should return False when Jellyseerr returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Should return False when Jellyseerr returns 401 Unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "invalid-api-key"
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

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "test-api-key"
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

            result = await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_server_url(self) -> None:
        """Should strip trailing slash from server URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"running": True, "progress": 0, "total": 0}

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            await trigger_jellyseerr_library_sync(
                "https://jellyseerr.example.com/",  # Trailing slash
                "test-api-key",
            )

            # Should call without double slash
            mock_client.post.assert_called_once_with(
                "https://jellyseerr.example.com/api/v1/settings/jellyfin/sync",
                headers={
                    "X-Api-Key": "test-api-key",
                    "Content-Type": "application/json",
                },
                json={"start": True},
            )

    @pytest.mark.asyncio
    async def test_logs_warning_on_failure(self) -> None:
        """Should log warning when sync fails (not raise exception)."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.logger") as mock_logger:
                result = await trigger_jellyseerr_library_sync(
                    "https://jellyseerr.example.com", "test-api-key"
                )

                assert result is False
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logs_info_on_success(self) -> None:
        """Should log info when sync is triggered successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"running": True, "progress": 0, "total": 69}

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.logger") as mock_logger:
                result = await trigger_jellyseerr_library_sync(
                    "https://jellyseerr.example.com", "test-api-key"
                )

                assert result is True
                mock_logger.info.assert_called()
