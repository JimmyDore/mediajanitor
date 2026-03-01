"""Tests for re-whitelisting items after expiration.

Verifies that expired whitelist entries are cleaned up and replaced
when a user re-whitelists the same item, instead of blocking with
a 'already in whitelist' error.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    ContentWhitelist,
    EpisodeLanguageExempt,
    JellyseerrRequestWhitelist,
)
from tests.conftest import TestingAsyncSessionLocal


class TestRewhitelistAfterExpiration:
    """Test that expired whitelist entries don't block re-whitelisting."""

    def _get_auth_token(self, client: TestClient, email: str) -> str:
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

    def _get_user_id(self, client: TestClient, headers: dict) -> int:
        me_response = client.get("/api/auth/me", headers=headers)
        return me_response.json()["id"]

    # ----------------------------------------------------------------
    # BaseJellyfinIdWhitelistService (content whitelist)
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_can_rewhitelist_content_after_expiration(self, client: TestClient) -> None:
        """Adding to content whitelist should succeed when existing entry is expired."""
        token = self._get_auth_token(client, "rewhitelist-content@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        # Insert an expired whitelist entry directly in DB
        async with TestingAsyncSessionLocal() as session:
            expired_entry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-rewhitelist",
                name="Movie To Rewhitelist",
                media_type="Movie",
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
            session.add(expired_entry)
            await session.commit()

        # Re-whitelisting the same item should succeed (not 409)
        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-rewhitelist",
                "name": "Movie To Rewhitelist",
                "media_type": "Movie",
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == 201

        # Verify old entry was replaced - only one entry should exist
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentWhitelist).where(
                    ContentWhitelist.user_id == user_id,
                    ContentWhitelist.jellyfin_id == "movie-rewhitelist",
                )
            )
            entries = result.scalars().all()
            assert len(entries) == 1
            # The new entry should have a future expiration
            assert entries[0].expires_at is not None

    @pytest.mark.asyncio
    async def test_non_expired_content_still_blocks_duplicate(self, client: TestClient) -> None:
        """Adding to content whitelist should still fail when existing entry is NOT expired."""
        token = self._get_auth_token(client, "noexpire-content@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        # Insert a still-valid whitelist entry
        async with TestingAsyncSessionLocal() as session:
            valid_entry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-still-valid",
                name="Still Valid Movie",
                media_type="Movie",
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add(valid_entry)
            await session.commit()

        # Should still get 409
        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-still-valid",
                "name": "Still Valid Movie",
                "media_type": "Movie",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_permanent_content_still_blocks_duplicate(self, client: TestClient) -> None:
        """Adding to content whitelist should still fail when existing entry is permanent."""
        token = self._get_auth_token(client, "permanent-content2@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        # Insert a permanent whitelist entry (expires_at=None)
        async with TestingAsyncSessionLocal() as session:
            permanent_entry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-permanent",
                name="Permanent Movie",
                media_type="Movie",
                expires_at=None,
            )
            session.add(permanent_entry)
            await session.commit()

        # Should still get 409
        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-permanent",
                "name": "Permanent Movie",
                "media_type": "Movie",
            },
        )
        assert response.status_code == 409

    # ----------------------------------------------------------------
    # BaseJellyseerrIdWhitelistService (request whitelist)
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_can_rewhitelist_request_after_expiration(self, client: TestClient) -> None:
        """Adding to request whitelist should succeed when existing entry is expired."""
        token = self._get_auth_token(client, "rewhitelist-request@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        # Insert an expired request whitelist entry
        async with TestingAsyncSessionLocal() as session:
            expired_entry = JellyseerrRequestWhitelist(
                user_id=user_id,
                jellyseerr_id=999,
                title="Expired Request",
                media_type="movie",
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
            session.add(expired_entry)
            await session.commit()

        # Re-whitelisting should succeed
        response = client.post(
            "/api/whitelist/requests",
            headers=headers,
            json={
                "jellyseerr_id": 999,
                "title": "Expired Request",
                "media_type": "movie",
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == 201

        # Verify only one entry exists
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(JellyseerrRequestWhitelist).where(
                    JellyseerrRequestWhitelist.user_id == user_id,
                    JellyseerrRequestWhitelist.jellyseerr_id == 999,
                )
            )
            entries = result.scalars().all()
            assert len(entries) == 1
            assert entries[0].expires_at is not None

    @pytest.mark.asyncio
    async def test_non_expired_request_still_blocks_duplicate(self, client: TestClient) -> None:
        """Adding to request whitelist should still fail when existing entry is NOT expired."""
        token = self._get_auth_token(client, "noexpire-request@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        async with TestingAsyncSessionLocal() as session:
            valid_entry = JellyseerrRequestWhitelist(
                user_id=user_id,
                jellyseerr_id=888,
                title="Valid Request",
                media_type="movie",
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add(valid_entry)
            await session.commit()

        response = client.post(
            "/api/whitelist/requests",
            headers=headers,
            json={
                "jellyseerr_id": 888,
                "title": "Valid Request",
                "media_type": "movie",
            },
        )
        assert response.status_code == 409

    # ----------------------------------------------------------------
    # EpisodeLanguageExempt (custom add function)
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_can_rewhitelist_episode_after_expiration(self, client: TestClient) -> None:
        """Adding episode exempt should succeed when existing entry is expired."""
        token = self._get_auth_token(client, "rewhitelist-episode@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        # Insert an expired episode exempt entry
        async with TestingAsyncSessionLocal() as session:
            expired_entry = EpisodeLanguageExempt(
                user_id=user_id,
                jellyfin_id="series-rewhitelist",
                series_name="Test Series",
                season_number=1,
                episode_number=5,
                episode_name="Expired Episode",
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
            session.add(expired_entry)
            await session.commit()

        # Re-exempting should succeed
        response = client.post(
            "/api/whitelist/episode-exempt",
            headers=headers,
            json={
                "jellyfin_id": "series-rewhitelist",
                "series_name": "Test Series",
                "season_number": 1,
                "episode_number": 5,
                "episode_name": "Expired Episode",
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == 201

        # Verify only one entry exists
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(EpisodeLanguageExempt).where(
                    EpisodeLanguageExempt.user_id == user_id,
                    EpisodeLanguageExempt.jellyfin_id == "series-rewhitelist",
                    EpisodeLanguageExempt.season_number == 1,
                    EpisodeLanguageExempt.episode_number == 5,
                )
            )
            entries = result.scalars().all()
            assert len(entries) == 1
            assert entries[0].expires_at is not None

    @pytest.mark.asyncio
    async def test_non_expired_episode_still_blocks_duplicate(self, client: TestClient) -> None:
        """Adding episode exempt should still fail when existing entry is NOT expired."""
        token = self._get_auth_token(client, "noexpire-episode@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        user_id = self._get_user_id(client, headers)

        async with TestingAsyncSessionLocal() as session:
            valid_entry = EpisodeLanguageExempt(
                user_id=user_id,
                jellyfin_id="series-valid-ep",
                series_name="Valid Series",
                season_number=2,
                episode_number=3,
                episode_name="Valid Episode",
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add(valid_entry)
            await session.commit()

        response = client.post(
            "/api/whitelist/episode-exempt",
            headers=headers,
            json={
                "jellyfin_id": "series-valid-ep",
                "series_name": "Valid Series",
                "season_number": 2,
                "episode_number": 3,
                "episode_name": "Valid Episode",
            },
        )
        assert response.status_code == 409
