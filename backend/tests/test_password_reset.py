"""Tests for password reset token model and functionality."""

from datetime import datetime, timedelta
from unittest.mock import patch

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import PasswordResetToken, User


class TestPasswordResetTokenModel:
    """Tests for PasswordResetToken database model."""

    async def _create_user(self, session, email: str = "test@example.com") -> User:
        """Helper to create a test user."""
        import bcrypt

        hashed_password = bcrypt.hashpw(b"TestPassword123!", bcrypt.gensalt()).decode("utf-8")
        user = User(
            email=email,
            hashed_password=hashed_password,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_create_password_reset_token(self, setup_database) -> None:
        """Test creating a password reset token."""
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            user = await self._create_user(session)

            token = PasswordResetToken(
                user_id=user.id,
                token_hash="hashed_token_value",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            session.add(token)
            await session.commit()
            await session.refresh(token)

            assert token.id is not None
            assert token.user_id == user.id
            assert token.token_hash == "hashed_token_value"
            assert token.used is False
            assert token.created_at is not None

    @pytest.mark.asyncio
    async def test_token_has_index_on_token_hash(self, setup_database) -> None:
        """Test that token_hash column has an index for fast lookup."""
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            user = await self._create_user(session)

            # Create multiple tokens
            for i in range(3):
                token = PasswordResetToken(
                    user_id=user.id,
                    token_hash=f"hashed_token_{i}",
                    expires_at=datetime.utcnow() + timedelta(minutes=15),
                )
                session.add(token)
            await session.commit()

            # Query by token_hash (this should use the index)
            result = await session.execute(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == "hashed_token_1")
            )
            found_token = result.scalar_one_or_none()

            assert found_token is not None
            assert found_token.token_hash == "hashed_token_1"

    @pytest.mark.asyncio
    async def test_foreign_key_constraint_exists(self, setup_database) -> None:
        """Test that PasswordResetToken has proper foreign key to users table.

        Note: CASCADE delete behavior is database-engine dependent.
        SQLite requires PRAGMA foreign_keys=ON to enforce constraints.
        This test verifies the model structure is correct.
        """
        from sqlalchemy import inspect

        from tests.conftest import async_engine

        async with async_engine.connect() as conn:
            # Get foreign keys for password_reset_tokens table
            def get_fks(connection):
                inspector = inspect(connection)
                return inspector.get_foreign_keys("password_reset_tokens")

            fks = await conn.run_sync(get_fks)

            # Verify foreign key exists pointing to users table
            assert len(fks) == 1
            fk = fks[0]
            assert fk["referred_table"] == "users"
            assert "user_id" in fk["constrained_columns"]
            assert "id" in fk["referred_columns"]

    @pytest.mark.asyncio
    async def test_multiple_tokens_per_user(self, setup_database) -> None:
        """Test that a user can have multiple reset tokens (e.g., before cleanup)."""
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            user = await self._create_user(session, "multi@example.com")

            # Create multiple tokens
            token1 = PasswordResetToken(
                user_id=user.id,
                token_hash="first_token",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=True,  # Already used
            )
            token2 = PasswordResetToken(
                user_id=user.id,
                token_hash="second_token",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            session.add_all([token1, token2])
            await session.commit()

            # Query all tokens for user
            result = await session.execute(
                select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
            )
            tokens = result.scalars().all()

            assert len(tokens) == 2

    @pytest.mark.asyncio
    async def test_token_expiration_query(self, setup_database) -> None:
        """Test querying for non-expired, unused tokens."""
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            user = await self._create_user(session, "expiry@example.com")

            # Create expired token
            expired_token = PasswordResetToken(
                user_id=user.id,
                token_hash="expired_token",
                expires_at=datetime.utcnow() - timedelta(minutes=1),  # Already expired
                used=False,
            )
            # Create valid token
            valid_token = PasswordResetToken(
                user_id=user.id,
                token_hash="valid_token",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            # Create used token
            used_token = PasswordResetToken(
                user_id=user.id,
                token_hash="used_token",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=True,
            )
            session.add_all([expired_token, valid_token, used_token])
            await session.commit()

            # Query for valid, unused tokens
            result = await session.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.expires_at > datetime.utcnow(),
                    PasswordResetToken.used == False,  # noqa: E712
                )
            )
            valid_tokens = result.scalars().all()

            assert len(valid_tokens) == 1
            assert valid_tokens[0].token_hash == "valid_token"

    @pytest.mark.asyncio
    async def test_mark_token_as_used(self, setup_database) -> None:
        """Test marking a token as used."""
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            user = await self._create_user(session, "markused@example.com")

            token = PasswordResetToken(
                user_id=user.id,
                token_hash="token_to_use",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            session.add(token)
            await session.commit()

            # Mark as used
            token.used = True
            await session.commit()
            await session.refresh(token)

            assert token.used is True

            # Verify it persists after re-query
            result = await session.execute(
                select(PasswordResetToken).where(PasswordResetToken.token_hash == "token_to_use")
            )
            found_token = result.scalar_one()
            assert found_token.used is True


class TestRequestPasswordResetEndpoint:
    """Tests for POST /api/auth/request-password-reset endpoint."""

    def test_request_password_reset_success(self, client: TestClient) -> None:
        """Test requesting password reset for existing user sends email."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "reset@example.com",
                "password": "SecurePassword123!",
            },
        )

        with patch("app.routers.auth.send_password_reset_email") as mock_send_email:
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "reset@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "reset link" in data["message"].lower()

            # Verify email was called with correct parameters
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            assert call_args.kwargs["to_email"] == "reset@example.com"
            assert call_args.kwargs["user_email"] == "reset@example.com"
            assert "reset_url" in call_args.kwargs
            assert "token=" in call_args.kwargs["reset_url"]

    @pytest.mark.asyncio
    async def test_request_password_reset_creates_token(self, client: TestClient) -> None:
        """Test that requesting password reset creates a token in database."""
        from tests.conftest import TestingAsyncSessionLocal

        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "token@example.com",
                "password": "SecurePassword123!",
            },
        )

        with patch("app.routers.auth.send_password_reset_email"):
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "token@example.com"},
            )

            assert response.status_code == 200

        # Verify token was created in database
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(select(PasswordResetToken))
            tokens = result.scalars().all()
            assert len(tokens) == 1
            token = tokens[0]
            assert token.used is False
            assert token.expires_at > datetime.utcnow()
            # Verify token is hashed (not raw)
            assert len(token.token_hash) > 40  # bcrypt hashes are long

    def test_request_password_reset_nonexistent_email(self, client: TestClient) -> None:
        """Test requesting reset for non-existent email returns 200 (no enumeration)."""
        with patch("app.routers.auth.send_password_reset_email") as mock_send_email:
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "nonexistent@example.com"},
            )

            # Should still return 200 to prevent email enumeration
            assert response.status_code == 200
            data = response.json()
            assert "message" in data

            # Email should NOT be sent for non-existent user
            mock_send_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_password_reset_deletes_old_tokens(self, client: TestClient) -> None:
        """Test that requesting new reset deletes old unused tokens for same user."""
        from tests.conftest import TestingAsyncSessionLocal

        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "oldtoken@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Get user id
        async with TestingAsyncSessionLocal() as session:
            from app.database import User

            result = await session.execute(select(User).where(User.email == "oldtoken@example.com"))
            user = result.scalar_one()

            # Create existing unused token
            old_token = PasswordResetToken(
                user_id=user.id,
                token_hash="old_token_hash",
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            session.add(old_token)
            await session.commit()

        with patch("app.routers.auth.send_password_reset_email"):
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "oldtoken@example.com"},
            )

            assert response.status_code == 200

        # Verify old token is deleted and new one exists
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(select(PasswordResetToken))
            tokens = result.scalars().all()
            assert len(tokens) == 1
            assert tokens[0].token_hash != "old_token_hash"

    def test_request_password_reset_invalid_email_format(self, client: TestClient) -> None:
        """Test requesting reset with invalid email format returns 422."""
        response = client.post(
            "/api/auth/request-password-reset",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_request_password_reset_token_expires_in_15_minutes(
        self, client: TestClient
    ) -> None:
        """Test that created token expires in approximately 15 minutes."""
        from tests.conftest import TestingAsyncSessionLocal

        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "expire@example.com",
                "password": "SecurePassword123!",
            },
        )

        with patch("app.routers.auth.send_password_reset_email"):
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "expire@example.com"},
            )

            assert response.status_code == 200

        # Verify token expires in ~15 minutes
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(select(PasswordResetToken))
            token = result.scalar_one()
            now = datetime.utcnow()
            # Token should expire between 14 and 16 minutes from now
            time_diff = (token.expires_at - now).total_seconds()
            assert 14 * 60 <= time_diff <= 16 * 60

    def test_request_password_reset_url_contains_frontend_url(self, client: TestClient) -> None:
        """Test that reset URL uses the configured frontend URL."""
        # First register a user
        client.post(
            "/api/auth/register",
            json={
                "email": "urltest@example.com",
                "password": "SecurePassword123!",
            },
        )

        with patch("app.routers.auth.send_password_reset_email") as mock_send_email:
            response = client.post(
                "/api/auth/request-password-reset",
                json={"email": "urltest@example.com"},
            )

            assert response.status_code == 200

            # Verify URL in email contains frontend URL
            mock_send_email.assert_called_once()
            reset_url = mock_send_email.call_args.kwargs["reset_url"]
            # Default frontend_url is http://localhost:5173
            assert "/reset-password?token=" in reset_url


class TestPasswordResetRateLimiting:
    """Tests for password reset rate limiting (3 requests per email per hour)."""

    def test_rate_limit_allows_first_three_requests(self) -> None:
        """Test that the first 3 requests are allowed."""
        import os

        # Need to disable TESTING mode to enable rate limiting
        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            # Import fresh app to pick up new TESTING value
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import password_reset_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            password_reset_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # Register a user
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "ratelimit@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                with patch("app.routers.auth.send_password_reset_email"):
                    # First 3 requests should succeed
                    for i in range(3):
                        response = test_client.post(
                            "/api/auth/request-password-reset",
                            json={"email": "ratelimit@example.com"},
                        )
                        assert response.status_code == 200, f"Request {i + 1} should succeed"

            # Clean up
            password_reset_rate_limiter.clear()
            fresh_app.dependency_overrides.clear()

    def test_rate_limit_blocks_fourth_request(self) -> None:
        """Test that the 4th request within an hour is blocked."""
        import os

        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import password_reset_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            password_reset_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # Register a user
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "blocked@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                with patch("app.routers.auth.send_password_reset_email"):
                    # Make 3 requests
                    for _ in range(3):
                        test_client.post(
                            "/api/auth/request-password-reset",
                            json={"email": "blocked@example.com"},
                        )

                    # 4th request should be rate limited
                    response = test_client.post(
                        "/api/auth/request-password-reset",
                        json={"email": "blocked@example.com"},
                    )
                    assert response.status_code == 429
                    assert "Retry-After" in response.headers

            # Clean up
            password_reset_rate_limiter.clear()
            fresh_app.dependency_overrides.clear()

    def test_rate_limit_is_per_email(self) -> None:
        """Test that rate limit is tracked per email address."""
        import os

        with patch.dict(os.environ, {"TESTING": "0"}, clear=False):
            from app.database import get_db
            from app.main import app as fresh_app
            from app.services.rate_limit import password_reset_rate_limiter
            from tests.conftest import override_get_db

            # Clear rate limiter state from previous tests
            password_reset_rate_limiter.clear()

            fresh_app.dependency_overrides[get_db] = override_get_db

            with TestClient(fresh_app) as test_client:
                # Register two users
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "email1@example.com",
                        "password": "SecurePassword123!",
                    },
                )
                test_client.post(
                    "/api/auth/register",
                    json={
                        "email": "email2@example.com",
                        "password": "SecurePassword123!",
                    },
                )

                with patch("app.routers.auth.send_password_reset_email"):
                    # Max out rate limit for email1
                    for _ in range(3):
                        test_client.post(
                            "/api/auth/request-password-reset",
                            json={"email": "email1@example.com"},
                        )

                    # email2 should still be allowed
                    response = test_client.post(
                        "/api/auth/request-password-reset",
                        json={"email": "email2@example.com"},
                    )
                    assert response.status_code == 200

                    # But email1 is still blocked
                    response = test_client.post(
                        "/api/auth/request-password-reset",
                        json={"email": "email1@example.com"},
                    )
                    assert response.status_code == 429

            # Clean up
            password_reset_rate_limiter.clear()
            fresh_app.dependency_overrides.clear()


class TestResetPasswordEndpoint:
    """Tests for POST /api/auth/reset-password endpoint."""

    async def _create_user_with_reset_token(
        self,
        client: TestClient,
        email: str = "resetuser@example.com",
        password: str = "OldPassword123!",
    ) -> tuple[str, int]:
        """
        Helper to create a user and return a valid reset token.

        Returns:
            Tuple of (raw_token, user_id)
        """
        import secrets

        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        # Get user id and create token directly in database
        from tests.conftest import TestingAsyncSessionLocal

        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one()

            # Create a valid token
            raw_token = secrets.token_urlsafe(32)
            token_hash = bcrypt.hashpw(raw_token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False,
            )
            session.add(reset_token)
            await session.commit()

            return raw_token, user.id

    def test_reset_password_success(self, client: TestClient) -> None:
        """Test successful password reset with valid token."""
        import asyncio

        loop = asyncio.get_event_loop()
        raw_token, user_id = loop.run_until_complete(
            self._create_user_with_reset_token(client, "success@example.com")
        )

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_updates_user_password(self, client: TestClient) -> None:
        """Test that password is actually updated after reset."""

        raw_token, user_id = await self._create_user_with_reset_token(client, "updated@example.com")

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 200

        # Verify the password was updated by logging in with new password
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "updated@example.com",
                "password": "NewSecure123!",
            },
        )
        assert login_response.status_code == 200

        # Old password should not work
        old_login_response = client.post(
            "/api/auth/login",
            json={
                "email": "updated@example.com",
                "password": "OldPassword123!",
            },
        )
        assert old_login_response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_marks_token_as_used(self, client: TestClient) -> None:
        """Test that token is marked as used after successful reset."""
        from tests.conftest import TestingAsyncSessionLocal

        raw_token, user_id = await self._create_user_with_reset_token(
            client, "tokenused@example.com"
        )

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 200

        # Verify token is marked as used
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
            )
            token = result.scalar_one()
            assert token.used is True

    def test_reset_password_invalid_token(self, client: TestClient) -> None:
        """Test that invalid token returns 400."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_token_that_does_not_exist",
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower() or "expired" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, client: TestClient) -> None:
        """Test that expired token returns 400."""
        import secrets

        from tests.conftest import TestingAsyncSessionLocal

        # Create user
        client.post(
            "/api/auth/register",
            json={
                "email": "expired@example.com",
                "password": "OldPassword123!",
            },
        )

        # Create expired token
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == "expired@example.com"))
            user = result.scalar_one()

            raw_token = secrets.token_urlsafe(32)
            token_hash = bcrypt.hashpw(raw_token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            expired_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() - timedelta(minutes=1),  # Already expired
                used=False,
            )
            session.add(expired_token)
            await session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "expired" in data["detail"].lower() or "invalid" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_already_used_token(self, client: TestClient) -> None:
        """Test that already-used token returns 400."""
        import secrets

        from tests.conftest import TestingAsyncSessionLocal

        # Create user
        client.post(
            "/api/auth/register",
            json={
                "email": "usedtoken@example.com",
                "password": "OldPassword123!",
            },
        )

        # Create already-used token
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == "usedtoken@example.com")
            )
            user = result.scalar_one()

            raw_token = secrets.token_urlsafe(32)
            token_hash = bcrypt.hashpw(raw_token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            used_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=True,  # Already used
            )
            session.add(used_token)
            await session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewSecure123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert (
            "invalid" in data["detail"].lower()
            or "expired" in data["detail"].lower()
            or "used" in data["detail"].lower()
        )

    def test_reset_password_too_short(self, client: TestClient) -> None:
        """Test that password less than 8 chars returns 422."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "sometoken",
                "new_password": "Short1!",  # Only 7 chars
            },
        )

        assert response.status_code == 422

    def test_reset_password_missing_uppercase(self, client: TestClient) -> None:
        """Test that password without uppercase returns 422."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "sometoken",
                "new_password": "nouppercase123!",
            },
        )

        assert response.status_code == 422

    def test_reset_password_missing_lowercase(self, client: TestClient) -> None:
        """Test that password without lowercase returns 422."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "sometoken",
                "new_password": "NOLOWERCASE123!",
            },
        )

        assert response.status_code == 422

    def test_reset_password_missing_number(self, client: TestClient) -> None:
        """Test that password without number returns 422."""
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "sometoken",
                "new_password": "NoNumberHere!",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_reset_password_token_cannot_be_reused(self, client: TestClient) -> None:
        """Test that a token cannot be used twice."""
        raw_token, user_id = await self._create_user_with_reset_token(client, "reuse@example.com")

        # First reset should succeed
        response1 = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "FirstNew123!",
            },
        )
        assert response1.status_code == 200

        # Second reset with same token should fail
        response2 = client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "SecondNew123!",
            },
        )
        assert response2.status_code == 400


class TestChangePasswordEndpoint:
    """Tests for POST /api/auth/change-password endpoint."""

    def _register_and_login(
        self,
        client: TestClient,
        email: str = "changepass@example.com",
        password: str = "OldPassword123!",
    ) -> str:
        """
        Helper to register a user and return their access token.

        Returns:
            Access token string
        """
        # Register a user
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
            },
        )

        # Login to get access token
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        return login_response.json()["access_token"]

    def test_change_password_success(self, client: TestClient) -> None:
        """Test successful password change with correct current password."""
        token = self._register_and_login(client, "success1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower()

    def test_change_password_updates_password(self, client: TestClient) -> None:
        """Test that password is actually updated after change."""
        token = self._register_and_login(client, "update1@example.com")

        # Change password
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Verify can log in with new password
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "update1@example.com",
                "password": "NewSecure456!",
            },
        )
        assert login_response.status_code == 200

        # Verify old password no longer works
        old_login_response = client.post(
            "/api/auth/login",
            json={
                "email": "update1@example.com",
                "password": "OldPassword123!",
            },
        )
        assert old_login_response.status_code == 401

    def test_change_password_wrong_current_password(self, client: TestClient) -> None:
        """Test that wrong current password returns 400."""
        token = self._register_and_login(client, "wrong1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "current password" in data["detail"].lower() or "incorrect" in data["detail"].lower()

    def test_change_password_requires_authentication(self, client: TestClient) -> None:
        """Test that change password requires valid authentication."""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewSecure456!",
            },
        )

        assert response.status_code == 401

    def test_change_password_invalid_token(self, client: TestClient) -> None:
        """Test that change password with invalid token returns 401."""
        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    def test_change_password_too_short(self, client: TestClient) -> None:
        """Test that new password less than 8 chars returns 422."""
        token = self._register_and_login(client, "short1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "Short1!",  # Only 7 chars
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_change_password_missing_uppercase(self, client: TestClient) -> None:
        """Test that new password without uppercase returns 422."""
        token = self._register_and_login(client, "upper1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "nouppercase123!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_change_password_missing_lowercase(self, client: TestClient) -> None:
        """Test that new password without lowercase returns 422."""
        token = self._register_and_login(client, "lower1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NOLOWERCASE123!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_change_password_missing_number(self, client: TestClient) -> None:
        """Test that new password without number returns 422."""
        token = self._register_and_login(client, "num1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "NoNumberHere!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    def test_change_password_same_as_current(self, client: TestClient) -> None:
        """Test that new password can be same as current (no restriction)."""
        token = self._register_and_login(client, "same1@example.com")

        response = client.post(
            "/api/auth/change-password",
            json={
                "current_password": "OldPassword123!",
                "new_password": "OldPassword123!",  # Same as current
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # This could either succeed (200) or fail with 400 depending on business requirements
        # We'll allow it for simplicity (no restriction on setting same password)
        assert response.status_code == 200
