"""Tests for retry with exponential backoff functionality (US-26.1)."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.retry import (
    is_transient_error,
    retry_with_backoff,
    MAX_RETRIES,
    INITIAL_DELAY,
)


class TestIsTransientError:
    """Test identification of transient vs permanent errors."""

    def test_timeout_is_transient(self) -> None:
        """Timeout exceptions should be retried."""
        error = httpx.TimeoutException("Connection timed out")
        assert is_transient_error(error) is True

    def test_connect_error_is_transient(self) -> None:
        """Connection errors should be retried."""
        error = httpx.ConnectError("Failed to connect")
        assert is_transient_error(error) is True

    def test_read_error_is_transient(self) -> None:
        """Read errors should be retried."""
        error = httpx.ReadError("Connection reset")
        assert is_transient_error(error) is True

    def test_500_error_is_transient(self) -> None:
        """5xx HTTP errors should be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(500, request=request)
        error = httpx.HTTPStatusError("Server error", request=request, response=response)
        assert is_transient_error(error) is True

    def test_502_error_is_transient(self) -> None:
        """502 Bad Gateway should be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(502, request=request)
        error = httpx.HTTPStatusError("Bad gateway", request=request, response=response)
        assert is_transient_error(error) is True

    def test_503_error_is_transient(self) -> None:
        """503 Service Unavailable should be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(503, request=request)
        error = httpx.HTTPStatusError("Service unavailable", request=request, response=response)
        assert is_transient_error(error) is True

    def test_401_error_is_not_transient(self) -> None:
        """401 Unauthorized should NOT be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(401, request=request)
        error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
        assert is_transient_error(error) is False

    def test_404_error_is_not_transient(self) -> None:
        """404 Not Found should NOT be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(404, request=request)
        error = httpx.HTTPStatusError("Not found", request=request, response=response)
        assert is_transient_error(error) is False

    def test_400_error_is_not_transient(self) -> None:
        """400 Bad Request should NOT be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(400, request=request)
        error = httpx.HTTPStatusError("Bad request", request=request, response=response)
        assert is_transient_error(error) is False

    def test_403_error_is_not_transient(self) -> None:
        """403 Forbidden should NOT be retried."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(403, request=request)
        error = httpx.HTTPStatusError("Forbidden", request=request, response=response)
        assert is_transient_error(error) is False


class TestRetryWithBackoff:
    """Test retry mechanism with exponential backoff."""

    @pytest.mark.asyncio
    async def test_returns_result_on_first_success(self) -> None:
        """Should return result immediately if first call succeeds."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_with_backoff(mock_func, "Jellyfin")

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error_then_succeeds(self) -> None:
        """Should retry on transient error and succeed if subsequent call works."""
        # First call: timeout error, second call: success
        mock_func = AsyncMock(side_effect=[
            httpx.TimeoutException("Timeout"),
            "success",
        ])

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(mock_func, "Jellyfin")

        assert result == "success"
        assert mock_func.call_count == 2
        # Should have slept with initial delay (1 second)
        mock_sleep.assert_called_once_with(INITIAL_DELAY)

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self) -> None:
        """Should use exponential backoff: 1s, 2s, 4s between retries."""
        # Fail 3 times, succeed on 4th
        mock_func = AsyncMock(side_effect=[
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            httpx.ConnectError("Connection failed"),
            "success",
        ])

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(mock_func, "Jellyfin")

        assert result == "success"
        assert mock_func.call_count == 4
        # Should have slept with delays: 1, 2, 4 seconds
        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @pytest.mark.asyncio
    async def test_raises_after_max_retries_exhausted(self) -> None:
        """Should raise the error after all retries are exhausted."""
        # Fail all 4 attempts (1 initial + 3 retries)
        timeout_error = httpx.TimeoutException("Persistent timeout")
        mock_func = AsyncMock(side_effect=[
            timeout_error,
            timeout_error,
            timeout_error,
            timeout_error,
        ])

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.TimeoutException) as exc_info:
                await retry_with_backoff(mock_func, "Jellyfin")

        assert mock_func.call_count == 4  # 1 initial + 3 retries
        assert "Persistent timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_does_not_retry_on_permanent_error(self) -> None:
        """Should NOT retry on permanent errors like 401, 404."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(401, request=request)
        auth_error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
        mock_func = AsyncMock(side_effect=auth_error)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await retry_with_backoff(mock_func, "Jellyfin")

        # Should not retry - only one call
        assert mock_func.call_count == 1
        assert exc_info.value.response.status_code == 401

    @pytest.mark.asyncio
    async def test_does_not_retry_on_404(self) -> None:
        """Should NOT retry on 404 Not Found."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(404, request=request)
        not_found_error = httpx.HTTPStatusError("Not found", request=request, response=response)
        mock_func = AsyncMock(side_effect=not_found_error)

        with pytest.raises(httpx.HTTPStatusError):
            await retry_with_backoff(mock_func, "Jellyfin")

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_500_errors(self) -> None:
        """Should retry on 500 Internal Server Error."""
        request = httpx.Request("GET", "http://example.com")
        response = httpx.Response(500, request=request)
        server_error = httpx.HTTPStatusError("Server error", request=request, response=response)

        # Fail twice with 500, then succeed
        mock_func = AsyncMock(side_effect=[
            server_error,
            server_error,
            "success",
        ])

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_backoff(mock_func, "Jellyfin")

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(self) -> None:
        """Should log each retry attempt with service name and delay."""
        mock_func = AsyncMock(side_effect=[
            httpx.TimeoutException("Timeout"),
            "success",
        ])

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock):
            with patch("app.services.retry.logger") as mock_logger:
                await retry_with_backoff(mock_func, "Jellyfin")

        # Should log the retry attempt
        mock_logger.warning.assert_called()
        call_args = str(mock_logger.warning.call_args)
        assert "Retry 1/3" in call_args
        assert "Jellyfin" in call_args

    @pytest.mark.asyncio
    async def test_error_message_includes_service_and_error_type(self) -> None:
        """Error message after exhausted retries should include service and error type."""
        timeout_error = httpx.TimeoutException("Connection timed out")
        mock_func = AsyncMock(side_effect=timeout_error)

        with patch("app.services.retry.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.TimeoutException):
                await retry_with_backoff(mock_func, "Jellyfin")

        # The original error is raised after all retries


class TestRetryConstants:
    """Test retry configuration constants."""

    def test_max_retries_is_three(self) -> None:
        """Should have 3 retries (4 total attempts)."""
        assert MAX_RETRIES == 3

    def test_initial_delay_is_one_second(self) -> None:
        """Initial delay should be 1 second."""
        assert INITIAL_DELAY == 1
