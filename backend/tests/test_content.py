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


class TestAddToContentWhitelist:
    """Test POST /api/whitelist/content endpoint (US-3.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "whitelist@example.com") -> str:
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
        """POST /api/whitelist/content should require authentication."""
        response = client.post(
            "/api/whitelist/content",
            json={
                "jellyfin_id": "movie-123",
                "name": "Test Movie",
                "media_type": "Movie"
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_adds_content_to_whitelist(self, client: TestClient) -> None:
        """Should add content to user's whitelist and return success."""
        token = self._get_auth_token(client, "add-whitelist@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-123",
                "name": "Test Movie",
                "media_type": "Movie"
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to whitelist"
        assert data["jellyfin_id"] == "movie-123"
        assert data["name"] == "Test Movie"

    @pytest.mark.asyncio
    async def test_whitelist_entry_persisted_to_database(self, client: TestClient) -> None:
        """Whitelist entry should be stored in database."""
        token = self._get_auth_token(client, "persist-whitelist@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Get user ID
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Add to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-persist",
                "name": "Persisted Movie",
                "media_type": "Movie"
            },
        )

        # Verify in database
        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentWhitelist).where(
                    ContentWhitelist.user_id == user_id,
                    ContentWhitelist.jellyfin_id == "movie-persist"
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.name == "Persisted Movie"
            assert entry.media_type == "Movie"

    @pytest.mark.asyncio
    async def test_protected_item_disappears_from_old_content_list(
        self, client: TestClient
    ) -> None:
        """After adding to whitelist, item should not appear in old content list."""
        token = self._get_auth_token(client, "protect-disappear@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create old unwatched content
        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-to-protect",
                name="Movie To Protect",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            session.add(item)
            await session.commit()

        # Verify item appears in old content list
        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert any(i["jellyfin_id"] == "movie-to-protect" for i in items)

        # Add to whitelist
        protect_response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-to-protect",
                "name": "Movie To Protect",
                "media_type": "Movie"
            },
        )
        assert protect_response.status_code == 201

        # Verify item no longer appears in old content list
        response = client.get("/api/content/old-unwatched", headers=headers)
        assert response.status_code == 200
        items = response.json()["items"]
        assert not any(i["jellyfin_id"] == "movie-to-protect" for i in items)

    @pytest.mark.asyncio
    async def test_prevents_duplicate_whitelist_entries(self, client: TestClient) -> None:
        """Should not create duplicate entries for same jellyfin_id."""
        token = self._get_auth_token(client, "duplicate-whitelist@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add first time
        response1 = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-duplicate",
                "name": "Duplicate Movie",
                "media_type": "Movie"
            },
        )
        assert response1.status_code == 201

        # Try to add again
        response2 = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-duplicate",
                "name": "Duplicate Movie",
                "media_type": "Movie"
            },
        )
        # Should return 409 Conflict
        assert response2.status_code == 409
        assert "already in whitelist" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_validates_required_fields(self, client: TestClient) -> None:
        """Should validate that all required fields are provided."""
        token = self._get_auth_token(client, "validate-whitelist@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Missing jellyfin_id
        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "name": "Test Movie",
                "media_type": "Movie"
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_user_isolation(self, client: TestClient) -> None:
        """Users should only be able to see their own whitelist entries."""
        token1 = self._get_auth_token(client, "user1-wl@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "user2-wl@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()

        # User 1 adds to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers1,
            json={
                "jellyfin_id": "user1-movie",
                "name": "User 1 Movie",
                "media_type": "Movie"
            },
        )

        # Create old content for both users
        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Same jellyfin_id for both users
            item1 = CachedMediaItem(
                user_id=me1["id"],
                jellyfin_id="user1-movie",
                name="User 1 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            item2 = CachedMediaItem(
                user_id=me2["id"],
                jellyfin_id="user1-movie",  # Same jellyfin_id
                name="User 1 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        # User 1's whitelist should protect User 1's content
        response1 = client.get("/api/content/old-unwatched", headers=headers1)
        assert not any(i["jellyfin_id"] == "user1-movie" for i in response1.json()["items"])

        # User 2's content with same jellyfin_id should NOT be protected
        response2 = client.get("/api/content/old-unwatched", headers=headers2)
        assert any(i["jellyfin_id"] == "user1-movie" for i in response2.json()["items"])


class TestGetContentWhitelist:
    """Test GET /api/whitelist/content endpoint (US-3.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "whitelist@example.com") -> str:
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
        """GET /api/whitelist/content should require authentication."""
        response = client.get("/api/whitelist/content")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_whitelist_items(
        self, client: TestClient
    ) -> None:
        """Should return empty list when user has no whitelist entries."""
        token = self._get_auth_token(client, "empty-wl@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/whitelist/content", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_returns_user_whitelist_items(self, client: TestClient) -> None:
        """Should return all items in user's whitelist."""
        token = self._get_auth_token(client, "get-wl@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Get user ID
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create whitelist entries directly in DB
        async with TestingAsyncSessionLocal() as session:
            entry1 = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-wl-1",
                name="Whitelisted Movie 1",
                media_type="Movie",
            )
            entry2 = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="series-wl-1",
                name="Whitelisted Series 1",
                media_type="Series",
            )
            session.add_all([entry1, entry2])
            await session.commit()

        response = client.get("/api/whitelist/content", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["items"]) == 2

        # Check both items are present
        jellyfin_ids = [item["jellyfin_id"] for item in data["items"]]
        assert "movie-wl-1" in jellyfin_ids
        assert "series-wl-1" in jellyfin_ids

    @pytest.mark.asyncio
    async def test_returns_all_required_fields(self, client: TestClient) -> None:
        """Each whitelist item should have required fields: id, name, media_type, created_at."""
        token = self._get_auth_token(client, "wl-fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add item to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-fields-test",
                "name": "Fields Test Movie",
                "media_type": "Movie"
            },
        )

        response = client.get("/api/whitelist/content", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item = data["items"][0]
        assert "id" in item
        assert "jellyfin_id" in item
        assert "name" in item
        assert "media_type" in item
        assert "created_at" in item

    @pytest.mark.asyncio
    async def test_user_only_sees_their_own_whitelist(self, client: TestClient) -> None:
        """User should only see their own whitelist, not other users'."""
        token1 = self._get_auth_token(client, "wl-user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "wl-user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 adds to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers1,
            json={
                "jellyfin_id": "user1-wl-movie",
                "name": "User 1 WL Movie",
                "media_type": "Movie"
            },
        )

        # User 2 adds different item to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers2,
            json={
                "jellyfin_id": "user2-wl-movie",
                "name": "User 2 WL Movie",
                "media_type": "Movie"
            },
        )

        # User 1 should only see their item
        response1 = client.get("/api/whitelist/content", headers=headers1)
        data1 = response1.json()
        assert data1["total_count"] == 1
        assert data1["items"][0]["jellyfin_id"] == "user1-wl-movie"

        # User 2 should only see their item
        response2 = client.get("/api/whitelist/content", headers=headers2)
        data2 = response2.json()
        assert data2["total_count"] == 1
        assert data2["items"][0]["jellyfin_id"] == "user2-wl-movie"


