"""Unit tests for content_cache service functions (US-60.1).

Tests for:
- get_user_settings()
- lookup_jellyseerr_media_by_tmdb()
- lookup_jellyseerr_media_by_request_id()
- delete_cached_media_by_tmdb_id()
- delete_cached_jellyseerr_request_by_tmdb_id()
- delete_cached_jellyseerr_request_by_id()
"""

import pytest
from sqlalchemy import select

from app.database import CachedJellyseerrRequest, CachedMediaItem, UserSettings
from app.services.content_cache import (
    delete_cached_jellyseerr_request_by_id,
    delete_cached_jellyseerr_request_by_tmdb_id,
    delete_cached_media_by_tmdb_id,
    get_user_settings,
    lookup_jellyseerr_media_by_request_id,
    lookup_jellyseerr_media_by_tmdb,
)
from tests.conftest import TestingAsyncSessionLocal


class TestGetUserSettings:
    """Tests for get_user_settings function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_settings(self) -> None:
        """Should return None when user has no settings."""
        async with TestingAsyncSessionLocal() as session:
            result = await get_user_settings(session, user_id=999)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_settings_when_exists(self) -> None:
        """Should return UserSettings when they exist."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                jellyfin_server_url="http://jellyfin:8096",
                jellyfin_api_key_encrypted="encrypted_key",
            )
            session.add(settings)
            await session.commit()

            result = await get_user_settings(session, user_id=1)
            assert result is not None
            assert result.jellyfin_server_url == "http://jellyfin:8096"

    @pytest.mark.asyncio
    async def test_returns_correct_user_settings(self) -> None:
        """Should return settings for the correct user only."""
        async with TestingAsyncSessionLocal() as session:
            settings1 = UserSettings(
                user_id=1,
                jellyfin_server_url="http://user1-jellyfin:8096",
            )
            settings2 = UserSettings(
                user_id=2,
                jellyfin_server_url="http://user2-jellyfin:8096",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            result = await get_user_settings(session, user_id=2)
            assert result is not None
            assert result.jellyfin_server_url == "http://user2-jellyfin:8096"


class TestLookupJellyseerrMediaByTmdb:
    """Tests for lookup_jellyseerr_media_by_tmdb function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self) -> None:
        """Should return None when no cached request matches."""
        async with TestingAsyncSessionLocal() as session:
            result = await lookup_jellyseerr_media_by_tmdb(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_media_id_when_match(self) -> None:
        """Should return jellyseerr_media_id when matching request exists."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                jellyseerr_media_id=200,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            session.add(request)
            await session.commit()

            result = await lookup_jellyseerr_media_by_tmdb(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            assert result == 200

    @pytest.mark.asyncio
    async def test_filters_by_media_type(self) -> None:
        """Should filter by media type (movie vs tv)."""
        async with TestingAsyncSessionLocal() as session:
            movie_request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                jellyseerr_media_id=200,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            tv_request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=101,
                jellyseerr_media_id=201,
                tmdb_id=12345,  # Same TMDB ID but different media type
                media_type="tv",
                status=5,
                title="Test TV Show",
            )
            session.add_all([movie_request, tv_request])
            await session.commit()

            # Should find movie
            movie_result = await lookup_jellyseerr_media_by_tmdb(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            assert movie_result == 200

            # Should find TV
            tv_result = await lookup_jellyseerr_media_by_tmdb(
                session, user_id=1, tmdb_id=12345, media_type="tv"
            )
            assert tv_result == 201

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Should only return requests for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            request1 = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                jellyseerr_media_id=200,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 1 Movie",
            )
            request2 = CachedJellyseerrRequest(
                user_id=2,
                jellyseerr_id=101,
                jellyseerr_media_id=201,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 2 Movie",
            )
            session.add_all([request1, request2])
            await session.commit()

            result = await lookup_jellyseerr_media_by_tmdb(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            assert result == 200  # User 1's media_id, not user 2's


class TestLookupJellyseerrMediaByRequestId:
    """Tests for lookup_jellyseerr_media_by_request_id function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(self) -> None:
        """Should return None when no cached request matches."""
        async with TestingAsyncSessionLocal() as session:
            result = await lookup_jellyseerr_media_by_request_id(
                session, user_id=1, jellyseerr_id=999
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_media_id_when_match(self) -> None:
        """Should return jellyseerr_media_id when matching request exists."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                jellyseerr_media_id=200,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            session.add(request)
            await session.commit()

            result = await lookup_jellyseerr_media_by_request_id(
                session, user_id=1, jellyseerr_id=100
            )
            assert result == 200

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Should only return requests for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            request1 = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                jellyseerr_media_id=200,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 1 Movie",
            )
            request2 = CachedJellyseerrRequest(
                user_id=2,
                jellyseerr_id=100,  # Same jellyseerr_id but different user
                jellyseerr_media_id=999,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 2 Movie",
            )
            session.add_all([request1, request2])
            await session.commit()

            result = await lookup_jellyseerr_media_by_request_id(
                session, user_id=1, jellyseerr_id=100
            )
            assert result == 200  # User 1's media_id


class TestDeleteCachedMediaByTmdbId:
    """Tests for delete_cached_media_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_match(self) -> None:
        """Should return 0 when no items match the TMDB ID."""
        async with TestingAsyncSessionLocal() as session:
            result = await delete_cached_media_by_tmdb_id(session, user_id=1, tmdb_id=99999)
            assert result == 0

    @pytest.mark.asyncio
    async def test_deletes_matching_item_and_returns_count(self) -> None:
        """Should delete items with matching TMDB ID and return count."""
        async with TestingAsyncSessionLocal() as session:
            item = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-123",
                name="Test Movie",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345", "Imdb": "tt0012345"}},
            )
            session.add(item)
            await session.commit()

            result = await delete_cached_media_by_tmdb_id(session, user_id=1, tmdb_id=12345)
            await session.commit()

            assert result == 1

            # Verify item was deleted
            check = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.jellyfin_id == "movie-123")
            )
            assert check.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Should only delete items for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            item1 = CachedMediaItem(
                user_id=1,
                jellyfin_id="user1-movie",
                name="User 1 Movie",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            item2 = CachedMediaItem(
                user_id=2,
                jellyfin_id="user2-movie",
                name="User 2 Movie",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},  # Same TMDB ID
            )
            session.add_all([item1, item2])
            await session.commit()

            # Delete for user 1 only
            result = await delete_cached_media_by_tmdb_id(session, user_id=1, tmdb_id=12345)
            await session.commit()

            assert result == 1

            # User 2's item should still exist
            check = await session.execute(
                select(CachedMediaItem).where(CachedMediaItem.user_id == 2)
            )
            assert check.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_handles_missing_provider_ids(self) -> None:
        """Should handle items without ProviderIds in raw_data."""
        async with TestingAsyncSessionLocal() as session:
            item_with_ids = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-with-ids",
                name="Movie With IDs",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            item_without_ids = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-without-ids",
                name="Movie Without IDs",
                media_type="Movie",
                raw_data={},  # No ProviderIds
            )
            item_none_raw = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-none-raw",
                name="Movie None Raw",
                media_type="Movie",
                raw_data=None,
            )
            session.add_all([item_with_ids, item_without_ids, item_none_raw])
            await session.commit()

            # Should only delete the one with matching TMDB ID
            result = await delete_cached_media_by_tmdb_id(session, user_id=1, tmdb_id=12345)
            await session.commit()

            assert result == 1

    @pytest.mark.asyncio
    async def test_deletes_multiple_items_with_same_tmdb_id(self) -> None:
        """Should delete all items with the same TMDB ID."""
        async with TestingAsyncSessionLocal() as session:
            # A movie and its associated season might both have the same TMDB ID
            item1 = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-main",
                name="Test Movie",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},
            )
            item2 = CachedMediaItem(
                user_id=1,
                jellyfin_id="movie-extra",
                name="Test Movie Extra",
                media_type="Movie",
                raw_data={"ProviderIds": {"Tmdb": "12345"}},  # Same TMDB
            )
            session.add_all([item1, item2])
            await session.commit()

            result = await delete_cached_media_by_tmdb_id(session, user_id=1, tmdb_id=12345)
            await session.commit()

            assert result == 2


class TestDeleteCachedJellyseerrRequestByTmdbId:
    """Tests for delete_cached_jellyseerr_request_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_deletes_matching_request(self) -> None:
        """Should delete request with matching TMDB ID and media type."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            session.add(request)
            await session.commit()

            await delete_cached_jellyseerr_request_by_tmdb_id(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            await session.commit()

            # Verify deletion
            check = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.jellyseerr_id == 100)
            )
            assert check.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_filters_by_media_type(self) -> None:
        """Should only delete requests with matching media type."""
        async with TestingAsyncSessionLocal() as session:
            movie_request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            tv_request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=101,
                tmdb_id=12345,  # Same TMDB
                media_type="tv",
                status=5,
                title="Test TV",
            )
            session.add_all([movie_request, tv_request])
            await session.commit()

            # Delete only movie
            await delete_cached_jellyseerr_request_by_tmdb_id(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            await session.commit()

            # TV should still exist
            check = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.media_type == "tv")
            )
            assert check.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Should only delete requests for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            request1 = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 1 Movie",
            )
            request2 = CachedJellyseerrRequest(
                user_id=2,
                jellyseerr_id=101,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 2 Movie",
            )
            session.add_all([request1, request2])
            await session.commit()

            # Delete for user 1 only
            await delete_cached_jellyseerr_request_by_tmdb_id(
                session, user_id=1, tmdb_id=12345, media_type="movie"
            )
            await session.commit()

            # User 2's request should still exist
            check = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == 2)
            )
            assert check.scalar_one_or_none() is not None


class TestDeleteCachedJellyseerrRequestById:
    """Tests for delete_cached_jellyseerr_request_by_id function."""

    @pytest.mark.asyncio
    async def test_deletes_matching_request(self) -> None:
        """Should delete request with matching jellyseerr_id."""
        async with TestingAsyncSessionLocal() as session:
            request = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="Test Movie",
            )
            session.add(request)
            await session.commit()

            await delete_cached_jellyseerr_request_by_id(session, user_id=1, jellyseerr_id=100)
            await session.commit()

            # Verify deletion
            check = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.jellyseerr_id == 100)
            )
            assert check.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self) -> None:
        """Should only delete requests for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            request1 = CachedJellyseerrRequest(
                user_id=1,
                jellyseerr_id=100,
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 1 Movie",
            )
            request2 = CachedJellyseerrRequest(
                user_id=2,
                jellyseerr_id=100,  # Same jellyseerr_id, different user
                tmdb_id=12345,
                media_type="movie",
                status=5,
                title="User 2 Movie",
            )
            session.add_all([request1, request2])
            await session.commit()

            # Delete for user 1 only
            await delete_cached_jellyseerr_request_by_id(session, user_id=1, jellyseerr_id=100)
            await session.commit()

            # User 2's request should still exist
            check = await session.execute(
                select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == 2)
            )
            assert check.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_match(self) -> None:
        """Should not raise error when no matching request exists."""
        async with TestingAsyncSessionLocal() as session:
            # This should not raise an error
            await delete_cached_jellyseerr_request_by_id(session, user_id=1, jellyseerr_id=999)
            await session.commit()
