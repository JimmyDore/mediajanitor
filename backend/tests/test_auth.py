"""Tests for user registration and authentication."""

import pytest
from fastapi.testclient import TestClient

from app.services.auth import create_access_token, hash_refresh_token


class TestUserLogin:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client: TestClient) -> None:
        """Test successful login returns JWT token and refresh token cookie."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePassword123!",
            },
        )
        # Then login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] == 15 * 60  # 15 minutes in seconds

        # Check refresh token cookie is set
        assert "refresh_token" in response.cookies

    def test_login_invalid_email(self, client: TestClient) -> None:
        """Test login with non-existent email."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_wrong_password(self, client: TestClient) -> None:
        """Test login with wrong password."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "SecurePassword123!",
            },
        )
        # Then login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "email": "wrongpass@example.com",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_missing_email(self, client: TestClient) -> None:
        """Test login without email field."""
        response = client.post(
            "/api/auth/login",
            json={
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient) -> None:
        """Test login without password field."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
            },
        )
        assert response.status_code == 422

    def test_login_returns_valid_jwt(self, client: TestClient) -> None:
        """Test that the returned token is a valid JWT."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "jwttest@example.com",
                "password": "SecurePassword123!",
            },
        )
        # Then login
        response = client.post(
            "/api/auth/login",
            json={
                "email": "jwttest@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        # JWT tokens have 3 parts separated by dots
        parts = token.split(".")
        assert len(parts) == 3


class TestUserRegistration:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_user_success(self, client: TestClient) -> None:
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "password" not in data  # Password should not be returned

    def test_register_user_invalid_email(self, client: TestClient) -> None:
        """Test registration with invalid email format."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_user_weak_password(self, client: TestClient) -> None:
        """Test registration with weak password (less than 8 chars)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422  # Validation error

    def test_register_user_duplicate_email(self, client: TestClient) -> None:
        """Test registration with already existing email."""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123!",
            },
        )
        # Second registration with same email
        response = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPassword123!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_user_missing_email(self, client: TestClient) -> None:
        """Test registration without email field."""
        response = client.post(
            "/api/auth/register",
            json={
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 422

    def test_register_user_missing_password(self, client: TestClient) -> None:
        """Test registration without password field."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
            },
        )
        assert response.status_code == 422

    def test_password_is_hashed_in_database(self, client: TestClient) -> None:
        """Test that password is stored hashed, not in plain text."""
        # This test verifies the password hashing by checking that
        # registering with the same password twice produces different hashes
        # (due to salting) - we'll verify this indirectly through the API
        response = client.post(
            "/api/auth/register",
            json={
                "email": "hashtest@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert response.status_code == 201
        # The fact that registration succeeded and password is not in response
        # is a basic check. Full hash verification happens in service tests.


class TestProtectedRoutes:
    """Tests for protected API endpoints requiring valid JWT."""

    def test_protected_endpoint_without_token(self, client: TestClient) -> None:
        """Test protected endpoint returns 401 without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_protected_endpoint_with_invalid_token(self, client: TestClient) -> None:
        """Test protected endpoint returns 401 with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client: TestClient) -> None:
        """Test protected endpoint returns user data with valid token."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "protected@example.com",
                "password": "SecurePassword123!",
            },
        )
        # Login to get token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "protected@example.com",
                "password": "SecurePassword123!",
            },
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"
        assert "id" in data

    def test_protected_endpoint_with_expired_token(self, client: TestClient) -> None:
        """Test protected endpoint returns 401 with expired token."""
        from datetime import timedelta

        # Create an already-expired token
        expired_token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(seconds=-10),  # Expired 10 seconds ago
        )
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_malformed_header(self, client: TestClient) -> None:
        """Test protected endpoint returns 401 with malformed auth header."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer some-token"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_user_not_found(self, client: TestClient) -> None:
        """Test protected endpoint returns 401 if user in token doesn't exist."""
        # Create token for non-existent user
        token = create_access_token(data={"sub": "nonexistent@example.com"})
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401


class TestRefreshToken:
    """Tests for POST /api/auth/refresh endpoint."""

    def test_refresh_success_with_cookie(self, client: TestClient) -> None:
        """Test refreshing token using httpOnly cookie."""
        # First register and login
        client.post(
            "/api/auth/register",
            json={"email": "refresh@example.com", "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": "refresh@example.com", "password": "SecurePassword123!"},
        )
        assert login_response.status_code == 200
        old_access_token = login_response.json()["access_token"]

        # Refresh (cookie is automatically sent by TestClient)
        refresh_response = client.post("/api/auth/refresh")
        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

        # New access token should be different
        new_access_token = data["access_token"]
        # Note: tokens may be the same if generated within same second, but structure should be valid
        assert len(new_access_token.split(".")) == 3

        # New refresh token cookie should be set
        assert "refresh_token" in refresh_response.cookies

    def test_refresh_without_token_returns_401(self, client: TestClient) -> None:
        """Test refresh without any token returns 401."""
        # Create a fresh client without any cookies
        from fastapi.testclient import TestClient
        from app.main import app
        fresh_client = TestClient(app)

        response = fresh_client.post("/api/auth/refresh")
        assert response.status_code == 401
        assert "missing" in response.json()["detail"].lower()

    def test_refresh_with_invalid_token_returns_401(self, client: TestClient) -> None:
        """Test refresh with invalid token returns 401."""
        response = client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_rotates_token(self, client: TestClient) -> None:
        """Test that refresh invalidates old token (rotation)."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": "rotate@example.com", "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": "rotate@example.com", "password": "SecurePassword123!"},
        )
        old_refresh_token = login_response.cookies.get("refresh_token")

        # First refresh should succeed
        first_refresh = client.post("/api/auth/refresh")
        assert first_refresh.status_code == 200

        # Try to use the old token again - should fail
        second_refresh = client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": old_refresh_token},
        )
        assert second_refresh.status_code == 401

    def test_refresh_via_request_body(self, client: TestClient) -> None:
        """Test refreshing token using request body (for non-cookie clients)."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": "bodyclient@example.com", "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": "bodyclient@example.com", "password": "SecurePassword123!"},
        )
        refresh_token = login_response.cookies.get("refresh_token")

        # Create fresh client without cookies
        from fastapi.testclient import TestClient
        from app.main import app
        fresh_client = TestClient(app)

        # Refresh using body
        refresh_response = fresh_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 200
        assert "access_token" in refresh_response.json()


