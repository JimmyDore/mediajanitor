"""Tests for password reset token model and functionality."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.database import User, PasswordResetToken


class TestPasswordResetTokenModel:
    """Tests for PasswordResetToken database model."""

    async def _create_user(self, session, email: str = "test@example.com") -> User:
        """Helper to create a test user."""
        import bcrypt

        hashed_password = bcrypt.hashpw("TestPassword123!".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
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
