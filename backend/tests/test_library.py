"""Tests for Library API endpoints (US-22.1)."""

import pytest
from fastapi.testclient import TestClient

from app.database import CachedMediaItem, UserSettings
from tests.conftest import TestingAsyncSessionLocal


class TestLibraryEndpoint:
    """Test GET /api/library endpoint."""

    def _get_auth_token(self, client: TestClient, email: str = "library@example.com") -> str:
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
        """GET /api/library should require authentication."""
        response = client.get("/api/library")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_cached_items(self, client: TestClient) -> None:
        """Should return empty list when no cached items exist."""
        token = self._get_auth_token(client, "library_empty@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["total_size_bytes"] == 0
        assert data["total_size_formatted"] == "0 B"

    @pytest.mark.asyncio
    async def test_returns_all_cached_media_items(self, client: TestClient) -> None:
        """Should return all cached media items for the user."""
        token = self._get_auth_token(client, "library_all@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-1",
                name="Test Movie",
                media_type="Movie",
                production_year=2020,
                date_created="2024-01-15T00:00:00Z",
                path="/media/movies/Test Movie",
                size_bytes=10_000_000_000,
                played=True,
                play_count=2,
                last_played_date="2024-06-15T00:00:00Z",
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-1",
                name="Test Series",
                media_type="Series",
                production_year=2021,
                date_created="2024-02-15T00:00:00Z",
                path="/media/series/Test Series",
                size_bytes=50_000_000_000,
                played=False,
                play_count=0,
                last_played_date=None,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["items"]) == 2
        assert data["total_size_bytes"] == 60_000_000_000

    @pytest.mark.asyncio
    async def test_filter_by_type_movie(self, client: TestClient) -> None:
        """Should filter items by type=movie."""
        token = self._get_auth_token(client, "library_movie@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-filter",
                name="Filter Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-filter",
                name="Filter Series",
                media_type="Series",
                size_bytes=20_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?type=movie", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["media_type"] == "Movie"

    @pytest.mark.asyncio
    async def test_filter_by_type_series(self, client: TestClient) -> None:
        """Should filter items by type=series."""
        token = self._get_auth_token(client, "library_series@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-series-filter",
                name="Filter Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-series-filter",
                name="Filter Series",
                media_type="Series",
                size_bytes=20_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?type=series", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["media_type"] == "Series"

    @pytest.mark.asyncio
    async def test_filter_by_search(self, client: TestClient) -> None:
        """Should filter items by search string (case-insensitive)."""
        token = self._get_auth_token(client, "library_search@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-search-1",
                name="The Matrix",
                media_type="Movie",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-search-2",
                name="Star Wars",
                media_type="Movie",
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?search=matrix", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "The Matrix"

    @pytest.mark.asyncio
    async def test_filter_by_watched_true(self, client: TestClient) -> None:
        """Should filter items by watched=true."""
        token = self._get_auth_token(client, "library_watched@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-watched-1",
                name="Watched Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
                played=True,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-watched-2",
                name="Unwatched Movie",
                media_type="Movie",
                size_bytes=15_000_000_000,
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?watched=true", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Watched Movie"

    @pytest.mark.asyncio
    async def test_filter_by_watched_false(self, client: TestClient) -> None:
        """Should filter items by watched=false."""
        token = self._get_auth_token(client, "library_unwatched@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-unwatched-1",
                name="Watched Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
                played=True,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-unwatched-2",
                name="Unwatched Movie",
                media_type="Movie",
                size_bytes=15_000_000_000,
                played=False,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?watched=false", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Unwatched Movie"

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(self, client: TestClient) -> None:
        """Should sort items by name ascending."""
        token = self._get_auth_token(client, "library_sort_name@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-sort-1",
                name="Zebra Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-sort-2",
                name="Alpha Movie",
                media_type="Movie",
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?sort=name&order=asc", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Alpha Movie"
        assert data["items"][1]["name"] == "Zebra Movie"

    @pytest.mark.asyncio
    async def test_sort_by_size_desc(self, client: TestClient) -> None:
        """Should sort items by size descending."""
        token = self._get_auth_token(client, "library_sort_size@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-size-1",
                name="Small Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-size-2",
                name="Large Movie",
                media_type="Movie",
                size_bytes=20_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?sort=size&order=desc", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Large Movie"
        assert data["items"][1]["name"] == "Small Movie"

    @pytest.mark.asyncio
    async def test_sort_by_year_asc(self, client: TestClient) -> None:
        """Should sort items by production year ascending."""
        token = self._get_auth_token(client, "library_sort_year@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-year-1",
                name="New Movie",
                media_type="Movie",
                production_year=2023,
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-year-2",
                name="Old Movie",
                media_type="Movie",
                production_year=1990,
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?sort=year&order=asc", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Old Movie"
        assert data["items"][1]["name"] == "New Movie"

    @pytest.mark.asyncio
    async def test_filter_by_min_year(self, client: TestClient) -> None:
        """Should filter items by min_year."""
        token = self._get_auth_token(client, "library_min_year@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-min-year-1",
                name="Recent Movie",
                media_type="Movie",
                production_year=2022,
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-min-year-2",
                name="Old Movie",
                media_type="Movie",
                production_year=2015,
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?min_year=2020", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Recent Movie"

    @pytest.mark.asyncio
    async def test_filter_by_max_year(self, client: TestClient) -> None:
        """Should filter items by max_year."""
        token = self._get_auth_token(client, "library_max_year@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-max-year-1",
                name="Recent Movie",
                media_type="Movie",
                production_year=2022,
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-max-year-2",
                name="Classic Movie",
                media_type="Movie",
                production_year=2000,
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?max_year=2010", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Classic Movie"

    @pytest.mark.asyncio
    async def test_filter_by_min_size_gb(self, client: TestClient) -> None:
        """Should filter items by min_size_gb."""
        token = self._get_auth_token(client, "library_min_size@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-min-size-1",
                name="Large Movie",
                media_type="Movie",
                size_bytes=15_000_000_000,  # ~14 GB
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-min-size-2",
                name="Small Movie",
                media_type="Movie",
                size_bytes=2_000_000_000,  # ~2 GB
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?min_size_gb=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Large Movie"

    @pytest.mark.asyncio
    async def test_filter_by_max_size_gb(self, client: TestClient) -> None:
        """Should filter items by max_size_gb."""
        token = self._get_auth_token(client, "library_max_size@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-max-size-1",
                name="Large Movie",
                media_type="Movie",
                size_bytes=20_000_000_000,  # ~19 GB
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-max-size-2",
                name="Small Movie",
                media_type="Movie",
                size_bytes=5_000_000_000,  # ~5 GB
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?max_size_gb=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["items"][0]["name"] == "Small Movie"

    @pytest.mark.asyncio
    async def test_response_includes_service_urls(self, client: TestClient) -> None:
        """Should include service URLs in response."""
        token = self._get_auth_token(client, "library_urls@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Set up user settings with URLs
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=user_id,
                jellyfin_server_url="https://jellyfin.example.com",
            )
            session.add(settings)
            await session.commit()

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "service_urls" in data
        assert data["service_urls"]["jellyfin_url"] == "https://jellyfin.example.com"

    @pytest.mark.asyncio
    async def test_response_item_includes_all_fields(self, client: TestClient) -> None:
        """Should include all required fields in each item."""
        token = self._get_auth_token(client, "library_fields@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-fields-1",
                name="Complete Movie",
                media_type="Movie",
                production_year=2020,
                date_created="2024-01-15T00:00:00Z",
                size_bytes=10_000_000_000,
                played=True,
                last_played_date="2024-06-15T00:00:00Z",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            session.add(item)
            await session.commit()

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()
        item = data["items"][0]

        # Verify all required fields are present
        assert "jellyfin_id" in item
        assert "name" in item
        assert "media_type" in item
        assert "production_year" in item
        assert "size_bytes" in item
        assert "size_formatted" in item
        assert "played" in item
        assert "last_played_date" in item
        assert "date_created" in item
        assert "tmdb_id" in item

    @pytest.mark.asyncio
    async def test_sort_by_date_added(self, client: TestClient) -> None:
        """Should sort items by date_added (date_created)."""
        token = self._get_auth_token(client, "library_sort_added@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-added-1",
                name="Old Addition",
                media_type="Movie",
                date_created="2023-01-15T00:00:00Z",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-added-2",
                name="New Addition",
                media_type="Movie",
                date_created="2024-06-15T00:00:00Z",
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?sort=date_added&order=desc", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "New Addition"
        assert data["items"][1]["name"] == "Old Addition"

    @pytest.mark.asyncio
    async def test_sort_by_last_watched(self, client: TestClient) -> None:
        """Should sort items by last_watched date."""
        token = self._get_auth_token(client, "library_sort_watched@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-last-watched-1",
                name="Recently Watched",
                media_type="Movie",
                last_played_date="2024-06-15T00:00:00Z",
                played=True,
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-last-watched-2",
                name="Watched Long Ago",
                media_type="Movie",
                last_played_date="2023-01-15T00:00:00Z",
                played=True,
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        response = client.get("/api/library?sort=last_watched&order=desc", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Recently Watched"
        assert data["items"][1]["name"] == "Watched Long Ago"

    @pytest.mark.asyncio
    async def test_default_sort_is_name_asc(self, client: TestClient) -> None:
        """Default sort should be by name ascending."""
        token = self._get_auth_token(client, "library_default_sort@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-default-sort-1",
                name="Zebra Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
            )
            item2 = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-default-sort-2",
                name="Alpha Movie",
                media_type="Movie",
                size_bytes=15_000_000_000,
            )
            session.add_all([item1, item2])
            await session.commit()

        # No sort/order params - should default to name asc
        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["name"] == "Alpha Movie"
        assert data["items"][1]["name"] == "Zebra Movie"

    @pytest.mark.asyncio
    async def test_series_includes_sonarr_title_slug(self, client: TestClient) -> None:
        """Series items should include sonarr_title_slug when Sonarr is configured."""
        from unittest.mock import AsyncMock, patch

        token = self._get_auth_token(client, "library_sonarr_slug@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create series with TMDB ID in ProviderIds
            series = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-slug-1",
                name="Arcane",
                media_type="Series",
                size_bytes=50_000_000_000,
                raw_data={"ProviderIds": {"Tmdb": "94605"}},  # Arcane's TMDB ID
            )
            # Create a movie to verify it returns null for sonarr_title_slug
            movie = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="movie-slug-1",
                name="Test Movie",
                media_type="Movie",
                size_bytes=10_000_000_000,
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            # Set up Sonarr settings
            settings = UserSettings(
                user_id=user_id,
                sonarr_server_url="https://sonarr.example.com",
                sonarr_api_key_encrypted="encrypted_key",
            )
            session.add_all([series, movie, settings])
            await session.commit()

        # Mock the Sonarr API call to return the slug map
        # Patch at app.services.sonarr since the import is inside get_library()
        mock_slug_map = {94605: "arcane"}  # TMDB ID -> titleSlug mapping
        with patch(
            "app.services.sonarr.get_sonarr_tmdb_to_slug_map", new_callable=AsyncMock
        ) as mock_sonarr:
            mock_sonarr.return_value = mock_slug_map
            with patch("app.services.sonarr.get_decrypted_sonarr_api_key") as mock_key:
                mock_key.return_value = "test_api_key"

                response = client.get("/api/library", headers=headers)
                assert response.status_code == 200
                data = response.json()

                # Find the series and movie in response
                items_by_name = {item["name"]: item for item in data["items"]}

                # Series should have sonarr_title_slug
                assert "Arcane" in items_by_name
                assert items_by_name["Arcane"]["sonarr_title_slug"] == "arcane"

                # Movie should have sonarr_title_slug as null
                assert "Test Movie" in items_by_name
                assert items_by_name["Test Movie"]["sonarr_title_slug"] is None

    @pytest.mark.asyncio
    async def test_series_sonarr_title_slug_null_when_sonarr_not_configured(
        self, client: TestClient
    ) -> None:
        """Series items should have null sonarr_title_slug when Sonarr not configured."""
        token = self._get_auth_token(client, "library_no_sonarr@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        async with TestingAsyncSessionLocal() as session:
            # Create series without Sonarr settings
            series = CachedMediaItem(
                user_id=user_id,
                jellyfin_id="series-no-sonarr-1",
                name="Test Series",
                media_type="Series",
                size_bytes=50_000_000_000,
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            session.add(series)
            await session.commit()

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        # sonarr_title_slug should be null (not present or None)
        assert data["items"][0].get("sonarr_title_slug") is None


class TestLibraryPagination:
    """Test GET /api/library pagination functionality (US-59.3)."""

    def _get_auth_token(self, client: TestClient, email: str = "pagination@example.com") -> str:
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

    async def _create_many_items(self, user_id: int, count: int, prefix: str = "Item") -> None:
        """Helper to create multiple cached media items."""
        async with TestingAsyncSessionLocal() as session:
            items = [
                CachedMediaItem(
                    user_id=user_id,
                    jellyfin_id=f"{prefix}-{i}",
                    name=f"{prefix} {i:03d}",  # Zero-pad for consistent sorting
                    media_type="Movie",
                    size_bytes=1_000_000_000,  # 1 GB each
                )
                for i in range(count)
            ]
            session.add_all(items)
            await session.commit()

    @pytest.mark.asyncio
    async def test_default_pagination_returns_50_items(self, client: TestClient) -> None:
        """Default pagination should return 50 items per page."""
        token = self._get_auth_token(client, "pagination_default@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 75 items
        await self._create_many_items(user_id, 75, "Pagination")

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should return only 50 items (default limit)
        assert len(data["items"]) == 50
        # total_count should reflect ALL matching items, not just current page
        assert data["total_count"] == 75
        # Should include pagination info
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["total_pages"] == 2  # ceil(75 / 50)

    @pytest.mark.asyncio
    async def test_pagination_with_custom_limit(self, client: TestClient) -> None:
        """Should support custom page_size (limit) parameter."""
        token = self._get_auth_token(client, "pagination_limit@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 30 items
        await self._create_many_items(user_id, 30, "Limit")

        response = client.get("/api/library?page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 10
        assert data["total_count"] == 30
        assert data["page_size"] == 10
        assert data["total_pages"] == 3  # ceil(30 / 10)

    @pytest.mark.asyncio
    async def test_pagination_page_2(self, client: TestClient) -> None:
        """Should return correct items for page 2."""
        token = self._get_auth_token(client, "pagination_page2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 25 items with zero-padded names for consistent sorting
        await self._create_many_items(user_id, 25, "Page")

        # Get page 2 with 10 items per page
        response = client.get("/api/library?page=2&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 10
        assert data["page"] == 2
        assert data["total_count"] == 25
        # Items should be Page 010 through Page 019 (sorted by name)
        assert data["items"][0]["name"] == "Page 010"
        assert data["items"][9]["name"] == "Page 019"

    @pytest.mark.asyncio
    async def test_pagination_last_page_partial(self, client: TestClient) -> None:
        """Last page may have fewer items than page_size."""
        token = self._get_auth_token(client, "pagination_last@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 25 items
        await self._create_many_items(user_id, 25, "Last")

        # Get page 3 with 10 items per page (should have only 5 items)
        response = client.get("/api/library?page=3&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 5
        assert data["page"] == 3
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_pagination_beyond_last_page_returns_empty(self, client: TestClient) -> None:
        """Requesting page beyond total pages should return empty items."""
        token = self._get_auth_token(client, "pagination_beyond@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 10 items
        await self._create_many_items(user_id, 10, "Beyond")

        # Request page 5 when there's only 1 page
        response = client.get("/api/library?page=5&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 0
        assert data["page"] == 5
        assert data["total_count"] == 10
        assert data["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_pagination_with_filters(self, client: TestClient) -> None:
        """Pagination should work correctly with filters applied."""
        token = self._get_auth_token(client, "pagination_filter@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 20 movies and 20 series
        async with TestingAsyncSessionLocal() as session:
            items = []
            for i in range(20):
                items.append(
                    CachedMediaItem(
                        user_id=user_id,
                        jellyfin_id=f"movie-filter-{i}",
                        name=f"Movie {i:03d}",
                        media_type="Movie",
                        size_bytes=1_000_000_000,
                    )
                )
                items.append(
                    CachedMediaItem(
                        user_id=user_id,
                        jellyfin_id=f"series-filter-{i}",
                        name=f"Series {i:03d}",
                        media_type="Series",
                        size_bytes=2_000_000_000,
                    )
                )
            session.add_all(items)
            await session.commit()

        # Filter by movies only, page 2 with 10 per page
        response = client.get("/api/library?type=movie&page=2&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Should return 10 items from movies only
        assert len(data["items"]) == 10
        assert data["total_count"] == 20  # Only movies, not series
        assert data["total_pages"] == 2
        # All items should be movies
        for item in data["items"]:
            assert item["media_type"] == "Movie"

    @pytest.mark.asyncio
    async def test_pagination_with_search(self, client: TestClient) -> None:
        """Pagination should work correctly with search filter."""
        token = self._get_auth_token(client, "pagination_search@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create items: 15 with "Matrix" in name, 15 without
        async with TestingAsyncSessionLocal() as session:
            items = []
            for i in range(15):
                items.append(
                    CachedMediaItem(
                        user_id=user_id,
                        jellyfin_id=f"matrix-{i}",
                        name=f"The Matrix {i:03d}",
                        media_type="Movie",
                        size_bytes=1_000_000_000,
                    )
                )
                items.append(
                    CachedMediaItem(
                        user_id=user_id,
                        jellyfin_id=f"other-{i}",
                        name=f"Other Movie {i:03d}",
                        media_type="Movie",
                        size_bytes=1_000_000_000,
                    )
                )
            session.add_all(items)
            await session.commit()

        # Search for "Matrix" with pagination
        response = client.get("/api/library?search=Matrix&page=1&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 10
        assert data["total_count"] == 15  # Only Matrix movies
        assert data["total_pages"] == 2

    @pytest.mark.asyncio
    async def test_total_size_is_for_all_matching_items(self, client: TestClient) -> None:
        """total_size should be calculated for all matching items, not just current page."""
        token = self._get_auth_token(client, "pagination_size@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 20 items at 1 GB each = 20 GB total
        await self._create_many_items(user_id, 20, "Size")

        # Get page 1 with 5 items per page
        response = client.get("/api/library?page=1&page_size=5", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 5
        # total_size_bytes should be for ALL 20 items, not just page 1
        assert data["total_size_bytes"] == 20_000_000_000

    @pytest.mark.asyncio
    async def test_page_size_max_limit_rejects_over_100(self, client: TestClient) -> None:
        """page_size over 100 should be rejected with 422."""
        token = self._get_auth_token(client, "pagination_max@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Request 500 items per page - should be rejected (max is 100)
        response = client.get("/api/library?page_size=500", headers=headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_page_size_min_limit_rejects_zero(self, client: TestClient) -> None:
        """page_size of 0 or less should be rejected with 422."""
        token = self._get_auth_token(client, "pagination_min@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        # Request 0 items per page - should be rejected (min is 1)
        response = client.get("/api/library?page_size=0", headers=headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_page_size_100_is_valid(self, client: TestClient) -> None:
        """page_size of 100 should be valid."""
        token = self._get_auth_token(client, "pagination_100@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        # Create 110 items
        await self._create_many_items(user_id, 110, "Max100")

        response = client.get("/api/library?page_size=100", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 100
        assert data["page_size"] == 100

    @pytest.mark.asyncio
    async def test_page_defaults_to_1(self, client: TestClient) -> None:
        """page should default to 1 when not specified."""
        token = self._get_auth_token(client, "pagination_default_page@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/auth/me", headers=headers)
        user_id = me_response.json()["id"]

        await self._create_many_items(user_id, 10, "DefaultPage")

        response = client.get("/api/library", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
