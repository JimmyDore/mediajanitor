"""Tests for Jellyseerr sync polling functionality (US-64.4)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sync import wait_for_jellyseerr_sync_completion


class TestWaitForJellyseerrSyncCompletion:
    """Test waiting for Jellyseerr library sync completion (US-64.4)."""

    @pytest.mark.asyncio
    async def test_returns_true_when_sync_already_complete(self) -> None:
        """Should return True immediately when sync is not running."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
            "libraries": [],
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyseerr_sync_completion(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is True
            mock_client.get.assert_called_once_with(
                "https://jellyseerr.example.com/api/v1/settings/jellyfin/sync",
                headers={"X-Api-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_returns_true_after_running_becomes_false(self) -> None:
        """Should poll and return True when sync transitions from running to complete."""
        # First call: running=True, Second call: running=False
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
            "libraries": [],
        }

        complete_response = MagicMock()
        complete_response.status_code = 200
        complete_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
            "libraries": [],
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, complete_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                result = await wait_for_jellyseerr_sync_completion(
                    "https://jellyseerr.example.com", "test-api-key"
                )

            assert result is True
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False when timeout is reached."""
        # Always return running=True to trigger timeout
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
            "libraries": [],
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = running_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                # Use short timeout to limit poll iterations
                result = await wait_for_jellyseerr_sync_completion(
                    "https://jellyseerr.example.com",
                    "test-api-key",
                    timeout_seconds=10,
                    poll_interval_seconds=5,
                )

            assert result is False
            # 10s timeout / 5s interval = 2 polls
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False when connection to Jellyseerr fails."""
        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyseerr_sync_completion(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout_exception(self) -> None:
        """Should return False when request times out."""
        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyseerr_sync_completion(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200_response(self) -> None:
        """Should return False when API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyseerr_sync_completion(
                "https://jellyseerr.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_server_url(self) -> None:
        """Should strip trailing slash from server URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await wait_for_jellyseerr_sync_completion(
                "https://jellyseerr.example.com/",  # Trailing slash
                "test-api-key",
            )

            mock_client.get.assert_called_once_with(
                "https://jellyseerr.example.com/api/v1/settings/jellyfin/sync",
                headers={"X-Api-Key": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_default_timeout_is_300_seconds(self) -> None:
        """Should use 300 seconds (5 minutes) as default timeout."""
        # Always return running=True to trigger timeout
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = running_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await wait_for_jellyseerr_sync_completion(
                    "https://jellyseerr.example.com", "test-api-key"
                )

            assert result is False
            # Default: 300s timeout / 5s interval = 60 polls
            assert mock_client.get.call_count == 60
            # Sleep called 59 times (between polls)
            assert mock_sleep.call_count == 59

    @pytest.mark.asyncio
    async def test_logs_progress_on_each_poll(self) -> None:
        """Should log progress on each poll iteration with item counts."""
        # First call: progress 30/69, Second call: complete
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
        }

        complete_response = MagicMock()
        complete_response.status_code = 200
        complete_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, complete_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.services.sync.logger") as mock_logger:
                    await wait_for_jellyseerr_sync_completion(
                        "https://jellyseerr.example.com", "test-api-key"
                    )

            # Should log info with progress counts
            assert mock_logger.info.call_count >= 2
            # Check that progress is logged (e.g., "30/69 items")
            calls = [str(call) for call in mock_logger.info.call_args_list]
            progress_logged = any("30" in call and "69" in call for call in calls)
            assert progress_logged, f"Expected progress logging, got: {calls}"

    @pytest.mark.asyncio
    async def test_custom_poll_interval(self) -> None:
        """Should use custom poll interval when specified."""
        # First: running, Second: complete
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
        }

        complete_response = MagicMock()
        complete_response.status_code = 200
        complete_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, complete_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await wait_for_jellyseerr_sync_completion(
                    "https://jellyseerr.example.com",
                    "test-api-key",
                    poll_interval_seconds=10,  # Custom interval
                )

            # Should sleep for 10 seconds between polls
            mock_sleep.assert_called_with(10)

    @pytest.mark.asyncio
    async def test_logs_warning_on_timeout(self) -> None:
        """Should log warning when timeout is reached."""
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = {
            "running": True,
            "progress": 30,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = running_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.services.sync.logger") as mock_logger:
                    await wait_for_jellyseerr_sync_completion(
                        "https://jellyseerr.example.com",
                        "test-api-key",
                        timeout_seconds=10,
                        poll_interval_seconds=5,
                    )

            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_logs_info_on_completion(self) -> None:
        """Should log info when sync completes successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "running": False,
            "progress": 69,
            "total": 69,
        }

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.logger") as mock_logger:
                result = await wait_for_jellyseerr_sync_completion(
                    "https://jellyseerr.example.com", "test-api-key"
                )

                assert result is True
                mock_logger.info.assert_called()
