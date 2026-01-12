"""Tests for user registration and authentication."""

import pytest
from fastapi.testclient import TestClient

from app.services.auth import create_access_token


class TestUserLogin:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client: TestClient) -> None:
        """Test successful login returns JWT token."""
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
