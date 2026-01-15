"""Unit tests for Slack notification service."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.services.slack import send_slack_message
from app.config import Settings


class TestSendSlackMessage:
    """Tests for send_slack_message function."""

    @pytest.mark.asyncio
    async def test_sends_message_to_webhook_url(self) -> None:
        """Test that message is sent to the correct webhook URL."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            webhook_url = "https://hooks.slack.com/services/T00/B00/XXX"
            message = {"text": "Hello, Slack!"}

            result = await send_slack_message(webhook_url, message)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == webhook_url
            assert call_args[1]["json"] == message
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        """Test that function returns True on successful send."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = await send_slack_message(
                "https://hooks.slack.com/services/T00/B00/XXX",
                {"text": "Test message"},
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self) -> None:
        """Test that function returns False on HTTP error and logs warning."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            with patch("app.services.slack.logger") as mock_logger:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_response = AsyncMock()
                mock_response.status_code = 400
                mock_response.text = "invalid_payload"
                mock_client.post.return_value = mock_response

                result = await send_slack_message(
                    "https://hooks.slack.com/services/T00/B00/XXX",
                    {"invalid": "payload"},
                )

                assert result is False
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_request_error(self) -> None:
        """Test that function returns False on network error and logs warning."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            with patch("app.services.slack.logger") as mock_logger:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.post.side_effect = httpx.RequestError("Connection refused")

                result = await send_slack_message(
                    "https://hooks.slack.com/services/T00/B00/XXX",
                    {"text": "Test"},
                )

                assert result is False
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test that function returns False on timeout and logs warning."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            with patch("app.services.slack.logger") as mock_logger:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                mock_client.post.side_effect = httpx.TimeoutException("Timed out")

                result = await send_slack_message(
                    "https://hooks.slack.com/services/T00/B00/XXX",
                    {"text": "Test"},
                )

                assert result is False
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_async_and_non_blocking(self) -> None:
        """Test that function is async and completes without blocking."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            # If this doesn't block, the test will pass
            import asyncio
            result = await asyncio.wait_for(
                send_slack_message(
                    "https://hooks.slack.com/services/T00/B00/XXX",
                    {"text": "Test"},
                ),
                timeout=1.0,  # Should complete almost instantly with mock
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_accepts_block_kit_format(self) -> None:
        """Test that function accepts Slack Block Kit formatted messages."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            # Block Kit message format
            message = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*New user signed up!*",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": "*Email:*\ntest@example.com"},
                            {"type": "mrkdwn", "text": "*Time:*\n2024-01-15 10:30 UTC"},
                        ],
                    },
                ]
            }

            result = await send_slack_message(
                "https://hooks.slack.com/services/T00/B00/XXX",
                message,
            )

            call_args = mock_client.post.call_args
            assert call_args[1]["json"] == message
            assert result is True

    @pytest.mark.asyncio
    async def test_does_not_crash_on_error(self) -> None:
        """Test that function handles errors gracefully and doesn't crash."""
        with patch("app.services.slack.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            # Simulate unexpected exception
            mock_client.post.side_effect = Exception("Unexpected error")

            # Should not raise, just return False
            result = await send_slack_message(
                "https://hooks.slack.com/services/T00/B00/XXX",
                {"text": "Test"},
            )

            assert result is False


class TestSlackConfig:
    """Tests for Slack configuration settings."""

    def test_slack_webhook_new_users_defaults_to_empty(self) -> None:
        """Test that slack_webhook_new_users defaults to empty string."""
        settings = Settings()
        assert settings.slack_webhook_new_users == ""

    def test_slack_webhook_sync_failures_defaults_to_empty(self) -> None:
        """Test that slack_webhook_sync_failures defaults to empty string."""
        settings = Settings()
        assert settings.slack_webhook_sync_failures == ""

    def test_webhooks_are_optional(self) -> None:
        """Test that webhooks being empty is valid - they're optional."""
        settings = Settings()
        # Empty string is falsy, so we can use it to check if configured
        assert not settings.slack_webhook_new_users
        assert not settings.slack_webhook_sync_failures
