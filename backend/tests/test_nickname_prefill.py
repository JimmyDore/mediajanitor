"""Tests for nickname prefill during sync (US-37.1)."""

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import User, UserSettings, UserNickname
from tests.conftest import TestingAsyncSessionLocal


class TestNicknamePrefillModel:
    """Test UserNickname model has has_jellyseerr_account field."""

    @pytest.mark.asyncio
    async def test_user_nickname_has_jellyseerr_account_field(self, client: TestClient) -> None:
        """UserNickname model should have has_jellyseerr_account boolean field."""
        async with TestingAsyncSessionLocal() as session:
            # Create a user first
            user = User(
                email="test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create nickname with has_jellyseerr_account
            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="testuser",
                display_name="Test User",
                has_jellyseerr_account=True,
            )
            session.add(nickname)
            await session.commit()

            assert nickname.id is not None
            assert nickname.has_jellyseerr_account is True

    @pytest.mark.asyncio
    async def test_user_nickname_defaults_to_false(self, client: TestClient) -> None:
        """has_jellyseerr_account should default to False."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="test2@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # Create nickname without setting has_jellyseerr_account
            nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="testuser2",
                display_name="Test User 2",
            )
            session.add(nickname)
            await session.commit()

            # Should default to False
            assert nickname.has_jellyseerr_account is False


class TestNicknamePrefillDuringSync:
    """Test nickname prefill logic during sync."""

    @pytest.mark.asyncio
    async def test_sync_creates_nicknames_for_jellyfin_users(
        self,
        client: TestClient,
    ) -> None:
        """Sync should create nickname records for all Jellyfin users."""
        from sqlalchemy import select
        from app.services.sync import run_user_sync

        # Mock Jellyfin users response
        mock_jellyfin_users = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
            {"Id": "user3", "Name": "Bob"},
        ]

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="sync_prefill@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                with patch("app.services.sync.fetch_jellyfin_media_with_progress", return_value=[]):
                    with patch("app.services.sync.calculate_season_sizes"):
                        with patch("app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users):
                            with patch("app.services.sync.fetch_jellyseerr_users", return_value=[]):
                                await run_user_sync(session, user.id)

            # Check that nickname records were created
            result = await session.execute(
                select(UserNickname).where(UserNickname.user_id == user.id)
            )
            nicknames = result.scalars().all()

            assert len(nicknames) == 3
            usernames = {n.jellyseerr_username for n in nicknames}
            assert usernames == {"John", "Jane", "Bob"}

            # Display names should be empty (user fills them in)
            for nickname in nicknames:
                assert nickname.display_name == ""

    @pytest.mark.asyncio
    async def test_sync_marks_users_with_jellyseerr_account(
        self,
        client: TestClient,
    ) -> None:
        """Sync should mark users that have Jellyseerr accounts."""
        from sqlalchemy import select
        from app.services.sync import run_user_sync

        # Mock Jellyfin users
        mock_jellyfin_users = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
            {"Id": "user3", "Name": "Bob"},
        ]

        # Mock Jellyseerr users - only John and Bob have accounts
        mock_jellyseerr_users = [
            {"id": 1, "displayName": "John", "email": "john@example.com"},
            {"id": 2, "displayName": "Bob", "email": "bob@example.com"},
        ]

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="sync_mark@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                with patch("app.services.sync.fetch_jellyfin_media_with_progress", return_value=[]):
                    with patch("app.services.sync.calculate_season_sizes"):
                        with patch("app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users):
                            with patch("app.services.sync.fetch_jellyseerr_users", return_value=mock_jellyseerr_users):
                                with patch("app.services.sync.fetch_jellyseerr_requests", return_value=[]):
                                    await run_user_sync(session, user.id)

            # Check that has_jellyseerr_account is set correctly
            result = await session.execute(
                select(UserNickname).where(UserNickname.user_id == user.id)
            )
            nicknames = {n.jellyseerr_username: n for n in result.scalars().all()}

            assert nicknames["John"].has_jellyseerr_account is True
            assert nicknames["Jane"].has_jellyseerr_account is False  # Not in Jellyseerr
            assert nicknames["Bob"].has_jellyseerr_account is True

    @pytest.mark.asyncio
    async def test_sync_preserves_existing_nickname_mappings(
        self,
        client: TestClient,
    ) -> None:
        """Sync should NOT overwrite existing nickname mappings."""
        from sqlalchemy import select
        from app.services.sync import run_user_sync

        mock_jellyfin_users = [
            {"Id": "user1", "Name": "John"},
            {"Id": "user2", "Name": "Jane"},
        ]

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="sync_preserve@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)

            # Pre-existing nickname for John with a custom display name
            existing_nickname = UserNickname(
                user_id=user.id,
                jellyseerr_username="John",
                display_name="Johnny Boy",  # User's custom name
                has_jellyseerr_account=False,
            )
            session.add(existing_nickname)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                with patch("app.services.sync.fetch_jellyfin_media_with_progress", return_value=[]):
                    with patch("app.services.sync.calculate_season_sizes"):
                        with patch("app.services.sync.fetch_jellyfin_users", return_value=mock_jellyfin_users):
                            with patch("app.services.sync.fetch_jellyseerr_users", return_value=[]):
                                await run_user_sync(session, user.id)

            # Check that John's nickname was NOT overwritten
            result = await session.execute(
                select(UserNickname).where(
                    UserNickname.user_id == user.id,
                    UserNickname.jellyseerr_username == "John",
                )
            )
            john_nickname = result.scalar_one_or_none()

            assert john_nickname is not None
            assert john_nickname.display_name == "Johnny Boy"  # Preserved!

            # Jane should have been added
            result = await session.execute(
                select(UserNickname).where(
                    UserNickname.user_id == user.id,
                    UserNickname.jellyseerr_username == "Jane",
                )
            )
            jane_nickname = result.scalar_one_or_none()
            assert jane_nickname is not None
            assert jane_nickname.display_name == ""  # New entry has empty display name


class TestFetchJellyseerrUsers:
    """Test Jellyseerr users API fetch."""

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_users_returns_users_list(self) -> None:
        """fetch_jellyseerr_users should return list of users from API."""
        from app.services.sync import fetch_jellyseerr_users
        import httpx

        users_response = [
            {"id": 1, "displayName": "John", "email": "john@example.com"},
            {"id": 2, "displayName": "Jane", "email": "jane@example.com"},
            {"id": 3, "displayName": "Bob", "email": "bob@example.com"},
        ]

        async def mock_get(self_or_url, url_or_headers=None, **kwargs):
            response = httpx.Response(200, json=users_response)
            response.raise_for_status = lambda: None
            return response

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyseerr_users("http://jellyseerr.local", "api-key")

        assert len(users) == 3
        assert users[0]["displayName"] == "John"
        assert users[1]["displayName"] == "Jane"
        assert users[2]["displayName"] == "Bob"

    @pytest.mark.asyncio
    async def test_fetch_jellyseerr_users_handles_error_gracefully(self) -> None:
        """fetch_jellyseerr_users should return empty list on error."""
        from app.services.sync import fetch_jellyseerr_users
        import httpx

        async def mock_get(*args, **kwargs):
            raise httpx.RequestError("Connection failed")

        with patch("httpx.AsyncClient.get", new=mock_get):
            users = await fetch_jellyseerr_users("http://jellyseerr.local", "api-key")

        assert users == []


class TestNicknameAPIResponse:
    """Test that nickname API returns has_jellyseerr_account field."""

    def _get_auth_token(self, client: TestClient, email: str = "nickname_api@example.com") -> str:
        """Helper to register and login a user, returning JWT token."""
        client.post(
            "/api/auth/register",
            json={"email": email, "password": "SecurePassword123!"},
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        return login_response.json()["access_token"]

    def test_nickname_list_includes_has_jellyseerr_account(self, client: TestClient) -> None:
        """GET /api/settings/nicknames should return has_jellyseerr_account field."""
        token = self._get_auth_token(client, "nickname_api1@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Create a nickname
        client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "TestUser", "display_name": "Test Display"},
            headers=headers,
        )

        # Get nicknames
        response = client.get("/api/settings/nicknames", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert "has_jellyseerr_account" in data["items"][0]
        assert data["items"][0]["has_jellyseerr_account"] is False  # Default

    def test_create_nickname_returns_has_jellyseerr_account(self, client: TestClient) -> None:
        """POST /api/settings/nicknames should return has_jellyseerr_account in response."""
        token = self._get_auth_token(client, "nickname_api2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/settings/nicknames",
            json={"jellyseerr_username": "NewUser", "display_name": "New Display"},
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "has_jellyseerr_account" in data
        assert data["has_jellyseerr_account"] is False  # Default for manually created
