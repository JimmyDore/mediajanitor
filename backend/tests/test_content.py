"""Tests for content analysis endpoints (US-3.1)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import User, CachedMediaItem, ContentWhitelist
from tests.conftest import TestingAsyncSessionLocal


class TestOldUnwatchedContent:
    """Test GET /api/content/old-unwatched endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "content@example.com") -> str:
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

    def test_requires_authentication(self, client: TestClient) -> None:
        """GET /api/content/old-unwatched should require authentication."""
        response = client.get("/api/content/old-unwatched")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_cached_items(
        self, client: TestClient
    ) -> None:
        """Should return empty list when no cached items exist."""
        token = self._get_auth_token(client, "empty@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["total_size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_returns_never_watched_content_older_than_min_age(
        self, client: TestClient
    ) -> None:
        """Should return content that was never watched and added more than 3 months ago."""
        token = self._get_auth_token(client, "unwatched@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Get user ID from auth
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create cached items directly in DB
        async with TestingAsyncSessionLocal() as session:
            # Item 1: Never watched, added 4 months ago (should appear)
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-unwatched",
                name="Old Unwatched Movie",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Old Movie",
                size_bytes=10_000_000_000,  # 10GB
                played=False,
                play_count=0,
                last_played_date=None,
            )
            # Item 2: Never watched, but added recently (should NOT appear)
            recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-recent-unwatched",
                name="Recent Unwatched Movie",
                media_type="Movie",
                production_year=2023,
                date_created=recent_date,
                path="/media/movies/Recent Movie",
                size_bytes=8_000_000_000,
                played=False,
                play_count=0,
                last_played_date=None,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["jellyfin_id"] == "movie-old-unwatched"
        assert data["items"][0]["name"] == "Old Unwatched Movie"

    @pytest.mark.asyncio
    async def test_returns_content_not_watched_in_4_months(
        self, client: TestClient
    ) -> None:
        """Should return content last watched more than 4 months ago."""
        token = self._get_auth_token(client, "oldwatch@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Item: Watched, but 5 months ago (should appear)
            old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            old_watched_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-watched",
                name="Old Watched Movie",
                media_type="Movie",
                production_year=2019,
                date_created=old_date,
                path="/media/movies/Old Watched",
                size_bytes=15_000_000_000,  # 15GB
                played=True,
                play_count=1,
                last_played_date=old_watched_date,
            )
            # Item: Watched recently (should NOT appear)
            recent_watched = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-recent-watched",
                name="Recently Watched Movie",
                media_type="Movie",
                production_year=2022,
                date_created=old_date,
                path="/media/movies/Recent Watched",
                size_bytes=12_000_000_000,
                played=True,
                play_count=3,
                last_played_date=recent_watched,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-old-watched"

    @pytest.mark.asyncio
    async def test_excludes_whitelisted_content(
        self, client: TestClient
    ) -> None:
        """Should not return content that is in user's whitelist."""
        token = self._get_auth_token(client, "whitelist@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create old unwatched content
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-protected",
                name="Protected Movie",
                media_type="Movie",
                production_year=2018,
                date_created=old_date,
                path="/media/movies/Protected",
                size_bytes=10_000_000_000,
                played=False,
                play_count=0,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-not-protected",
                name="Not Protected Movie",
                media_type="Movie",
                production_year=2017,
                date_created=old_date,
                path="/media/movies/Not Protected",
                size_bytes=8_000_000_000,
                played=False,
                play_count=0,
            )
            # Add item1 to whitelist
            whitelist_entry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-protected",
                name="Protected Movie",
                media_type="Movie",
            )
            session.add_all([item1, item2, whitelist_entry])
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-not-protected"

    @pytest.mark.asyncio
    async def test_sorted_by_size_descending(
        self, client: TestClient
    ) -> None:
        """Items should be sorted by size, largest first."""
        token = self._get_auth_token(client, "sorted@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Small item
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-small",
                name="Small Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=1_000_000_000,  # 1GB
                played=False,
            )
            # Large item
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large",
                name="Large Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=20_000_000_000,  # 20GB
                played=False,
            )
            # Medium item
            item3 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-medium",
                name="Medium Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,  # 5GB
                played=False,
            )
            session.add_all([item1, item2, item3])
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 3
        # Should be sorted: large, medium, small
        assert data["items"][0]["jellyfin_id"] == "movie-large"
        assert data["items"][1]["jellyfin_id"] == "movie-medium"
        assert data["items"][2]["jellyfin_id"] == "movie-small"

    @pytest.mark.asyncio
    async def test_returns_all_required_fields(
        self, client: TestClient
    ) -> None:
        """Each item should have all required fields."""
        token = self._get_auth_token(client, "fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-fields",
                name="Test Movie",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Test Movie/movie.mkv",
                size_bytes=10_000_000_000,
                played=False,
                last_played_date=None,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item = data["items"][0]
        # Required fields per acceptance criteria
        assert "jellyfin_id" in item
        assert "name" in item
        assert "media_type" in item
        assert "production_year" in item
        assert "size_bytes" in item
        assert "size_formatted" in item
        assert "last_played_date" in item
        assert "path" in item

    @pytest.mark.asyncio
    async def test_calculates_total_size(
        self, client: TestClient
    ) -> None:
        """Should calculate total size of all items."""
        token = self._get_auth_token(client, "totalsize@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-1",
                name="Movie 1",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,  # 10GB
                played=False,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-2",
                name="Movie 2",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,  # 5GB
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_size_bytes"] == 15_000_000_000
        assert "total_size_formatted" in data

    @pytest.mark.asyncio
    async def test_user_only_sees_their_own_content(
        self, client: TestClient
    ) -> None:
        """User should only see their own cached content, not other users'."""
        token1 = self._get_auth_token(client, "user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # User 1's content
            item1 = CachedMediaItem(
                user_id=me1["id"],
                jellyfin_id="user1-movie",
                name="User 1 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            # User 2's content
            item2 = CachedMediaItem(
                user_id=me2["id"],
                jellyfin_id="user2-movie",
                name="User 2 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=8_000_000_000,
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        # User 1 should only see their own content
        response1 = client.get("/api/content/old-unwatched", headers=headers1)
        data1 = response1.json()
        assert data1["total_count"] == 1
        assert data1["items"][0]["jellyfin_id"] == "user1-movie"

        # User 2 should only see their own content
        response2 = client.get("/api/content/old-unwatched", headers=headers2)
        data2 = response2.json()
        assert data2["total_count"] == 1
        assert data2["items"][0]["jellyfin_id"] == "user2-movie"


class TestContentWhitelistModel:
    """Test ContentWhitelist database model."""

    @pytest.mark.asyncio
    async def test_content_whitelist_model_exists(self, client: TestClient) -> None:
        """ContentWhitelist model should exist with required fields."""
        async with TestingAsyncSessionLocal() as session:
            entry = ContentWhitelist(
                user_id=1,
                jellyfin_id="test-123",
                name="Protected Content",
                media_type="Movie",
            )
            session.add(entry)
            await session.commit()
            assert entry.id is not None
            assert entry.created_at is not None