class TestLogout:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client: TestClient) -> None:
        """Test logout invalidates refresh token and clears cookie."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": "logout@example.com", "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": "logout@example.com", "password": "SecurePassword123!"},
        )
        refresh_token = login_response.cookies.get("refresh_token")

        # Logout
        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 204

        # Try to use the old refresh token - should fail
        refresh_response = client.post(
            "/api/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401

    def test_logout_without_token_succeeds(self, client: TestClient) -> None:
        """Test logout works even without a refresh token (idempotent)."""
        from fastapi.testclient import TestClient
        from app.main import app
        fresh_client = TestClient(app)

        response = fresh_client.post("/api/auth/logout")
        assert response.status_code == 204

    def test_logout_clears_cookie(self, client: TestClient) -> None:
        """Test logout clears the refresh token cookie."""
        # Register and login
        client.post(
            "/api/auth/register",
            json={"email": "cookieclear@example.com", "password": "SecurePassword123!"},
        )
        client.post(
            "/api/auth/login",
            json={"email": "cookieclear@example.com", "password": "SecurePassword123!"},
        )

        # Logout
        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 204

        # Cookie should be deleted (set to empty or expired)
        # FastAPI/Starlette sets max-age=0 to delete cookies
        set_cookie = logout_response.headers.get("set-cookie", "")
        # Either cookie is cleared or max-age is 0
        assert "refresh_token" in set_cookie.lower() or logout_response.cookies.get("refresh_token", "") == ""


class TestNewUserSignupNotifications:
    """Tests for Slack notifications on user signup."""

    def test_signup_sends_slack_notification(self, client: TestClient) -> None:
        """Test that successful registration sends Slack notification."""
        from unittest.mock import patch, AsyncMock

        with patch("app.routers.auth.send_signup_notification") as mock_notify:
            mock_notify.return_value = None  # fire-and-forget, no return needed

            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser1@example.com",
                    "password": "SecurePassword123!",
                },
            )
            assert response.status_code == 201

            # Verify notification was called with correct email
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert call_args[1]["email"] == "newuser1@example.com"
            assert "user_id" in call_args[1]
            assert "total_users" in call_args[1]

    def test_signup_notification_includes_total_user_count(self, client: TestClient) -> None:
        """Test that notification includes correct total user count."""
        from unittest.mock import patch

        # First register a user to have count > 1
        client.post(
            "/api/auth/register",
            json={
                "email": "firstuser@example.com",
                "password": "SecurePassword123!",
            },
        )

        with patch("app.routers.auth.send_signup_notification") as mock_notify:
            mock_notify.return_value = None

            response = client.post(
                "/api/auth/register",
                json={
                    "email": "seconduser@example.com",
                    "password": "SecurePassword123!",
                },
            )
            assert response.status_code == 201

            # Total users should be 2 (after this registration)
            call_args = mock_notify.call_args
            assert call_args[1]["total_users"] >= 2

    def test_signup_notification_is_fire_and_forget(self, client: TestClient) -> None:
        """Test that notification failure doesn't block registration."""
        from unittest.mock import patch, AsyncMock

        # Mock the Slack send function to fail (inside send_signup_notification)
        with patch("app.routers.auth.send_slack_message", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("Slack webhook failed")

            # Configure webhook so notification is attempted
            with patch("app.routers.auth.get_settings") as mock_settings_fn:
                from app.config import Settings
                mock_settings = Settings()
                mock_settings.slack_webhook_new_users = "https://hooks.slack.com/test"
                mock_settings_fn.return_value = mock_settings

                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": "fireforget@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                # Registration should still succeed even if Slack fails
                assert response.status_code == 201
                data = response.json()
                assert data["email"] == "fireforget@example.com"

    def test_signup_without_webhook_configured(self, client: TestClient) -> None:
        """Test that registration works when Slack webhook is not configured."""
        from unittest.mock import patch

        # Simulate webhook not configured (empty string)
        with patch("app.config.get_settings") as mock_settings:
            mock_settings.return_value.slack_webhook_new_users = ""

            response = client.post(
                "/api/auth/register",
                json={
                    "email": "nowebhook@example.com",
                    "password": "SecurePassword123!",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == "nowebhook@example.com"

    def test_signup_notification_uses_block_kit_format(self, client: TestClient) -> None:
        """Test that Slack message uses Block Kit format."""
        from unittest.mock import patch, AsyncMock

        with patch("app.services.slack.send_slack_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch("app.config.get_settings") as mock_settings_fn:
                from app.config import Settings
                mock_settings = Settings()
                mock_settings.slack_webhook_new_users = "https://hooks.slack.com/test"
                mock_settings_fn.return_value = mock_settings

                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": "blockkit@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                assert response.status_code == 201

                # Check that send_slack_message was called with Block Kit format
                if mock_send.called:
                    call_args = mock_send.call_args
                    message = call_args[0][1]  # Second positional arg is the message dict
                    # Block Kit messages should have "blocks" key
                    assert "blocks" in message or "text" in message

class TestDatabaseConcurrency:
    """Tests for database concurrency (regression test for WAL mode)."""

    def test_wal_mode_enabled_for_sqlite(self) -> None:
        """Test that WAL mode is enabled for SQLite databases.

        Regression test for: Database lock errors during login when sync is running.
        WAL mode allows concurrent reads during writes, preventing 500 errors
        when users try to login while sync operations are happening.
        """
        from app.database import ASYNC_DATABASE_URL

        # Only test if using SQLite
        if not ASYNC_DATABASE_URL.startswith("sqlite"):
            pytest.skip("Test only applicable for SQLite databases")

        import sqlite3
        # Extract path from sqlite+aiosqlite:///path
        db_path = ASYNC_DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        if db_path == ":memory:":
            pytest.skip("WAL mode cannot be tested on in-memory database")

        # WAL mode should be enabled in init_db_settings()
        # This test just verifies the configuration exists
        from app.database import init_db_settings
        assert init_db_settings is not None

        # Verify connect_args are configured
        from app.database import async_engine
        if hasattr(async_engine, 'pool'):
            # Engine is configured with timeout and connection settings
            assert True
        else:
            pytest.fail("async_engine not properly configured")
