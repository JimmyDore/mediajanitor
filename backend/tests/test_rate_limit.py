"""Tests for rate limiting on auth endpoints."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestRateLimitingLogin:
    """Tests for rate limiting on POST /api/auth/login endpoint."""

    def test_login_within_rate_limit_succeeds(self, client: TestClient) -> None:
        """Test that requests within rate limit succeed."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "ratelimit@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Make a few login requests - should all succeed
        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "ratelimit@example.com",
                    "password": "SecurePassword123!",
                },
            )
            assert response.status_code == 200

    def test_login_rate_limit_returns_429(self) -> None:
        """Test that exceeding rate limit returns 429 Too Many Requests."""
        # Need to disable TESTING mode to enable rate limiting
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            # Import fresh app to pick up new TESTING value
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import login_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            login_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # First register a user
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "ratelimitexceed@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                # Make 10 login requests (at the limit)
                for i in range(10):
                    response = test_client.post(
                        "/api/auth/login",
                        json={
                            "email": "ratelimitexceed@example.com",
                            "password": "SecurePassword123!",
                        },
                    )
                    # First 10 should succeed (even if password wrong)
                    assert response.status_code in (200, 401), (
                        f"Request {i + 1} failed unexpectedly"
                    )

                # 11th request should be rate limited
                response = test_client.post(
                    "/api/auth/login",
                    json={
                        "email": "ratelimitexceed@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 429

            fresh_app.dependency_overrides.clear()

    def test_login_rate_limit_includes_retry_after_header(self) -> None:
        """Test that rate limited response includes Retry-After header."""
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import login_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            login_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "retryafter@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                # Make 10 requests to reach limit
                for _ in range(10):
                    test_client.post(
                        "/api/auth/login",
                        json={
                            "email": "retryafter@example.com",
                            "password": "SecurePassword123!",
                        },
                    )

                # 11th request should have Retry-After header
                response = test_client.post(
                    "/api/auth/login",
                    json={
                        "email": "retryafter@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 429
                assert "Retry-After" in response.headers
                retry_after = int(response.headers["Retry-After"])
                assert retry_after > 0
                assert retry_after <= 60  # Should be within the 1-minute window

            fresh_app.dependency_overrides.clear()

    def test_login_rate_limit_error_message(self) -> None:
        """Test that rate limited response has clear error message."""
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import login_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            login_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "errormsg@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                # Exceed rate limit
                for _ in range(10):
                    test_client.post(
                        "/api/auth/login",
                        json={
                            "email": "errormsg@example.com",
                            "password": "SecurePassword123!",
                        },
                    )

                response = test_client.post(
                    "/api/auth/login",
                    json={
                        "email": "errormsg@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 429
                data = response.json()
                assert "detail" in data
                assert "too many requests" in data["detail"].lower()

            fresh_app.dependency_overrides.clear()


class TestRateLimitingRegister:
    """Tests for rate limiting on POST /api/auth/register endpoint."""

    def test_register_within_rate_limit_succeeds(self, client: TestClient) -> None:
        """Test that registration requests within rate limit succeed."""
        # Make a few registration requests - should all succeed or fail for normal reasons
        for i in range(5):
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"regtest{i}@example.com",
                    "password": "SecurePassword123!",
                },
            )
            # Should succeed (201) or fail for duplicate (400), not rate limited
            assert response.status_code in (201, 400)

    def test_register_rate_limit_returns_429(self) -> None:
        """Test that exceeding rate limit on register returns 429."""
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import register_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            register_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # Make 10 register requests (at the limit)
                for i in range(10):
                    response = test_client.post(
                        "/api/auth/register",
                        json={
                            "email": f"reglimit{i}@example.com",
                            "password": "SecurePassword123!",
                        },
                    )
                    # Should succeed or fail normally, not rate limited yet
                    assert response.status_code in (201, 400, 422)

                # 11th request should be rate limited
                response = test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "reglimit10@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 429

            fresh_app.dependency_overrides.clear()

    def test_register_rate_limit_includes_retry_after_header(self) -> None:
        """Test that rate limited register response includes Retry-After header."""
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import register_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            register_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # Exceed rate limit
                for i in range(10):
                    test_client.post(
                        "/api/auth/register",
                        json={
                            "email": f"regretry{i}@example.com",
                            "password": "SecurePassword123!",
                        },
                    )

                response = test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "regretry10@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 429
                assert "Retry-After" in response.headers

            fresh_app.dependency_overrides.clear()


class TestRateLimitingExclusions:
    """Tests to verify endpoints that should NOT be rate limited."""

    def test_me_endpoint_not_rate_limited(self, client: TestClient) -> None:
        """Test that /api/auth/me is not rate limited (authenticated requests only)."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={
                "email": "nolimit@example.com",
                "password": "SecurePassword123!",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "nolimit@example.com",
                "password": "SecurePassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Make many requests to /me - should all succeed
        for _ in range(20):
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200


class TestRateLimitingDisabledInTests:
    """Tests to verify rate limiting is disabled in test environment."""

    def test_rate_limiting_disabled_when_testing_env_set(self, client: TestClient) -> None:
        """Test that rate limiting is disabled when TESTING=1."""
        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "testenv@example.com",
                "password": "SecurePassword123!",
            },
        )

        # With TESTING=1 (default in tests), we should be able to make many requests
        for i in range(15):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "testenv@example.com",
                    "password": "SecurePassword123!",
                },
            )
            # Should never get 429 with TESTING=1
            assert response.status_code != 429, f"Got 429 on request {i + 1} despite TESTING=1"
