"""Retry utility with exponential backoff for transient API failures."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3  # 3 retries = 4 total attempts
INITIAL_DELAY = 1  # Initial delay in seconds (doubles each retry: 1, 2, 4)

T = TypeVar("T")


def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient and should be retried.

    Transient errors (SHOULD retry):
    - Timeout errors
    - Connection errors (ConnectError, ReadError)
    - 5xx HTTP status errors (server-side issues)

    Permanent errors (should NOT retry):
    - 401 Unauthorized (auth failed)
    - 403 Forbidden
    - 404 Not Found
    - 400 Bad Request
    - Other 4xx client errors

    Args:
        error: The exception to check

    Returns:
        True if the error is transient and should be retried
    """
    # Timeout errors are transient
    if isinstance(error, httpx.TimeoutException):
        return True

    # Connection errors are transient
    if isinstance(error, (httpx.ConnectError, httpx.ReadError)):
        return True

    # HTTP status errors - check status code
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        # 5xx errors are server-side and transient
        return status_code >= 500

    return False


async def retry_with_backoff(
    func: Callable[[], Coroutine[Any, Any, T]],
    service_name: str,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY,
) -> T:
    """
    Execute an async function with retry logic and exponential backoff.

    Retries only on transient errors (timeouts, 5xx, connection errors).
    Does NOT retry on permanent errors (401, 404, 400, etc.).

    Args:
        func: Async function to execute (no arguments, use partial/closure for params)
        service_name: Name of service for logging (e.g., "Jellyfin", "Jellyseerr")
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (doubles each retry)

    Returns:
        The result of the function if successful

    Raises:
        The last exception if all retries are exhausted or if error is not transient
    """
    last_error: Exception | None = None
    delay = initial_delay

    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            return await func()
        except Exception as e:
            last_error = e

            # Check if error is retryable
            if not is_transient_error(e):
                # Permanent error - raise immediately without retry
                raise

            # Check if we have retries left
            retries_remaining = max_retries - attempt
            if retries_remaining <= 0:
                # All retries exhausted
                logger.error(f"{service_name} API failed after {max_retries + 1} attempts: {e}")
                raise

            # Log retry attempt
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {service_name} API after {delay}s... "
                f"(Error: {type(e).__name__}: {e})"
            )

            # Wait with exponential backoff
            await asyncio.sleep(delay)
            delay *= 2  # Double delay for next retry

    # Should never reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in retry_with_backoff")
