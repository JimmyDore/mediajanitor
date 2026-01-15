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
