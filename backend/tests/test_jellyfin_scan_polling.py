"""Tests for Jellyfin library scan polling functionality (US-64.2)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.sync import wait_for_jellyfin_scan_completion


class TestWaitForJellyfinScanCompletion:
    """Test waiting for Jellyfin library scan completion (US-64.2)."""

    @pytest.mark.asyncio
    async def test_returns_true_when_scan_already_idle(self) -> None:
        """Should return True immediately when scan is already Idle."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
            {"Key": "SomeOtherTask", "Name": "Other Task", "State": "Running"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is True
            mock_client.get.assert_called_once_with(
                "https://jellyfin.example.com/ScheduledTasks",
                headers={"X-Emby-Token": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_returns_true_after_running_becomes_idle(self) -> None:
        """Should poll and return True when scan transitions from Running to Idle."""
        # First call: Running, Second call: Idle
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Running"},
        ]

        idle_response = MagicMock()
        idle_response.status_code = 200
        idle_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, idle_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                result = await wait_for_jellyfin_scan_completion(
                    "https://jellyfin.example.com", "test-api-key"
                )

            assert result is True
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False when timeout is reached."""
        # Always return Running to trigger timeout
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Running"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = running_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                # Use very short timeout (10 seconds) to limit poll iterations
                result = await wait_for_jellyfin_scan_completion(
                    "https://jellyfin.example.com",
                    "test-api-key",
                    timeout_seconds=10,
                    poll_interval_seconds=5,
                )

            assert result is False
            # 10s timeout / 5s interval = 2 polls (first at 0, second after 5s)
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_uses_key_not_name_for_task_identification(self) -> None:
        """Should find task by Key='RefreshLibrary', not by Name (which is localized)."""
        # Task has localized French name but should still be found by Key
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "Key": "RefreshLibrary",
                "Name": "Analyser la médiathèque",  # French localized name
                "State": "Idle",
            },
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_task_not_found(self) -> None:
        """Should return False when RefreshLibrary task is not in the list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"Key": "SomeOtherTask", "Name": "Other Task", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
            )

            # Should return False since we can't find the task to check status
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False when connection to Jellyfin fails."""
        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
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

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_strips_trailing_slash_from_server_url(self) -> None:
        """Should strip trailing slash from server URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com/",  # Trailing slash
                "test-api-key",
            )

            mock_client.get.assert_called_once_with(
                "https://jellyfin.example.com/ScheduledTasks",
                headers={"X-Emby-Token": "test-api-key"},
            )

    @pytest.mark.asyncio
    async def test_default_timeout_is_300_seconds(self) -> None:
        """Should use 300 seconds (5 minutes) as default timeout."""
        # Always return Running to trigger timeout
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Running"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = running_response
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await wait_for_jellyfin_scan_completion(
                    "https://jellyfin.example.com", "test-api-key"
                )

            assert result is False
            # Default: 300s timeout / 5s interval = 60 polls
            # First poll at 0, then 59 more after sleep
            assert mock_client.get.call_count == 60
            # Sleep called 59 times (between polls)
            assert mock_sleep.call_count == 59

    @pytest.mark.asyncio
    async def test_logs_progress_on_each_poll(self) -> None:
        """Should log progress on each poll iteration."""
        # First call: Running, Second call: Idle
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Running"},
        ]

        idle_response = MagicMock()
        idle_response.status_code = 200
        idle_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, idle_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.services.sync.logger") as mock_logger:
                    await wait_for_jellyfin_scan_completion(
                        "https://jellyfin.example.com", "test-api-key"
                    )

            # Should log info at least twice (once per poll)
            assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    async def test_handles_cancelling_state(self) -> None:
        """Should continue polling when task is in Cancelling state."""
        # First: Cancelling, Second: Idle
        cancelling_response = MagicMock()
        cancelling_response.status_code = 200
        cancelling_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Cancelling"},
        ]

        idle_response = MagicMock()
        idle_response.status_code = 200
        idle_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [cancelling_response, idle_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock):
                result = await wait_for_jellyfin_scan_completion(
                    "https://jellyfin.example.com", "test-api-key"
                )

            assert result is True
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_poll_interval(self) -> None:
        """Should use custom poll interval when specified."""
        # First: Running, Second: Idle
        running_response = MagicMock()
        running_response.status_code = 200
        running_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Running"},
        ]

        idle_response = MagicMock()
        idle_response.status_code = 200
        idle_response.json.return_value = [
            {"Key": "RefreshLibrary", "Name": "Scan Media Library", "State": "Idle"},
        ]

        with patch("app.services.sync.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = [running_response, idle_response]
            mock_client_class.return_value = mock_client

            with patch("app.services.sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await wait_for_jellyfin_scan_completion(
                    "https://jellyfin.example.com",
                    "test-api-key",
                    poll_interval_seconds=10,  # Custom interval
                )

            # Should sleep for 10 seconds between polls
            mock_sleep.assert_called_with(10)

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

            result = await wait_for_jellyfin_scan_completion(
                "https://jellyfin.example.com", "test-api-key"
            )

            assert result is False
