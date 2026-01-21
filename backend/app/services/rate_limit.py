"""Rate limiting service with in-memory storage."""

import os
import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class RateLimitRecord:
    """Record of requests from an IP address."""

    count: int
    window_start: float


class RateLimiter:
    """
    In-memory rate limiter using a sliding window.

    Limits requests per IP address within a time window.
    Thread-safe for concurrent access.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._records: dict[str, RateLimitRecord] = {}
        self._lock = Lock()

    def _is_testing(self) -> bool:
        """Check if we're running in test environment."""
        return os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

    def is_rate_limited(self, key: str) -> tuple[bool, int]:
        """
        Check if a key (usually IP address) is rate limited.

        Args:
            key: Identifier for the client (typically IP address)

        Returns:
            Tuple of (is_limited, retry_after_seconds)
            - is_limited: True if the key has exceeded the rate limit
            - retry_after_seconds: Seconds until the window resets (0 if not limited)
        """
        # Disable rate limiting in test environment
        if self._is_testing():
            return False, 0

        current_time = time.time()

        with self._lock:
            if key in self._records:
                record = self._records[key]
                time_elapsed = current_time - record.window_start

                # Check if window has expired
                if time_elapsed >= self.window_seconds:
                    # Start new window
                    self._records[key] = RateLimitRecord(count=1, window_start=current_time)
                    return False, 0

                # Window still active - check count
                if record.count >= self.max_requests:
                    # Rate limited
                    retry_after = int(self.window_seconds - time_elapsed) + 1
                    return True, retry_after

                # Increment count
                record.count += 1
                return False, 0
            else:
                # First request from this key
                self._records[key] = RateLimitRecord(count=1, window_start=current_time)
                return False, 0

    def clear(self) -> None:
        """Clear all rate limit records (for testing)."""
        with self._lock:
            self._records.clear()


# Global rate limiter instances for auth endpoints
# 10 requests per minute per IP
login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
register_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Password reset rate limiter: 3 requests per email per hour
# Note: This limiter is keyed by email address, not IP address
password_reset_rate_limiter = RateLimiter(max_requests=3, window_seconds=3600)
