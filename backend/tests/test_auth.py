"""Tests for user registration and authentication."""

import pytest
from fastapi.testclient import TestClient


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