class TestDeleteFromContentWhitelist:
    """Test DELETE /api/whitelist/content/{id} endpoint (US-3.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "whitelist@example.com") -> str:
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
        """DELETE /api/whitelist/content/{id} should require authentication."""
        response = client.delete("/api/whitelist/content/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_removes_item_from_whitelist(self, client: TestClient) -> None:
        """Should remove item from user's whitelist."""
        token = self._get_auth_token(client, "delete-wl@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add item to whitelist first
        add_response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-to-delete",
                "name": "Movie To Delete",
                "media_type": "Movie"
            },
        )
        assert add_response.status_code == 201

        # Get the whitelist to find the item ID
        list_response = client.get("/api/whitelist/content", headers=headers)
        item_id = list_response.json()["items"][0]["id"]

        # Delete the item
        delete_response = client.delete(f"/api/whitelist/content/{item_id}", headers=headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Removed from whitelist"

        # Verify item is gone from whitelist
        list_response = client.get("/api/whitelist/content", headers=headers)
        assert list_response.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_item(self, client: TestClient) -> None:
        """Should return 404 when trying to delete non-existent whitelist item."""
        token = self._get_auth_token(client, "delete-404@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/api/whitelist/content/99999", headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cannot_delete_other_users_whitelist_items(
        self, client: TestClient
    ) -> None:
        """User should not be able to delete another user's whitelist items."""
        token1 = self._get_auth_token(client, "delete-user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "delete-user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        # User 1 adds to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers1,
            json={
                "jellyfin_id": "user1-delete-movie",
                "name": "User 1 Delete Movie",
                "media_type": "Movie"
            },
        )

        # Get user 1's whitelist item ID
        list_response = client.get("/api/whitelist/content", headers=headers1)
        item_id = list_response.json()["items"][0]["id"]

        # User 2 tries to delete user 1's item - should get 404
        delete_response = client.delete(f"/api/whitelist/content/{item_id}", headers=headers2)
        assert delete_response.status_code == 404

        # Verify user 1's item still exists
        list_response = client.get("/api/whitelist/content", headers=headers1)
        assert list_response.json()["total_count"] == 1

    @pytest.mark.asyncio
    async def test_removed_item_reappears_in_old_content_list(
        self, client: TestClient
    ) -> None:
        """After removing from whitelist, item should reappear in old content list if still old."""
        token = self._get_auth_token(client, "reappear@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Get user ID
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create old unwatched content
        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-reappear",
                name="Movie Reappear",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            session.add(item)
            await session.commit()

        # Add to whitelist
        client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-reappear",
                "name": "Movie Reappear",
                "media_type": "Movie"
            },
        )

        # Verify item does NOT appear in old content list
        old_content = client.get("/api/content/old-unwatched", headers=headers)
        assert not any(i["jellyfin_id"] == "movie-reappear" for i in old_content.json()["items"])

        # Get whitelist item ID and delete
        list_response = client.get("/api/whitelist/content", headers=headers)
        item_id = list_response.json()["items"][0]["id"]
        client.delete(f"/api/whitelist/content/{item_id}", headers=headers)

        # Verify item NOW appears in old content list
        old_content = client.get("/api/content/old-unwatched", headers=headers)
        assert any(i["jellyfin_id"] == "movie-reappear" for i in old_content.json()["items"])
