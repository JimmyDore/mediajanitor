"""Tests for content analysis endpoints (US-3.1)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import (
    User,
    CachedMediaItem,
    CachedJellyseerrRequest,
    ContentWhitelist,
    FrenchOnlyWhitelist,
    LanguageExemptWhitelist,
)
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
    async def test_min_age_only_applies_to_unplayed_items(
        self, client: TestClient
    ) -> None:
        """min_age_months should ONLY apply to unplayed items.

        Bug fix: Original script applies min_age check only to never-watched items.
        Played items should be checked against last_played_date regardless of when added.
        """
        token = self._get_auth_token(client, "minagefix@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Recently added date (1 month ago - within min_age window)
            recent_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            # Old watched date (5 months ago - outside months_cutoff window)
            old_watched_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()

            # Item 1: Added recently, PLAYED long ago -> SHOULD appear
            # min_age check should NOT apply to played items
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-recent-add-old-watch",
                name="Recent Add Old Watch Movie",
                media_type="Movie",
                production_year=2021,
                date_created=recent_date,
                path="/media/movies/Recent Add Old Watch",
                size_bytes=10_000_000_000,
                played=True,
                play_count=1,
                last_played_date=old_watched_date,
            )
            # Item 2: Added recently, NOT played -> should NOT appear (min_age applies)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-recent-add-unplayed",
                name="Recent Add Unplayed Movie",
                media_type="Movie",
                production_year=2023,
                date_created=recent_date,
                path="/media/movies/Recent Add Unplayed",
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

        # Only item1 should appear:
        # - item1 is played (min_age doesn't apply), last_played > 4 months ago -> appears
        # - item2 is unplayed AND recently added -> min_age applies, doesn't appear
        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-recent-add-old-watch"

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

    @pytest.mark.asyncio
    async def test_content_whitelist_has_expires_at_column(self, client: TestClient) -> None:
        """ContentWhitelist model should have nullable expires_at column."""
        from datetime import datetime, timezone, timedelta
        async with TestingAsyncSessionLocal() as session:
            # Test with expires_at set
            entry_with_expiry = ContentWhitelist(
                user_id=1,
                jellyfin_id="test-expiry-123",
                name="Temporary Protected",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )
            session.add(entry_with_expiry)
            await session.commit()
            assert entry_with_expiry.expires_at is not None

            # Test with expires_at None (permanent)
            entry_permanent = ContentWhitelist(
                user_id=1,
                jellyfin_id="test-permanent-123",
                name="Permanent Protected",
                media_type="Movie",
                expires_at=None,
            )
            session.add(entry_permanent)
            await session.commit()
            assert entry_permanent.expires_at is None


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


class TestContentSummary:
    """Test GET /api/content/summary endpoint (US-D.1)."""

    def _get_auth_token(self, client: TestClient, email: str = "summary@example.com") -> str:
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
        """GET /api/content/summary should require authentication."""
        response = client.get("/api/content/summary")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_all_zero_counts_when_no_data(
        self, client: TestClient
    ) -> None:
        """Should return all zero counts when user has no cached items."""
        token = self._get_auth_token(client, "empty-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # All issue counts should be zero
        assert data["old_content"]["count"] == 0
        assert data["old_content"]["total_size_bytes"] == 0
        assert data["large_movies"]["count"] == 0
        assert data["large_movies"]["total_size_bytes"] == 0
        assert data["language_issues"]["count"] == 0
        assert data["unavailable_requests"]["count"] == 0

    @pytest.mark.asyncio
    async def test_returns_old_content_count(
        self, client: TestClient
    ) -> None:
        """Should return correct count of old/unwatched content."""
        token = self._get_auth_token(client, "old-count@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old unwatched item
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-1",
                name="Old Movie 1",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,  # 10GB
                played=False,
            )
            # Another old unwatched item
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-2",
                name="Old Movie 2",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,  # 5GB
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["old_content"]["count"] == 2
        assert data["old_content"]["total_size_bytes"] == 15_000_000_000
        assert "total_size_formatted" in data["old_content"]

    @pytest.mark.asyncio
    async def test_returns_large_movies_count(
        self, client: TestClient
    ) -> None:
        """Should return correct count of large movies (>13GB)."""
        token = self._get_auth_token(client, "large-count@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Large movie (15GB)
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large-1",
                name="Large Movie 1",
                media_type="Movie",
                size_bytes=15_000_000_000,  # 15GB > 13GB threshold
                played=True,
            )
            # Normal size movie (10GB)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-normal",
                name="Normal Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,  # 10GB < 13GB threshold
                played=True,
            )
            # Another large movie (20GB)
            item3 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large-2",
                name="Large Movie 2",
                media_type="Movie",
                size_bytes=20_000_000_000,  # 20GB > 13GB threshold
                played=True,
            )
            session.add_all([item1, item2, item3])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["large_movies"]["count"] == 2
        assert data["large_movies"]["total_size_bytes"] == 35_000_000_000
        assert "total_size_formatted" in data["large_movies"]

    @pytest.mark.asyncio
    async def test_large_movies_only_counts_movies_not_series(
        self, client: TestClient
    ) -> None:
        """Large movies count should only include movies, not series."""
        token = self._get_auth_token(client, "large-movies-only@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Large movie
            movie = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large",
                name="Large Movie",
                media_type="Movie",
                size_bytes=20_000_000_000,
                played=True,
            )
            # Large series (should not count as "large movie")
            series = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-large",
                name="Large Series",
                media_type="Series",
                size_bytes=50_000_000_000,  # 50GB
                played=True,
            )
            session.add_all([movie, series])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Only the movie should be counted
        assert data["large_movies"]["count"] == 1
        assert data["large_movies"]["total_size_bytes"] == 20_000_000_000

    @pytest.mark.asyncio
    async def test_large_movies_includes_exactly_threshold(
        self, client: TestClient
    ) -> None:
        """Movies exactly at 13GB threshold should be counted (>= not >).

        This matches original_script.py list_large_movies() behavior which uses >=.
        """
        token = self._get_auth_token(client, "large-exact@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        threshold_bytes = 13 * 1024 * 1024 * 1024  # Exactly 13GB

        async with TestingAsyncSessionLocal() as session:
            # Movie exactly at threshold (13GB)
            item_exact = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-exact-threshold",
                name="Movie Exactly 13GB",
                media_type="Movie",
                size_bytes=threshold_bytes,  # Exactly 13GB
                played=True,
            )
            # Movie just below threshold
            item_below = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-below-threshold",
                name="Movie Below 13GB",
                media_type="Movie",
                size_bytes=threshold_bytes - 1,  # 1 byte below 13GB
                played=True,
            )
            session.add_all([item_exact, item_below])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Movie at exactly 13GB should be counted (>= operator)
        assert data["large_movies"]["count"] == 1
        assert data["large_movies"]["total_size_bytes"] == threshold_bytes

    @pytest.mark.asyncio
    async def test_excludes_whitelisted_content_from_old_count(
        self, client: TestClient
    ) -> None:
        """Whitelisted content should not be counted in old content."""
        token = self._get_auth_token(client, "whitelist-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old item 1 (will be whitelisted)
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-whitelisted",
                name="Whitelisted Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            # Old item 2 (not whitelisted)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-not-whitelisted",
                name="Not Whitelisted Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=8_000_000_000,
                played=False,
            )
            # Add whitelist entry for item1
            whitelist_entry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-whitelisted",
                name="Whitelisted Movie",
                media_type="Movie",
            )
            session.add_all([item1, item2, whitelist_entry])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Only non-whitelisted item should be counted
        assert data["old_content"]["count"] == 1
        assert data["old_content"]["total_size_bytes"] == 8_000_000_000

    @pytest.mark.asyncio
    async def test_user_isolation(
        self, client: TestClient
    ) -> None:
        """Each user should only see counts for their own content."""
        token1 = self._get_auth_token(client, "summary-user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "summary-user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # User 1's content: 1 old item
            item1 = CachedMediaItem(
                user_id=me1["id"],
                jellyfin_id="user1-movie",
                name="User 1 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=10_000_000_000,
                played=False,
            )
            # User 2's content: 2 old items
            item2 = CachedMediaItem(
                user_id=me2["id"],
                jellyfin_id="user2-movie-1",
                name="User 2 Movie 1",
                media_type="Movie",
                date_created=old_date,
                size_bytes=8_000_000_000,
                played=False,
            )
            item3 = CachedMediaItem(
                user_id=me2["id"],
                jellyfin_id="user2-movie-2",
                name="User 2 Movie 2",
                media_type="Movie",
                date_created=old_date,
                size_bytes=7_000_000_000,
                played=False,
            )
            session.add_all([item1, item2, item3])
            await session.commit()

        # User 1 should see only 1 old item
        response1 = client.get("/api/content/summary", headers=headers1)
        data1 = response1.json()
        assert data1["old_content"]["count"] == 1

        # User 2 should see 2 old items
        response2 = client.get("/api/content/summary", headers=headers2)
        data2 = response2.json()
        assert data2["old_content"]["count"] == 2

    @pytest.mark.asyncio
    async def test_returns_language_issues_count_placeholder(
        self, client: TestClient
    ) -> None:
        """Language issues count should be 0 (not implemented yet)."""
        token = self._get_auth_token(client, "language-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Language issues will be implemented in US-5.1, for now return 0
        assert data["language_issues"]["count"] == 0

    @pytest.mark.asyncio
    async def test_returns_unavailable_requests_count_placeholder(
        self, client: TestClient
    ) -> None:
        """Unavailable requests count should be 0 (not implemented yet)."""
        token = self._get_auth_token(client, "requests-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Unavailable requests will be implemented in US-6.1, for now return 0
        assert data["unavailable_requests"]["count"] == 0


class TestInfoEndpoints:
    """Test info endpoints for US-D.2 - Dashboard Info Section."""

    def _get_auth_token(self, client: TestClient, email: str = "info@example.com") -> str:
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

    def test_recently_available_requires_authentication(self, client: TestClient) -> None:
        """GET /api/info/recent should require authentication."""
        response = client.get("/api/info/recent")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_recently_available_returns_empty_list_when_no_data(
        self, client: TestClient
    ) -> None:
        """Should return empty list when no recently available content exists."""
        token = self._get_auth_token(client, "recent-empty@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/info/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_recently_available_returns_content_from_past_7_days(
        self, client: TestClient
    ) -> None:
        """Should return content that became available in the past 7 days."""
        from app.database import CachedJellyseerrRequest

        token = self._get_auth_token(client, "recent-7days@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Request available 3 days ago (should appear)
            recent_date = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            recent_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=1001,
                tmdb_id=12345,
                media_type="movie",
                status=5,  # Available
                title="Recently Available Movie",
                requested_by="test_user",
                created_at_source=recent_date,
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            # Request available 10 days ago (should NOT appear)
            old_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
            old_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=1002,
                tmdb_id=12346,
                media_type="movie",
                status=5,  # Available
                title="Old Available Movie",
                requested_by="test_user",
                created_at_source=old_date,
                raw_data={"media": {"mediaAddedAt": old_date}},
            )
            session.add_all([recent_request, old_request])
            await session.commit()

        response = client.get("/api/info/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["title"] == "Recently Available Movie"

    @pytest.mark.asyncio
    async def test_recently_available_only_shows_available_status(
        self, client: TestClient
    ) -> None:
        """Should only return requests with status 4 (Partially Available) or 5 (Available)."""
        from app.database import CachedJellyseerrRequest

        token = self._get_auth_token(client, "recent-status@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            # Available request (should appear)
            available_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2001,
                tmdb_id=22345,
                media_type="movie",
                status=5,  # Available
                title="Available Movie",
                requested_by="test_user",
                created_at_source=recent_date,
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            # Pending request (should NOT appear)
            pending_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2002,
                tmdb_id=22346,
                media_type="movie",
                status=2,  # Pending
                title="Pending Movie",
                requested_by="test_user",
                created_at_source=recent_date,
                raw_data={},
            )
            session.add_all([available_request, pending_request])
            await session.commit()

        response = client.get("/api/info/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["title"] == "Available Movie"

    @pytest.mark.asyncio
    async def test_recently_available_returns_required_fields(
        self, client: TestClient
    ) -> None:
        """Each item should have: title, type, availability_date."""
        from app.database import CachedJellyseerrRequest

        token = self._get_auth_token(client, "recent-fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=3001,
                tmdb_id=32345,
                media_type="movie",
                status=5,
                title="Field Test Movie",
                requested_by="test_user",
                created_at_source=recent_date,
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            session.add(request)
            await session.commit()

        response = client.get("/api/info/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item = data["items"][0]
        assert "title" in item
        assert "media_type" in item
        assert "availability_date" in item

    @pytest.mark.asyncio
    async def test_recently_available_grouped_by_date(
        self, client: TestClient
    ) -> None:
        """Items should be sorted by date, newest first."""
        from app.database import CachedJellyseerrRequest

        token = self._get_auth_token(client, "recent-sorted@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Item from 1 day ago
            day1 = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            # Item from 3 days ago
            day3 = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            # Item from 5 days ago
            day5 = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

            req1 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=4001,
                media_type="movie",
                status=5,
                title="Day 1 Movie",
                raw_data={"media": {"mediaAddedAt": day1}},
            )
            req2 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=4002,
                media_type="movie",
                status=5,
                title="Day 3 Movie",
                raw_data={"media": {"mediaAddedAt": day3}},
            )
            req3 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=4003,
                media_type="movie",
                status=5,
                title="Day 5 Movie",
                raw_data={"media": {"mediaAddedAt": day5}},
            )
            session.add_all([req3, req1, req2])  # Add in non-sorted order
            await session.commit()

        response = client.get("/api/info/recent", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should be sorted newest first
        assert data["items"][0]["title"] == "Day 1 Movie"
        assert data["items"][1]["title"] == "Day 3 Movie"
        assert data["items"][2]["title"] == "Day 5 Movie"

    @pytest.mark.asyncio
    async def test_summary_includes_recently_available_count(
        self, client: TestClient
    ) -> None:
        """GET /api/content/summary should include recently_available count."""
        from app.database import CachedJellyseerrRequest

        token = self._get_auth_token(client, "summary-info@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Add recent available request
            recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=5001,
                media_type="movie",
                status=5,
                title="Recent Movie",
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            session.add(request)
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Summary should include recently_available count
        assert "recently_available" in data
        assert data["recently_available"]["count"] == 1

    @pytest.mark.asyncio
    async def test_user_isolation_for_recently_available(
        self, client: TestClient
    ) -> None:
        """Users should only see their own recently available content."""
        from app.database import CachedJellyseerrRequest

        token1 = self._get_auth_token(client, "recent-user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "recent-user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()

        async with TestingAsyncSessionLocal() as session:
            recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            # User 1's request
            req1 = CachedJellyseerrRequest(
                user_id=me1["id"],
                jellyseerr_id=6001,
                media_type="movie",
                status=5,
                title="User 1 Movie",
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            # User 2's request
            req2 = CachedJellyseerrRequest(
                user_id=me2["id"],
                jellyseerr_id=6002,
                media_type="movie",
                status=5,
                title="User 2 Movie",
                raw_data={"media": {"mediaAddedAt": recent_date}},
            )
            session.add_all([req1, req2])
            await session.commit()

        # User 1 should only see their movie
        response1 = client.get("/api/info/recent", headers=headers1)
        data1 = response1.json()
        assert data1["total_count"] == 1
        assert data1["items"][0]["title"] == "User 1 Movie"

        # User 2 should only see their movie
        response2 = client.get("/api/info/recent", headers=headers2)
        data2 = response2.json()
        assert data2["total_count"] == 1
        assert data2["items"][0]["title"] == "User 2 Movie"


class TestUnifiedIssuesEndpoint:
    """Test GET /api/content/issues endpoint (US-D.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "issues@example.com") -> str:
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
        """GET /api/content/issues should require authentication."""
        response = client.get("/api/content/issues")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_issues(
        self, client: TestClient
    ) -> None:
        """Should return empty list when user has no content with issues."""
        token = self._get_auth_token(client, "issues-empty@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["total_size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_returns_all_issues_without_filter(
        self, client: TestClient
    ) -> None:
        """Should return all content with issues when no filter specified."""
        token = self._get_auth_token(client, "issues-all@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old unwatched movie
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old",
                name="Old Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,  # 5GB
                played=False,
            )
            # Large movie (15GB)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large",
                name="Large Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=15_000_000_000,  # 15GB > 13GB threshold
                played=True,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should return both items
        assert data["total_count"] == 2
        jellyfin_ids = [item["jellyfin_id"] for item in data["items"]]
        assert "movie-old" in jellyfin_ids
        assert "movie-large" in jellyfin_ids

    @pytest.mark.asyncio
    async def test_filter_by_old_content(
        self, client: TestClient
    ) -> None:
        """Should filter to only old content when filter=old."""
        token = self._get_auth_token(client, "issues-old@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old unwatched movie
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-filter",
                name="Old Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
            )
            # Large but recently watched movie (not old)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large-recent",
                name="Large Recent Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=15_000_000_000,
                played=True,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-old-filter"
        assert "old" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_filter_by_large_movies(
        self, client: TestClient
    ) -> None:
        """Should filter to only large movies when filter=large."""
        token = self._get_auth_token(client, "issues-large@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Small old movie
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-small-old",
                name="Small Old Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,  # 5GB
                played=False,
            )
            # Large movie
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large-filter",
                name="Large Movie",
                media_type="Movie",
                size_bytes=16_000_000_000,  # 16GB > 13GB
                played=True,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/content/issues?filter=large", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-large-filter"
        assert "large" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_item_shows_multiple_issues(
        self, client: TestClient
    ) -> None:
        """Content with multiple issues should show all applicable issue badges."""
        token = self._get_auth_token(client, "issues-multi@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old AND large movie
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-old-and-large",
                name="Old Large Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=20_000_000_000,  # 20GB > 13GB
                played=False,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        item_data = data["items"][0]
        assert "old" in item_data["issues"]
        assert "large" in item_data["issues"]

    @pytest.mark.asyncio
    async def test_excludes_whitelisted_from_old_issues(
        self, client: TestClient
    ) -> None:
        """Whitelisted content should be excluded from old content issues."""
        token = self._get_auth_token(client, "issues-wl@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            # Old movie (will be whitelisted)
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-whitelisted-old",
                name="Whitelisted Old Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
            )
            # Old movie (not whitelisted)
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-not-whitelisted-old",
                name="Not Whitelisted Old Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=6_000_000_000,
                played=False,
            )
            # Add whitelist entry
            whitelist = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-whitelisted-old",
                name="Whitelisted Old Movie",
                media_type="Movie",
            )
            session.add_all([item1, item2, whitelist])
            await session.commit()

        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-not-whitelisted-old"

    @pytest.mark.asyncio
    async def test_returns_all_required_fields(
        self, client: TestClient
    ) -> None:
        """Each item should have all required fields."""
        token = self._get_auth_token(client, "issues-fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-fields-test",
                name="Fields Test Movie",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Test/movie.mkv",
                size_bytes=10_000_000_000,
                played=False,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item_data = data["items"][0]
        # Required fields per acceptance criteria
        assert "jellyfin_id" in item_data
        assert "name" in item_data
        assert "media_type" in item_data
        assert "production_year" in item_data
        assert "size_bytes" in item_data
        assert "size_formatted" in item_data
        assert "last_played_date" in item_data
        assert "path" in item_data
        assert "issues" in item_data  # List of issue types
        assert isinstance(item_data["issues"], list)

    @pytest.mark.asyncio
    async def test_sorted_by_size_descending_by_default(
        self, client: TestClient
    ) -> None:
        """Items should be sorted by size (largest first) by default."""
        token = self._get_auth_token(client, "issues-sort@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-small",
                name="Small Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=3_000_000_000,  # 3GB
                played=False,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-large",
                name="Large Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=20_000_000_000,  # 20GB
                played=False,
            )
            item3 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-medium",
                name="Medium Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=8_000_000_000,  # 8GB
                played=False,
            )
            session.add_all([item1, item2, item3])
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should be sorted: large, medium, small
        assert data["items"][0]["jellyfin_id"] == "movie-large"
        assert data["items"][1]["jellyfin_id"] == "movie-medium"
        assert data["items"][2]["jellyfin_id"] == "movie-small"

    @pytest.mark.asyncio
    async def test_calculates_total_size(
        self, client: TestClient
    ) -> None:
        """Should calculate total size of all items with issues."""
        token = self._get_auth_token(client, "issues-total@example.com")
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

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_size_bytes"] == 15_000_000_000
        assert "total_size_formatted" in data

    @pytest.mark.asyncio
    async def test_user_isolation(
        self, client: TestClient
    ) -> None:
        """User should only see their own content issues."""
        token1 = self._get_auth_token(client, "issues-user1@example.com")
        headers1 = {"Authorization": f"Bearer {token1}"}
        token2 = self._get_auth_token(client, "issues-user2@example.com")
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
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
                jellyfin_id="user2-movie",
                name="User 2 Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=8_000_000_000,
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        response1 = client.get("/api/content/issues", headers=headers1)
        data1 = response1.json()
        assert data1["total_count"] == 1
        assert data1["items"][0]["jellyfin_id"] == "user1-movie"

        response2 = client.get("/api/content/issues", headers=headers2)
        data2 = response2.json()
        assert data2["total_count"] == 1
        assert data2["items"][0]["jellyfin_id"] == "user2-movie"

    @pytest.mark.asyncio
    async def test_filter_language_returns_items_with_language_issues(
        self, client: TestClient
    ) -> None:
        """Language filter should return items missing EN or FR audio."""
        token = self._get_auth_token(client, "issues-lang@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Movie with language issue (missing French)
            raw_data = {
                "Id": "movie-lang-issue",
                "Name": "English Only",
                "Type": "Movie",
                "MediaSources": [{
                    "MediaStreams": [
                        {"Type": "Audio", "Language": "eng"},
                    ]
                }],
            }
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-lang-issue",
                name="English Only",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert "language" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_filter_requests_returns_empty_placeholder(
        self, client: TestClient
    ) -> None:
        """Requests filter should return empty (not implemented yet)."""
        token = self._get_auth_token(client, "issues-req@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Unavailable requests not yet implemented (US-6.1)
        assert data["items"] == []


class TestLanguageIssues:
    """Test language issues detection (US-5.1)."""

    def _get_auth_token(self, client: TestClient, email: str = "lang@example.com") -> str:
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

    def _create_movie_with_audio(
        self,
        jellyfin_id: str,
        name: str,
        audio_languages: list[str],
        subtitle_languages: list[str] | None = None,
    ) -> dict:
        """Create raw_data for a movie with specific audio/subtitle tracks."""
        media_streams = []
        for i, lang in enumerate(audio_languages):
            media_streams.append({
                "Type": "Audio",
                "Language": lang,
                "Index": i,
                "Codec": "aac",
                "Channels": 6,
                "IsDefault": i == 0,
            })
        for i, lang in enumerate(subtitle_languages or []):
            media_streams.append({
                "Type": "Subtitle",
                "Language": lang,
                "Index": len(audio_languages) + i,
            })
        return {
            "Id": jellyfin_id,
            "Name": name,
            "Type": "Movie",
            "MediaSources": [{
                "MediaStreams": media_streams,
            }],
        }

    @pytest.mark.asyncio
    async def test_movie_missing_english_audio_has_language_issue(
        self, client: TestClient
    ) -> None:
        """Movie with only French audio should have language issue."""
        token = self._get_auth_token(client, "lang-missing-en@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "movie-fr-only",
                "French Only Movie",
                ["fre"],  # Only French audio
                ["eng", "fre"],  # Has subtitles
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-fr-only",
                name="French Only Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-fr-only"
        assert "language" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_movie_missing_french_audio_has_language_issue(
        self, client: TestClient
    ) -> None:
        """Movie with only English audio should have language issue."""
        token = self._get_auth_token(client, "lang-missing-fr@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "movie-en-only",
                "English Only Movie",
                ["eng"],  # Only English audio
                ["eng"],  # No French subs
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-en-only",
                name="English Only Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-en-only"
        assert "language" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_movie_with_both_languages_has_no_language_issue(
        self, client: TestClient
    ) -> None:
        """Movie with both English and French audio should have no language issue."""
        token = self._get_auth_token(client, "lang-complete@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "movie-complete",
                "Complete Movie",
                ["eng", "fre"],  # Both English and French audio
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-complete",
                name="Complete Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_summary_includes_language_issues_count(
        self, client: TestClient
    ) -> None:
        """Summary should include count of items with language issues."""
        token = self._get_auth_token(client, "lang-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Movie with language issue
            raw_data = self._create_movie_with_audio(
                "movie-lang-issue",
                "Language Issue Movie",
                ["eng"],  # Missing French
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-lang-issue",
                name="Language Issue Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["language_issues"]["count"] == 1

    @pytest.mark.asyncio
    async def test_language_issue_includes_specific_issue_type(
        self, client: TestClient
    ) -> None:
        """Language issue should specify what's missing (missing_en_audio, missing_fr_audio)."""
        token = self._get_auth_token(client, "lang-specific@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "movie-specific-issue",
                "Specific Issue Movie",
                ["fre"],  # Missing English
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-specific-issue",
                name="Specific Issue Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item_data = data["items"][0]
        # Should have language_issues detail
        assert "language_issues" in item_data
        assert "missing_en_audio" in item_data["language_issues"]

    @pytest.mark.asyncio
    async def test_supports_language_code_variants(
        self, client: TestClient
    ) -> None:
        """Should recognize various language code formats (eng/en, fre/fr/fra)."""
        token = self._get_auth_token(client, "lang-variants@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Using 'en' and 'fr' instead of 'eng' and 'fre'
            raw_data = self._create_movie_with_audio(
                "movie-variants",
                "Variant Codes Movie",
                ["en", "fr"],  # Short codes
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-variants",
                name="Variant Codes Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should have no language issues - both languages present
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_language_issue_combined_with_other_issues(
        self, client: TestClient
    ) -> None:
        """Item can have language issue along with old/large issues."""
        token = self._get_auth_token(client, "lang-combined@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            raw_data = self._create_movie_with_audio(
                "movie-multi-issues",
                "Multi Issues Movie",
                ["eng"],  # Missing French = language issue
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-multi-issues",
                name="Multi Issues Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,  # Old and not watched = old issue
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        item_data = data["items"][0]
        # Should have both old and language issues
        assert "old" in item_data["issues"]
        assert "language" in item_data["issues"]


class TestFrenchOnlyWhitelist:
    """Test French-Only whitelist functionality (US-5.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "fronly@example.com") -> str:
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

    def _create_movie_with_audio(
        self,
        jellyfin_id: str,
        name: str,
        audio_languages: list[str],
    ) -> dict:
        """Create raw_data for a movie with specific audio tracks."""
        media_streams = []
        for i, lang in enumerate(audio_languages):
            media_streams.append({
                "Type": "Audio",
                "Language": lang,
                "Index": i,
            })
        return {
            "Id": jellyfin_id,
            "Name": name,
            "Type": "Movie",
            "MediaSources": [{
                "MediaStreams": media_streams,
            }],
        }

    def test_add_to_french_only_requires_auth(self, client: TestClient) -> None:
        """POST /api/whitelist/french-only should require authentication."""
        response = client.post(
            "/api/whitelist/french-only",
            json={"jellyfin_id": "test", "name": "Test", "media_type": "Movie"},
        )
        assert response.status_code == 401

    def test_add_to_french_only_creates_entry(self, client: TestClient) -> None:
        """Should create french-only whitelist entry."""
        token = self._get_auth_token(client, "fronly-add@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/whitelist/french-only",
            json={
                "jellyfin_id": "french-movie-1",
                "name": "Un Film Français",
                "media_type": "Movie",
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["jellyfin_id"] == "french-movie-1"
        assert data["name"] == "Un Film Français"

    def test_add_duplicate_returns_conflict(self, client: TestClient) -> None:
        """Adding same item twice should return 409 conflict."""
        token = self._get_auth_token(client, "fronly-dup@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add first time - should succeed
        client.post(
            "/api/whitelist/french-only",
            json={
                "jellyfin_id": "french-dup",
                "name": "Duplicate Film",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Add second time - should fail
        response = client.post(
            "/api/whitelist/french-only",
            json={
                "jellyfin_id": "french-dup",
                "name": "Duplicate Film",
                "media_type": "Movie",
            },
            headers=headers,
        )
        assert response.status_code == 409

    def test_get_french_only_whitelist(self, client: TestClient) -> None:
        """Should return list of french-only whitelist items."""
        token = self._get_auth_token(client, "fronly-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add some items
        client.post(
            "/api/whitelist/french-only",
            json={"jellyfin_id": "fr1", "name": "Film 1", "media_type": "Movie"},
            headers=headers,
        )
        client.post(
            "/api/whitelist/french-only",
            json={"jellyfin_id": "fr2", "name": "Film 2", "media_type": "Movie"},
            headers=headers,
        )

        response = client.get("/api/whitelist/french-only", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 2

    def test_delete_from_french_only(self, client: TestClient) -> None:
        """Should remove item from french-only whitelist."""
        token = self._get_auth_token(client, "fronly-del@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add an item
        client.post(
            "/api/whitelist/french-only",
            json={"jellyfin_id": "fr-del", "name": "To Delete", "media_type": "Movie"},
            headers=headers,
        )

        # Get the list to find the ID
        list_response = client.get("/api/whitelist/french-only", headers=headers)
        item_id = list_response.json()["items"][0]["id"]

        # Delete it
        response = client.delete(f"/api/whitelist/french-only/{item_id}", headers=headers)
        assert response.status_code == 200

        # Verify it's gone
        list_response = client.get("/api/whitelist/french-only", headers=headers)
        assert list_response.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_french_only_excludes_missing_en_audio_issue(
        self, client: TestClient
    ) -> None:
        """Items in french-only whitelist should not have missing_en_audio issue."""
        token = self._get_auth_token(client, "fronly-exclude@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a French-only movie (only French audio)
        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "french-only-movie",
                "Un Film Français",
                ["fre"],  # Only French audio - would normally flag missing EN
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="french-only-movie",
                name="Un Film Français",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        # Without whitelist, should have language issue
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert "missing_en_audio" in data["items"][0]["language_issues"]

        # Add to french-only whitelist
        client.post(
            "/api/whitelist/french-only",
            json={
                "jellyfin_id": "french-only-movie",
                "name": "Un Film Français",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Now should NOT have missing_en_audio issue (still might have missing_fr_audio if applicable)
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Item should no longer appear in language issues
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_french_only_still_flags_missing_french_audio(
        self, client: TestClient
    ) -> None:
        """French-only items should still flag missing French audio."""
        token = self._get_auth_token(client, "fronly-french@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a movie with only English audio (wrong for French-only!)
        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "wrongly-english-movie",
                "Wrong Audio",
                ["eng"],  # Only English audio - French-only should still need FR!
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="wrongly-english-movie",
                name="Wrong Audio",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        # Add to french-only whitelist
        client.post(
            "/api/whitelist/french-only",
            json={
                "jellyfin_id": "wrongly-english-movie",
                "name": "Wrong Audio",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Should still have missing_fr_audio issue
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert "missing_fr_audio" in data["items"][0]["language_issues"]
        # Should NOT have missing_en_audio (exempted by french-only)
        assert "missing_en_audio" not in data["items"][0]["language_issues"]


class TestLanguageExemptWhitelist:
    """Test /api/whitelist/language-exempt endpoints (US-5.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "langexempt@example.com") -> str:
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

    def _create_movie_with_audio(
        self, jellyfin_id: str, name: str, audio_langs: list[str]
    ) -> dict:
        """Create a cached media item with specific audio languages."""
        media_streams = [
            {"Type": "Audio", "Language": lang} for lang in audio_langs
        ]
        return {
            "Id": jellyfin_id,
            "Name": name,
            "MediaSources": [{
                "MediaStreams": media_streams,
            }],
        }

    def test_add_to_language_exempt_requires_auth(self, client: TestClient) -> None:
        """POST /api/whitelist/language-exempt should require authentication."""
        response = client.post(
            "/api/whitelist/language-exempt",
            json={"jellyfin_id": "test", "name": "Test", "media_type": "Movie"},
        )
        assert response.status_code == 401

    def test_add_to_language_exempt_creates_entry(self, client: TestClient) -> None:
        """Should create language-exempt whitelist entry."""
        token = self._get_auth_token(client, "langexempt-add@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/whitelist/language-exempt",
            json={
                "jellyfin_id": "exempt-movie-1",
                "name": "A Special Film",
                "media_type": "Movie",
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to language-exempt whitelist"
        assert data["jellyfin_id"] == "exempt-movie-1"

    def test_add_to_language_exempt_returns_409_if_duplicate(self, client: TestClient) -> None:
        """Should return 409 if item already in language-exempt whitelist."""
        token = self._get_auth_token(client, "langexempt-dup@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add first time - should succeed
        client.post(
            "/api/whitelist/language-exempt",
            json={
                "jellyfin_id": "exempt-dup",
                "name": "Duplicate Film",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Add second time - should fail
        response = client.post(
            "/api/whitelist/language-exempt",
            json={
                "jellyfin_id": "exempt-dup",
                "name": "Duplicate Film",
                "media_type": "Movie",
            },
            headers=headers,
        )
        assert response.status_code == 409

    def test_get_language_exempt_whitelist(self, client: TestClient) -> None:
        """Should return list of language-exempt whitelist items."""
        token = self._get_auth_token(client, "langexempt-list@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add some items
        client.post(
            "/api/whitelist/language-exempt",
            json={"jellyfin_id": "ex1", "name": "Film 1", "media_type": "Movie"},
            headers=headers,
        )
        client.post(
            "/api/whitelist/language-exempt",
            json={"jellyfin_id": "ex2", "name": "Film 2", "media_type": "Movie"},
            headers=headers,
        )

        response = client.get("/api/whitelist/language-exempt", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 2

    def test_delete_from_language_exempt(self, client: TestClient) -> None:
        """Should remove item from language-exempt whitelist."""
        token = self._get_auth_token(client, "langexempt-del@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add an item
        client.post(
            "/api/whitelist/language-exempt",
            json={"jellyfin_id": "ex-del", "name": "To Delete", "media_type": "Movie"},
            headers=headers,
        )

        # Get the list to find the ID
        list_response = client.get("/api/whitelist/language-exempt", headers=headers)
        item_id = list_response.json()["items"][0]["id"]

        # Delete it
        response = client.delete(f"/api/whitelist/language-exempt/{item_id}", headers=headers)
        assert response.status_code == 200

        # Verify it's gone
        list_response = client.get("/api/whitelist/language-exempt", headers=headers)
        assert list_response.json()["total_count"] == 0

    @pytest.mark.asyncio
    async def test_language_exempt_excludes_all_language_issues(
        self, client: TestClient
    ) -> None:
        """Items in language-exempt whitelist should not have any language issues."""
        token = self._get_auth_token(client, "langexempt-exclude@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a movie with only German audio (no EN or FR)
        async with TestingAsyncSessionLocal() as session:
            raw_data = self._create_movie_with_audio(
                "language-exempt-movie",
                "A German Film",
                ["deu"],  # Only German audio - would flag both missing EN and FR
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="language-exempt-movie",
                name="A German Film",
                media_type="Movie",
                size_bytes=5_000_000_000,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        # Verify it shows up as language issue
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert "missing_en_audio" in data["items"][0]["language_issues"]
        assert "missing_fr_audio" in data["items"][0]["language_issues"]

        # Add to language-exempt whitelist
        client.post(
            "/api/whitelist/language-exempt",
            json={
                "jellyfin_id": "language-exempt-movie",
                "name": "A German Film",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Should no longer appear in language issues
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Item should no longer appear in language issues
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_language_exempt_does_not_affect_other_issues(
        self, client: TestClient
    ) -> None:
        """Language-exempt should only exclude language issues, not other issues like old."""
        token = self._get_auth_token(client, "langexempt-other@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create an old movie with language issues
        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            raw_data = self._create_movie_with_audio(
                "old-exempt-movie",
                "Old Exempt Film",
                ["deu"],  # Only German audio
            )
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="old-exempt-movie",
                name="Old Exempt Film",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data=raw_data,
            )
            session.add(item)
            await session.commit()

        # Add to language-exempt whitelist
        client.post(
            "/api/whitelist/language-exempt",
            json={
                "jellyfin_id": "old-exempt-movie",
                "name": "Old Exempt Film",
                "media_type": "Movie",
            },
            headers=headers,
        )

        # Should still appear in old content filter (not language)
        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "old-exempt-movie"
        # Should have 'old' issue but NOT 'language' issue
        assert "old" in data["items"][0]["issues"]
        assert "language" not in data["items"][0]["issues"]


class TestUnavailableRequests:
    """Test unavailable Jellyseerr requests (US-6.1)."""

    def _get_auth_token(self, client: TestClient, email: str = "requests@example.com") -> str:
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

    @pytest.mark.asyncio
    async def test_summary_includes_unavailable_requests_count(
        self, client: TestClient
    ) -> None:
        """Summary should include count of unavailable requests."""
        token = self._get_auth_token(client, "summary-requests@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            # Unavailable request (status 1 = Pending)
            pending = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=1001,
                tmdb_id=12345,
                media_type="movie",
                status=1,  # Pending
                title="Pending Movie",
                requested_by="user1",
                raw_data={"media": {"title": "Pending Movie", "releaseDate": "2023-01-15"}},
            )
            # Available request (status 5 = Available) - should NOT count
            available = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=1002,
                tmdb_id=67890,
                media_type="movie",
                status=5,  # Available
                title="Available Movie",
                requested_by="user2",
                raw_data={"media": {"title": "Available Movie"}},
            )
            session.add_all([pending, available])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["unavailable_requests"]["count"] == 1

    @pytest.mark.asyncio
    async def test_unavailable_requests_includes_different_status_codes(
        self, client: TestClient
    ) -> None:
        """Unavailable requests include status 0 (Unknown), 1 (Pending), 2 (Approved), 4 (Partially Available)."""
        token = self._get_auth_token(client, "statuses@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            # Status 0 = Unknown
            req_unknown = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2001,
                media_type="movie",
                status=0,
                title="Unknown Status Movie",
                raw_data={"media": {"title": "Unknown Status Movie", "releaseDate": "2022-06-01"}},
            )
            # Status 1 = Pending
            req_pending = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2002,
                media_type="movie",
                status=1,
                title="Pending Movie",
                raw_data={"media": {"title": "Pending Movie", "releaseDate": "2023-01-15"}},
            )
            # Status 2 = Approved (but not downloading yet)
            req_approved = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2003,
                media_type="tv",
                status=2,
                title="Approved Series",
                raw_data={"media": {"title": "Approved Series", "releaseDate": "2021-09-01"}},
            )
            # Status 3 = Processing - should NOT be unavailable
            req_processing = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2004,
                media_type="movie",
                status=3,
                title="Processing Movie",
                raw_data={"media": {"title": "Processing Movie"}},
            )
            # Status 4 = Partially Available
            req_partial = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2005,
                media_type="tv",
                status=4,
                title="Partial Series",
                raw_data={"media": {"title": "Partial Series", "releaseDate": "2020-05-01"}},
            )
            # Status 5 = Available - should NOT be unavailable
            req_available = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=2006,
                media_type="movie",
                status=5,
                title="Available Movie",
                raw_data={"media": {"title": "Available Movie"}},
            )
            session.add_all([req_unknown, req_pending, req_approved, req_processing, req_partial, req_available])
            await session.commit()

        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Should count status 0, 1, 2, 4 = 4 requests
        assert data["unavailable_requests"]["count"] == 4

    @pytest.mark.asyncio
    async def test_issues_filter_requests_returns_unavailable_requests(
        self, client: TestClient
    ) -> None:
        """Filter=requests should return only unavailable Jellyseerr requests."""
        token = self._get_auth_token(client, "filter-requests@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            # Unavailable request
            unavailable = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=3001,
                tmdb_id=11111,
                media_type="movie",
                status=1,
                title="Unavailable Movie",
                requested_by="testuser",
                created_at_source="2024-01-15T10:00:00Z",
                raw_data={"media": {"title": "Unavailable Movie", "releaseDate": "2023-06-01"}},
            )
            # Available request - should NOT appear
            available = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=3002,
                media_type="movie",
                status=5,
                title="Available Movie",
                raw_data={"media": {"title": "Available Movie"}},
            )
            session.add_all([unavailable, available])
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        # Requests now use unified format with 'name' instead of 'title'
        assert data["items"][0]["name"] == "Unavailable Movie"
        # jellyfin_id is prefixed with 'request-' for requests
        assert data["items"][0]["jellyfin_id"] == "request-3001"
        assert data["items"][0]["media_type"] == "movie"
        assert "request" in data["items"][0]["issues"]

    @pytest.mark.asyncio
    async def test_unavailable_request_item_includes_required_fields(
        self, client: TestClient
    ) -> None:
        """Unavailable request items should include title, type, requested_by, request_date."""
        token = self._get_auth_token(client, "fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=4001,
                tmdb_id=22222,
                media_type="movie",
                status=1,
                title="Test Movie Request",
                requested_by="JohnDoe",
                created_at_source="2024-02-20T15:30:00Z",
                raw_data={
                    "media": {"title": "Test Movie Request", "releaseDate": "2023-03-15"},
                    "requestedBy": {"displayName": "JohnDoe"},
                    "createdAt": "2024-02-20T15:30:00Z",
                },
            )
            session.add(request)
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        item = data["items"][0]
        # Requests now use unified format with 'name' instead of 'title'
        assert item["name"] == "Test Movie Request"
        assert item["media_type"] == "movie"
        assert item["requested_by"] == "JohnDoe"
        assert item["request_date"] == "2024-02-20T15:30:00Z"

    @pytest.mark.asyncio
    async def test_tv_request_includes_missing_seasons_info(
        self, client: TestClient
    ) -> None:
        """TV requests should include which seasons are requested but missing."""
        token = self._get_auth_token(client, "tv-seasons@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            # TV request with seasons info
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=5001,
                tmdb_id=33333,
                media_type="tv",
                status=4,  # Partially Available
                title="Test TV Series",
                requested_by="JaneDoe",
                created_at_source="2024-03-10T12:00:00Z",
                raw_data={
                    "media": {"title": "Test TV Series", "firstAirDate": "2022-01-01"},
                    "requestedBy": {"displayName": "JaneDoe"},
                    "createdAt": "2024-03-10T12:00:00Z",
                    "seasons": [
                        {"seasonNumber": 1, "status": 5},  # Available
                        {"seasonNumber": 2, "status": 1},  # Pending (missing)
                        {"seasonNumber": 3, "status": 1},  # Pending (missing)
                    ],
                },
            )
            session.add(request)
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        item = data["items"][0]
        # Requests now use unified format with 'name' instead of 'title'
        assert item["name"] == "Test TV Series"
        assert item["media_type"] == "tv"
        # Should include info about missing seasons
        assert "missing_seasons" in item
        assert 2 in item["missing_seasons"]
        assert 3 in item["missing_seasons"]
        assert 1 not in item["missing_seasons"]  # Season 1 is available

    @pytest.mark.asyncio
    async def test_unavailable_requests_filters_future_releases(
        self, client: TestClient
    ) -> None:
        """Unavailable requests with future release dates should be excluded."""
        token = self._get_auth_token(client, "future@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest
        from datetime import datetime, timedelta

        future_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        past_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        async with TestingAsyncSessionLocal() as session:
            # Future release - should NOT appear
            future_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=6001,
                media_type="movie",
                status=1,
                title="Future Movie",
                raw_data={"media": {"title": "Future Movie", "releaseDate": future_date}},
            )
            # Past release - should appear
            past_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=6002,
                media_type="movie",
                status=1,
                title="Past Movie",
                raw_data={"media": {"title": "Past Movie", "releaseDate": past_date}},
            )
            session.add_all([future_request, past_request])
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Only past release should appear
        assert data["total_count"] == 1
        # Requests now use unified format with 'name' instead of 'title'
        assert data["items"][0]["name"] == "Past Movie"

    @pytest.mark.asyncio
    async def test_unavailable_requests_filters_recent_releases(
        self, client: TestClient
    ) -> None:
        """Unavailable requests released less than 3 months ago should be excluded."""
        token = self._get_auth_token(client, "recent-release@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest
        from datetime import datetime, timedelta

        # Release date 1 month ago (recent - should be filtered)
        recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        # Release date 6 months ago (old enough)
        old_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        async with TestingAsyncSessionLocal() as session:
            # Recent release - should NOT appear (too recent)
            recent_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=7001,
                media_type="movie",
                status=1,
                title="Recent Release Movie",
                raw_data={"media": {"title": "Recent Release Movie", "releaseDate": recent_date}},
            )
            # Old release - should appear
            old_request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=7002,
                media_type="movie",
                status=1,
                title="Old Release Movie",
                raw_data={"media": {"title": "Old Release Movie", "releaseDate": old_date}},
            )
            session.add_all([recent_request, old_request])
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # Only old release should appear
        assert data["total_count"] == 1
        # Requests now use unified format with 'name' instead of 'title'
        assert data["items"][0]["name"] == "Old Release Movie"

    @pytest.mark.asyncio
    async def test_tv_request_includes_sonarr_title_slug(
        self, client: TestClient
    ) -> None:
        """TV requests should include sonarr_title_slug when Sonarr is configured."""
        from unittest.mock import patch, AsyncMock

        token = self._get_auth_token(client, "sonarr-slug@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest, UserSettings
        from app.services.encryption import encrypt_value
        from datetime import datetime, timedelta

        past_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        async with TestingAsyncSessionLocal() as session:
            # Configure Sonarr settings for the user
            settings = UserSettings(
                user_id=user_id,
                sonarr_server_url="http://sonarr:8989",
                sonarr_api_key_encrypted=encrypt_value("test-sonarr-key"),
            )
            session.add(settings)

            # TV request
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=8001,
                tmdb_id=44444,
                media_type="tv",
                status=1,  # Pending
                title="Fallout",
                requested_by="TestUser",
                raw_data={
                    "media": {"title": "Fallout", "firstAirDate": past_date},
                },
            )
            session.add(request)
            await session.commit()

        # Mock the Sonarr API to return a titleSlug map
        mock_slug_map = {44444: "fallout"}
        with patch(
            "app.routers.content.get_sonarr_tmdb_to_slug_map",
            new_callable=AsyncMock,
            return_value=mock_slug_map,
        ):
            response = client.get("/api/content/issues?filter=requests", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        item = data["items"][0]
        assert item["name"] == "Fallout"
        assert item["media_type"] == "tv"
        assert item["sonarr_title_slug"] == "fallout"


class TestProviderIds:
    """Test TMDB/IMDB provider ID extraction (US-9.4)."""

    def _get_auth_token(self, client: TestClient, email: str = "provider@example.com") -> str:
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

    @pytest.mark.asyncio
    async def test_extract_provider_ids_with_both_ids(
        self, client: TestClient
    ) -> None:
        """Should extract both TMDB and IMDB IDs from raw_data."""
        from app.services.content import extract_provider_ids

        token = self._get_auth_token(client, "provider-both@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-provider-both",
                name="Movie With IDs",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data={
                    "Id": "movie-provider-both",
                    "ProviderIds": {
                        "Tmdb": "12345",
                        "Imdb": "tt0123456",
                    },
                },
            )
            session.add(item)
            await session.commit()

            # Refresh item from DB
            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.jellyfin_id == "movie-provider-both")
            )
            db_item = result.scalar_one()

            tmdb_id, imdb_id = extract_provider_ids(db_item)
            assert tmdb_id == "12345"
            assert imdb_id == "tt0123456"

    @pytest.mark.asyncio
    async def test_extract_provider_ids_with_only_tmdb(
        self, client: TestClient
    ) -> None:
        """Should handle items with only TMDB ID."""
        from app.services.content import extract_provider_ids

        token = self._get_auth_token(client, "provider-tmdb@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-tmdb-only",
                name="TMDB Only Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data={
                    "Id": "movie-tmdb-only",
                    "ProviderIds": {
                        "Tmdb": "67890",
                    },
                },
            )
            session.add(item)
            await session.commit()

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.jellyfin_id == "movie-tmdb-only")
            )
            db_item = result.scalar_one()

            tmdb_id, imdb_id = extract_provider_ids(db_item)
            assert tmdb_id == "67890"
            assert imdb_id is None

    @pytest.mark.asyncio
    async def test_extract_provider_ids_with_no_ids(
        self, client: TestClient
    ) -> None:
        """Should return None for both when no provider IDs present."""
        from app.services.content import extract_provider_ids

        token = self._get_auth_token(client, "provider-none@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-no-ids",
                name="No IDs Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data={
                    "Id": "movie-no-ids",
                },
            )
            session.add(item)
            await session.commit()

            result = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.jellyfin_id == "movie-no-ids")
            )
            db_item = result.scalar_one()

            tmdb_id, imdb_id = extract_provider_ids(db_item)
            assert tmdb_id is None
            assert imdb_id is None

    @pytest.mark.asyncio
    async def test_issues_endpoint_includes_provider_ids(
        self, client: TestClient
    ) -> None:
        """Issues endpoint should include tmdb_id and imdb_id in response."""
        token = self._get_auth_token(client, "provider-api@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-api-ids",
                name="API Test Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data={
                    "Id": "movie-api-ids",
                    "ProviderIds": {
                        "Tmdb": "99999",
                        "Imdb": "tt9999999",
                    },
                },
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        item_data = data["items"][0]
        assert item_data["tmdb_id"] == "99999"
        assert item_data["imdb_id"] == "tt9999999"

    @pytest.mark.asyncio
    async def test_issues_endpoint_handles_missing_provider_ids(
        self, client: TestClient
    ) -> None:
        """Issues endpoint should handle items without provider IDs gracefully."""
        token = self._get_auth_token(client, "provider-missing@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            old_date = (datetime.now(timezone.utc) - timedelta(days=150)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-no-provider-ids",
                name="No Provider IDs Movie",
                media_type="Movie",
                date_created=old_date,
                size_bytes=5_000_000_000,
                played=False,
                raw_data={"Id": "movie-no-provider-ids"},
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/content/issues", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        item_data = data["items"][0]
        assert item_data["tmdb_id"] is None
        assert item_data["imdb_id"] is None

    @pytest.mark.asyncio
    async def test_unavailable_requests_includes_tmdb_id(
        self, client: TestClient
    ) -> None:
        """Unavailable requests endpoint should include tmdb_id in response."""
        token = self._get_auth_token(client, "request-tmdb@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        from app.database import CachedJellyseerrRequest

        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=9001,
                tmdb_id=55555,
                media_type="movie",
                status=1,  # Pending
                title="Requested Movie",
                raw_data={"media": {"title": "Requested Movie", "releaseDate": "2023-01-15"}},
            )
            session.add(request)
            await session.commit()

        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        item_data = data["items"][0]
        # tmdb_id is now returned as string in unified format
        assert item_data["tmdb_id"] == "55555"


class TestWhitelistExpirationSchema:
    """Test whitelist expires_at column for all whitelist tables (US-11.1)."""

    @pytest.mark.asyncio
    async def test_french_only_whitelist_has_expires_at_column(
        self, client: TestClient
    ) -> None:
        """FrenchOnlyWhitelist model should have nullable expires_at column."""
        from datetime import datetime, timezone, timedelta

        async with TestingAsyncSessionLocal() as session:
            # Test with expires_at set
            entry_with_expiry = FrenchOnlyWhitelist(
                user_id=1,
                jellyfin_id="french-expiry-123",
                name="Temporary French-Only",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )
            session.add(entry_with_expiry)
            await session.commit()
            assert entry_with_expiry.expires_at is not None

            # Test with expires_at None (permanent)
            entry_permanent = FrenchOnlyWhitelist(
                user_id=1,
                jellyfin_id="french-permanent-123",
                name="Permanent French-Only",
                media_type="Movie",
                expires_at=None,
            )
            session.add(entry_permanent)
            await session.commit()
            assert entry_permanent.expires_at is None

    @pytest.mark.asyncio
    async def test_language_exempt_whitelist_has_expires_at_column(
        self, client: TestClient
    ) -> None:
        """LanguageExemptWhitelist model should have nullable expires_at column."""
        from datetime import datetime, timezone, timedelta

        async with TestingAsyncSessionLocal() as session:
            # Test with expires_at set
            entry_with_expiry = LanguageExemptWhitelist(
                user_id=1,
                jellyfin_id="exempt-expiry-123",
                name="Temporary Exempt",
                media_type="Series",
                expires_at=datetime.now(timezone.utc) + timedelta(days=180),
            )
            session.add(entry_with_expiry)
            await session.commit()
            assert entry_with_expiry.expires_at is not None

            # Test with expires_at None (permanent)
            entry_permanent = LanguageExemptWhitelist(
                user_id=1,
                jellyfin_id="exempt-permanent-123",
                name="Permanent Exempt",
                media_type="Series",
                expires_at=None,
            )
            session.add(entry_permanent)
            await session.commit()
            assert entry_permanent.expires_at is None


class TestWhitelistExpirationLogic:
    """Test whitelist expiration logic (US-11.2)."""

    def _get_auth_token(self, client: TestClient, email: str = "expire@example.com") -> str:
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

    @pytest.mark.asyncio
    async def test_expired_content_whitelist_does_not_protect_content(
        self, client: TestClient
    ) -> None:
        """Content with expired whitelist entry should appear in old content issues."""
        token = self._get_auth_token(client, "expired-content@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create old unwatched content
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-expired-whitelist",
                name="Movie With Expired Whitelist",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Expired Whitelist",
                size_bytes=10_000_000_000,
                played=False,
                play_count=0,
                last_played_date=None,
            )
            session.add(item)

            # Create EXPIRED whitelist entry (expired 1 day ago)
            expired_whitelist = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-expired-whitelist",
                name="Movie With Expired Whitelist",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            session.add(expired_whitelist)
            await session.commit()

        # Item should appear in issues because whitelist is expired
        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-expired-whitelist"

    @pytest.mark.asyncio
    async def test_non_expired_content_whitelist_protects_content(
        self, client: TestClient
    ) -> None:
        """Content with non-expired whitelist entry should NOT appear in old content issues."""
        token = self._get_auth_token(client, "non-expired-content@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create old unwatched content
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-valid-whitelist",
                name="Movie With Valid Whitelist",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Valid Whitelist",
                size_bytes=10_000_000_000,
                played=False,
                play_count=0,
                last_played_date=None,
            )
            session.add(item)

            # Create NON-expired whitelist entry (expires in 30 days)
            valid_whitelist = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-valid-whitelist",
                name="Movie With Valid Whitelist",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            session.add(valid_whitelist)
            await session.commit()

        # Item should NOT appear in issues because whitelist is valid
        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_permanent_content_whitelist_protects_content(
        self, client: TestClient
    ) -> None:
        """Content with NULL expires_at (permanent) should NOT appear in old content issues."""
        token = self._get_auth_token(client, "permanent-content@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create old unwatched content
            old_date = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-permanent-whitelist",
                name="Movie With Permanent Whitelist",
                media_type="Movie",
                production_year=2020,
                date_created=old_date,
                path="/media/movies/Permanent Whitelist",
                size_bytes=10_000_000_000,
                played=False,
                play_count=0,
                last_played_date=None,
            )
            session.add(item)

            # Create PERMANENT whitelist entry (NULL expires_at)
            permanent_whitelist = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="movie-permanent-whitelist",
                name="Movie With Permanent Whitelist",
                media_type="Movie",
                expires_at=None,  # Permanent - never expires
            )
            session.add(permanent_whitelist)
            await session.commit()

        # Item should NOT appear in issues because whitelist is permanent
        response = client.get("/api/content/issues?filter=old", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_api_accepts_expires_at_when_adding_to_content_whitelist(
        self, client: TestClient
    ) -> None:
        """POST /api/whitelist/content should accept optional expires_at field."""
        token = self._get_auth_token(client, "add-with-expiry@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        response = client.post(
            "/api/whitelist/content",
            headers=headers,
            json={
                "jellyfin_id": "movie-with-expiry",
                "name": "Movie With Expiry",
                "media_type": "Movie",
                "expires_at": expires_at,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to whitelist"

        # Verify in database that expires_at was saved
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(ContentWhitelist).where(
                    ContentWhitelist.user_id == user_id,
                    ContentWhitelist.jellyfin_id == "movie-with-expiry"
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.expires_at is not None

    @pytest.mark.asyncio
    async def test_expired_french_only_whitelist_does_not_exempt_from_language_check(
        self, client: TestClient
    ) -> None:
        """Content with expired french-only whitelist entry should flag missing English audio."""
        token = self._get_auth_token(client, "expired-french@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create content missing English audio
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-french-expired",
                name="French Movie With Expired Whitelist",
                media_type="Movie",
                production_year=2020,
                date_created=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                path="/media/movies/French Expired",
                size_bytes=8_000_000_000,
                played=True,
                play_count=1,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                raw_data={
                    "MediaSources": [{
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "fra"},  # Only French audio
                        ]
                    }]
                },
            )
            session.add(item)

            # Create EXPIRED french-only whitelist entry
            expired_french = FrenchOnlyWhitelist(
                user_id=user_id,
                jellyfin_id="movie-french-expired",
                name="French Movie With Expired Whitelist",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            session.add(expired_french)
            await session.commit()

        # Item should appear in language issues because french-only whitelist is expired
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-french-expired"
        assert "missing_en_audio" in data["items"][0]["language_issues"]

    @pytest.mark.asyncio
    async def test_non_expired_french_only_whitelist_exempts_from_english_check(
        self, client: TestClient
    ) -> None:
        """Content with valid french-only whitelist entry should NOT flag missing English audio."""
        token = self._get_auth_token(client, "valid-french@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create content with both English and French audio
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-french-valid",
                name="French Movie With Valid Whitelist",
                media_type="Movie",
                production_year=2020,
                date_created=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                path="/media/movies/French Valid",
                size_bytes=8_000_000_000,
                played=True,
                play_count=1,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                raw_data={
                    "MediaSources": [{
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "fra"},  # French audio only
                        ]
                    }]
                },
            )
            session.add(item)

            # Create VALID french-only whitelist entry (expires in 30 days)
            valid_french = FrenchOnlyWhitelist(
                user_id=user_id,
                jellyfin_id="movie-french-valid",
                name="French Movie With Valid Whitelist",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            session.add(valid_french)
            await session.commit()

        # Item should NOT appear in language issues because french-only is valid
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_expired_language_exempt_whitelist_does_not_exempt(
        self, client: TestClient
    ) -> None:
        """Content with expired language-exempt entry should flag language issues."""
        token = self._get_auth_token(client, "expired-exempt@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create content missing languages
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-exempt-expired",
                name="Movie With Expired Exempt",
                media_type="Movie",
                production_year=2020,
                date_created=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                path="/media/movies/Exempt Expired",
                size_bytes=8_000_000_000,
                played=True,
                play_count=1,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                raw_data={
                    "MediaSources": [{
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "jpn"},  # Only Japanese
                        ]
                    }]
                },
            )
            session.add(item)

            # Create EXPIRED language-exempt whitelist entry
            expired_exempt = LanguageExemptWhitelist(
                user_id=user_id,
                jellyfin_id="movie-exempt-expired",
                name="Movie With Expired Exempt",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            session.add(expired_exempt)
            await session.commit()

        # Item should appear in language issues because language-exempt is expired
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["jellyfin_id"] == "movie-exempt-expired"

    @pytest.mark.asyncio
    async def test_non_expired_language_exempt_whitelist_exempts(
        self, client: TestClient
    ) -> None:
        """Content with valid language-exempt entry should NOT flag language issues."""
        token = self._get_auth_token(client, "valid-exempt@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create content missing languages
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-exempt-valid",
                name="Movie With Valid Exempt",
                media_type="Movie",
                production_year=2020,
                date_created=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                path="/media/movies/Exempt Valid",
                size_bytes=8_000_000_000,
                played=True,
                play_count=1,
                last_played_date=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                raw_data={
                    "MediaSources": [{
                        "MediaStreams": [
                            {"Type": "Audio", "Language": "jpn"},  # Only Japanese
                        ]
                    }]
                },
            )
            session.add(item)

            # Create VALID language-exempt whitelist entry (expires in 30 days)
            valid_exempt = LanguageExemptWhitelist(
                user_id=user_id,
                jellyfin_id="movie-exempt-valid",
                name="Movie With Valid Exempt",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            session.add(valid_exempt)
            await session.commit()

        # Item should NOT appear in language issues because language-exempt is valid
        response = client.get("/api/content/issues?filter=language", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_api_accepts_expires_at_when_adding_to_french_only_whitelist(
        self, client: TestClient
    ) -> None:
        """POST /api/whitelist/french-only should accept optional expires_at field."""
        token = self._get_auth_token(client, "add-french-expiry@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        response = client.post(
            "/api/whitelist/french-only",
            headers=headers,
            json={
                "jellyfin_id": "french-movie-expiry",
                "name": "French Movie With Expiry",
                "media_type": "Movie",
                "expires_at": expires_at,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to french-only whitelist"

        # Verify in database that expires_at was saved
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(FrenchOnlyWhitelist).where(
                    FrenchOnlyWhitelist.user_id == user_id,
                    FrenchOnlyWhitelist.jellyfin_id == "french-movie-expiry"
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.expires_at is not None

    @pytest.mark.asyncio
    async def test_api_accepts_expires_at_when_adding_to_language_exempt_whitelist(
        self, client: TestClient
    ) -> None:
        """POST /api/whitelist/language-exempt should accept optional expires_at field."""
        token = self._get_auth_token(client, "add-exempt-expiry@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        expires_at = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()
        response = client.post(
            "/api/whitelist/language-exempt",
            headers=headers,
            json={
                "jellyfin_id": "exempt-movie-expiry",
                "name": "Exempt Movie With Expiry",
                "media_type": "Movie",
                "expires_at": expires_at,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to language-exempt whitelist"

        # Verify in database that expires_at was saved
        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            result = await session.execute(
                select(LanguageExemptWhitelist).where(
                    LanguageExemptWhitelist.user_id == user_id,
                    LanguageExemptWhitelist.jellyfin_id == "exempt-movie-expiry"
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.expires_at is not None

    @pytest.mark.asyncio
    async def test_whitelist_list_includes_expires_at(
        self, client: TestClient
    ) -> None:
        """GET /api/whitelist/content should return expires_at for each item."""
        token = self._get_auth_token(client, "list-expiry@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create whitelist entries with different expiration settings
        async with TestingAsyncSessionLocal() as session:
            # Permanent entry
            permanent = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="permanent-entry",
                name="Permanent Entry",
                media_type="Movie",
                expires_at=None,
            )
            # Entry with expiration
            with_expiry = ContentWhitelist(
                user_id=user_id,
                jellyfin_id="entry-with-expiry",
                name="Entry With Expiry",
                media_type="Movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )
            session.add_all([permanent, with_expiry])
            await session.commit()

        response = client.get("/api/whitelist/content", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        items_by_id = {item["jellyfin_id"]: item for item in data["items"]}

        assert items_by_id["permanent-entry"]["expires_at"] is None
        assert items_by_id["entry-with-expiry"]["expires_at"] is not None


class TestRequestWhitelist:
    """Tests for Jellyseerr request whitelist (US-13.4)."""

    def _get_auth_token(self, client: TestClient, email: str) -> str:
        """Helper to get auth token for a test user."""
        password = "testpassword123"
        # Register
        client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        # Login
        login_response = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        return login_response.json()["access_token"]

    def test_add_to_request_whitelist(self, client: TestClient) -> None:
        """POST /api/whitelist/requests should add a request to the whitelist."""
        token = self._get_auth_token(client, "reqwl-add@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 123, "title": "Test Movie", "media_type": "movie"},
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Added to request whitelist"
        assert data["name"] == "Test Movie"

    def test_add_duplicate_to_request_whitelist(self, client: TestClient) -> None:
        """POST /api/whitelist/requests should return 409 for duplicates."""
        token = self._get_auth_token(client, "reqwl-dup@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add first time
        client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 456, "title": "Dup Movie", "media_type": "movie"},
            headers=headers,
        )

        # Try to add again
        response = client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 456, "title": "Dup Movie", "media_type": "movie"},
            headers=headers,
        )

        assert response.status_code == 409
        assert "already in whitelist" in response.json()["detail"]

    def test_get_request_whitelist(self, client: TestClient) -> None:
        """GET /api/whitelist/requests should return list of whitelisted requests."""
        token = self._get_auth_token(client, "reqwl-get@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add some requests
        client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 1001, "title": "Movie One", "media_type": "movie"},
            headers=headers,
        )
        client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 1002, "title": "TV Show Two", "media_type": "tv"},
            headers=headers,
        )

        response = client.get("/api/whitelist/requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 2
        # Check fields are present
        item = data["items"][0]
        assert "jellyseerr_id" in item
        assert "title" in item
        assert "media_type" in item
        assert "created_at" in item
        assert "expires_at" in item

    def test_delete_from_request_whitelist(self, client: TestClient) -> None:
        """DELETE /api/whitelist/requests/{id} should remove from whitelist."""
        token = self._get_auth_token(client, "reqwl-del@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Add a request
        client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 2001, "title": "To Delete", "media_type": "movie"},
            headers=headers,
        )

        # Get the list to find the ID
        list_response = client.get("/api/whitelist/requests", headers=headers)
        item_id = list_response.json()["items"][0]["id"]

        # Delete it
        response = client.delete(f"/api/whitelist/requests/{item_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Removed from request whitelist"

        # Verify it's gone
        list_response = client.get("/api/whitelist/requests", headers=headers)
        assert list_response.json()["total_count"] == 0

    def test_delete_nonexistent_request_whitelist(self, client: TestClient) -> None:
        """DELETE /api/whitelist/requests/{id} should return 404 for non-existent."""
        token = self._get_auth_token(client, "reqwl-404@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/api/whitelist/requests/99999", headers=headers)
        assert response.status_code == 404

    def test_add_request_whitelist_with_expiration(self, client: TestClient) -> None:
        """POST /api/whitelist/requests should accept expires_at."""
        token = self._get_auth_token(client, "reqwl-exp@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        response = client.post(
            "/api/whitelist/requests",
            json={
                "jellyseerr_id": 3001,
                "title": "Expiring Request",
                "media_type": "movie",
                "expires_at": expires_at,
            },
            headers=headers,
        )

        assert response.status_code == 201

        # Verify expiration is stored
        list_response = client.get("/api/whitelist/requests", headers=headers)
        item = list_response.json()["items"][0]
        assert item["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_whitelisted_request_excluded_from_unavailable_list(
        self, client: TestClient
    ) -> None:
        """Whitelisted requests should not appear in unavailable requests list."""
        token = self._get_auth_token(client, "reqwl-excl@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a cached request that would be unavailable
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=5001,
                tmdb_id=12345,
                media_type="movie",
                status=1,  # Pending - would be unavailable
                title="Test Unavailable Movie",
                requested_by="test@example.com",
                created_at_source="2020-01-01T00:00:00Z",  # Old enough to pass filters
                release_date="2020-01-01",  # Old enough to pass filters
            )
            session.add(request)
            await session.commit()

        # Without whitelist, should appear in unavailable
        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

        # Add to whitelist
        client.post(
            "/api/whitelist/requests",
            json={
                "jellyseerr_id": 5001,
                "title": "Test Unavailable Movie",
                "media_type": "movie",
            },
            headers=headers,
        )

        # Should no longer appear
        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_expired_whitelist_does_not_exclude_request(
        self, client: TestClient
    ) -> None:
        """Expired whitelist entries should not filter out requests."""
        token = self._get_auth_token(client, "reqwl-expired@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a cached request that would be unavailable
        async with TestingAsyncSessionLocal() as session:
            from app.database import JellyseerrRequestWhitelist

            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=6001,
                tmdb_id=67890,
                media_type="movie",
                status=1,  # Pending - would be unavailable
                title="Expired Whitelist Movie",
                requested_by="test@example.com",
                created_at_source="2020-01-01T00:00:00Z",
                release_date="2020-01-01",
            )
            # Create expired whitelist entry directly in DB
            whitelist_entry = JellyseerrRequestWhitelist(
                user_id=user_id,
                jellyseerr_id=6001,
                title="Expired Whitelist Movie",
                media_type="movie",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            )
            session.add_all([request, whitelist_entry])
            await session.commit()

        # Should appear in unavailable (whitelist is expired)
        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

    @pytest.mark.asyncio
    async def test_non_expired_whitelist_excludes_request(
        self, client: TestClient
    ) -> None:
        """Non-expired whitelist entries should filter out requests."""
        token = self._get_auth_token(client, "reqwl-valid@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create a cached request that would be unavailable
        async with TestingAsyncSessionLocal() as session:
            from app.database import JellyseerrRequestWhitelist

            request = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=7001,
                tmdb_id=11111,
                media_type="movie",
                status=1,  # Pending - would be unavailable
                title="Valid Whitelist Movie",
                requested_by="test@example.com",
                created_at_source="2020-01-01T00:00:00Z",
                release_date="2020-01-01",
            )
            # Create non-expired whitelist entry directly in DB
            whitelist_entry = JellyseerrRequestWhitelist(
                user_id=user_id,
                jellyseerr_id=7001,
                title="Valid Whitelist Movie",
                media_type="movie",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),  # Not expired
            )
            session.add_all([request, whitelist_entry])
            await session.commit()

        # Should NOT appear in unavailable (whitelist is valid)
        response = client.get("/api/content/issues?filter=requests", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    @pytest.mark.asyncio
    async def test_summary_count_excludes_whitelisted_requests(
        self, client: TestClient
    ) -> None:
        """Content summary unavailable_requests count should exclude whitelisted."""
        token = self._get_auth_token(client, "reqwl-summary@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create two cached requests that would be unavailable
        async with TestingAsyncSessionLocal() as session:
            request1 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=8001,
                tmdb_id=22222,
                media_type="movie",
                status=1,
                title="Request One",
                requested_by="test@example.com",
                created_at_source="2020-01-01T00:00:00Z",
                release_date="2020-01-01",
            )
            request2 = CachedJellyseerrRequest(
                user_id=user_id,
                jellyseerr_id=8002,
                tmdb_id=33333,
                media_type="movie",
                status=1,
                title="Request Two",
                requested_by="test@example.com",
                created_at_source="2020-01-01T00:00:00Z",
                release_date="2020-01-01",
            )
            session.add_all([request1, request2])
            await session.commit()

        # Should have 2 unavailable
        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        assert response.json()["unavailable_requests"]["count"] == 2

        # Whitelist one
        client.post(
            "/api/whitelist/requests",
            json={"jellyseerr_id": 8001, "title": "Request One", "media_type": "movie"},
            headers=headers,
        )

        # Should have 1 unavailable now
        response = client.get("/api/content/summary", headers=headers)
        assert response.status_code == 200
        assert response.json()["unavailable_requests"]["count"] == 1
