"""Unit tests for Radarr service functions (US-60.6).

Tests for:
- validate_radarr_connection() network errors (timeout, connection error, DNS error)
- save_radarr_settings() update existing settings path
- get_user_radarr_settings() database queries
- get_decrypted_radarr_api_key() null handling
- get_radarr_movie_by_tmdb_id() API error handling
- delete_radarr_movie() deletion handling
- delete_movie_by_tmdb_id() combined lookup and delete
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.database import UserSettings
from app.services.radarr import (
    delete_movie_by_tmdb_id,
    delete_radarr_movie,
    get_decrypted_radarr_api_key,
    get_radarr_movie_by_tmdb_id,
    get_user_radarr_settings,
    save_radarr_settings,
    validate_radarr_connection,
)
from tests.conftest import TestingAsyncSessionLocal


class TestValidateRadarrConnection:
    """Tests for validate_radarr_connection function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_success(self) -> None:
        """Should return True when Radarr returns 200 status."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = await validate_radarr_connection(
                "https://radarr.example.com",
                "test-api-key",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_uses_system_status_endpoint(self) -> None:
        """Should call /api/v3/system/status endpoint for validation."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_radarr_connection(
                "https://radarr.example.com",
                "test-api-key",
            )

            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/api/v3/system/status" in url
            assert url == "https://radarr.example.com/api/v3/system/status"

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        """Should send X-Api-Key header with request."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_radarr_connection(
                "https://radarr.example.com",
                "my-secret-api-key",
            )

            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Api-Key") == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_radarr_connection(
                "https://radarr.example.com/",  # Trailing slash
                "test-api-key",
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            # Should not have double slashes
            assert "//api" not in url
            assert url == "https://radarr.example.com/api/v3/system/status"

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Should return False when API key is invalid (401)."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await validate_radarr_connection(
                "https://radarr.example.com",
                "invalid-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_403_forbidden(self) -> None:
        """Should return False when access is forbidden (403)."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response

            result = await validate_radarr_connection(
                "https://radarr.example.com",
                "limited-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_404_not_found(self) -> None:
        """Should return False when endpoint not found (404)."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            result = await validate_radarr_connection(
                "https://not-radarr.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_500_server_error(self) -> None:
        """Should return False when server returns 500."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response

            result = await validate_radarr_connection(
                "https://radarr.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False on timeout."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await validate_radarr_connection(
                "https://slow.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False on connection error."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await validate_radarr_connection(
                "https://nonexistent.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_dns_error(self) -> None:
        """Should return False on DNS resolution failure."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Name or service not known")

            result = await validate_radarr_connection(
                "https://invalid-hostname.local",
                "test-api-key",
            )

            assert result is False


class TestGetUserRadarrSettings:
    """Tests for get_user_radarr_settings function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_settings(self) -> None:
        """Should return None when user has no settings."""
        async with TestingAsyncSessionLocal() as session:
            result = await get_user_radarr_settings(session, user_id=999)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_settings_when_exists(self) -> None:
        """Should return UserSettings when they exist."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                radarr_server_url="http://radarr:7878",
                radarr_api_key_encrypted="encrypted_key",
            )
            session.add(settings)
            await session.commit()

            result = await get_user_radarr_settings(session, user_id=1)
            assert result is not None
            assert result.radarr_server_url == "http://radarr:7878"
            assert result.radarr_api_key_encrypted == "encrypted_key"

    @pytest.mark.asyncio
    async def test_returns_correct_user_settings(self) -> None:
        """Should return settings for the correct user only (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            settings1 = UserSettings(
                user_id=1,
                radarr_server_url="http://user1-radarr:7878",
            )
            settings2 = UserSettings(
                user_id=2,
                radarr_server_url="http://user2-radarr:7878",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            result = await get_user_radarr_settings(session, user_id=2)
            assert result is not None
            assert result.radarr_server_url == "http://user2-radarr:7878"


class TestSaveRadarrSettings:
    """Tests for save_radarr_settings function."""

    @pytest.mark.asyncio
    async def test_creates_new_settings(self) -> None:
        """Should create new UserSettings when none exist."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878",
                api_key="test-api-key",
            )
            await session.commit()

            assert result is not None
            assert result.user_id == 1
            assert result.radarr_server_url == "http://radarr:7878"
            assert result.radarr_api_key_encrypted is not None
            # API key should be encrypted, not plain text
            assert result.radarr_api_key_encrypted != "test-api-key"

    @pytest.mark.asyncio
    async def test_updates_existing_settings(self) -> None:
        """Should update existing UserSettings."""
        async with TestingAsyncSessionLocal() as session:
            # Create initial settings
            initial_settings = UserSettings(
                user_id=1,
                radarr_server_url="http://old-radarr:7878",
                radarr_api_key_encrypted="old_encrypted_key",
            )
            session.add(initial_settings)
            await session.commit()

            # Update settings
            result = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://new-radarr:7878",
                api_key="new-api-key",
            )
            await session.commit()

            assert result.radarr_server_url == "http://new-radarr:7878"
            # API key should be updated and encrypted
            assert result.radarr_api_key_encrypted != "old_encrypted_key"
            assert result.radarr_api_key_encrypted != "new-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878/",  # Trailing slash
                api_key="test-api-key",
            )
            await session.commit()

            # Trailing slash should be removed
            assert result.radarr_server_url == "http://radarr:7878"

    @pytest.mark.asyncio
    async def test_encrypts_api_key(self) -> None:
        """Should encrypt the API key before storing."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878",
                api_key="my-secret-api-key",
            )
            await session.commit()

            # The stored value should not be the plain text key
            assert result.radarr_api_key_encrypted != "my-secret-api-key"
            # It should be a non-empty encrypted string
            assert result.radarr_api_key_encrypted is not None
            assert len(result.radarr_api_key_encrypted) > 0

    @pytest.mark.asyncio
    async def test_preserves_user_isolation(self) -> None:
        """Should only update settings for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            # Create settings for two users
            settings1 = UserSettings(
                user_id=1,
                radarr_server_url="http://user1-radarr:7878",
                radarr_api_key_encrypted="user1_key",
            )
            settings2 = UserSettings(
                user_id=2,
                radarr_server_url="http://user2-radarr:7878",
                radarr_api_key_encrypted="user2_key",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            # Update only user 1's settings
            await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://user1-new-radarr:7878",
                api_key="new-api-key",
            )
            await session.commit()

            # User 2's settings should be unchanged
            user2_settings = await get_user_radarr_settings(session, user_id=2)
            assert user2_settings is not None
            assert user2_settings.radarr_server_url == "http://user2-radarr:7878"


class TestGetDecryptedRadarrApiKey:
    """Tests for get_decrypted_radarr_api_key function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_encrypted_key(self) -> None:
        """Should return None when radarr_api_key_encrypted is None."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                radarr_server_url="http://radarr:7878",
                radarr_api_key_encrypted=None,  # No API key set
            )
            session.add(settings)
            await session.commit()

            result = get_decrypted_radarr_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_decrypted_key(self) -> None:
        """Should return the decrypted API key when encrypted key exists."""
        async with TestingAsyncSessionLocal() as session:
            # Use save_radarr_settings to properly encrypt the key
            settings = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878",
                api_key="my-secret-api-key",
            )
            await session.commit()

            result = get_decrypted_radarr_api_key(settings)
            assert result == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_handles_empty_string_key(self) -> None:
        """Should handle empty string as encrypted key (returns empty or None)."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                radarr_server_url="http://radarr:7878",
                radarr_api_key_encrypted="",  # Empty string
            )
            session.add(settings)
            await session.commit()

            # Empty string is falsy, so should return None
            result = get_decrypted_radarr_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_special_characters(self) -> None:
        """Should correctly decrypt API keys with special characters."""
        async with TestingAsyncSessionLocal() as session:
            special_key = "abc!@#$%^&*()_+{}|:<>?-=[]\\;',./`~"
            settings = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878",
                api_key=special_key,
            )
            await session.commit()

            result = get_decrypted_radarr_api_key(settings)
            assert result == special_key

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_unicode(self) -> None:
        """Should correctly decrypt API keys with unicode characters."""
        async with TestingAsyncSessionLocal() as session:
            unicode_key = "api-key-with-émojis-🔐-and-汉字"
            settings = await save_radarr_settings(
                session,
                user_id=1,
                server_url="http://radarr:7878",
                api_key=unicode_key,
            )
            await session.commit()

            result = get_decrypted_radarr_api_key(settings)
            assert result == unicode_key


class TestGetRadarrMovieByTmdbId:
    """Tests for get_radarr_movie_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_returns_movie_id_on_match(self) -> None:
        """Should return Radarr movie ID when TMDB ID matches."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 10, "tmdbId": 12345, "title": "Test Movie"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result == 10

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_response(self) -> None:
        """Should return None when movie list is empty."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            result = await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_non_200_response(self) -> None:
        """Should return None when API returns non-200 status."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "invalid-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self) -> None:
        """Should return None on timeout."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await get_radarr_movie_by_tmdb_id(
                "https://slow.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self) -> None:
        """Should return None on connection error."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await get_radarr_movie_by_tmdb_id(
                "https://nonexistent.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_uses_movie_endpoint_with_tmdb_id_param(self) -> None:
        """Should call /api/v3/movie endpoint with tmdbId param."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/api/v3/movie" in url
            params = call_args[1].get("params", {})
            assert params.get("tmdbId") == 12345

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com/",  # Trailing slash
                "test-api-key",
                tmdb_id=12345,
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "//api" not in url

    @pytest.mark.asyncio
    async def test_handles_movie_with_none_id(self) -> None:
        """Should return None when movie ID is None."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": None, "tmdbId": 12345, "title": "Movie with None ID"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_first_movie_when_multiple_matches(self) -> None:
        """Should return first movie ID when multiple movies match."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 10, "tmdbId": 12345, "title": "Movie 1"},
                {"id": 20, "tmdbId": 12345, "title": "Movie 2"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_radarr_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result == 10


class TestDeleteRadarrMovie:
    """Tests for delete_radarr_movie function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_success(self) -> None:
        """Should return True when deletion succeeds."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            result = await delete_radarr_movie(
                "https://radarr.example.com",
                "test-api-key",
                radarr_id=123,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_sends_delete_request_with_correct_url(self) -> None:
        """Should send DELETE request to correct endpoint."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_radarr_movie(
                "https://radarr.example.com",
                "test-api-key",
                radarr_id=123,
            )

            mock_client.delete.assert_called_once()
            call_args = mock_client.delete.call_args
            url = call_args[0][0]
            assert url == "https://radarr.example.com/api/v3/movie/123"

    @pytest.mark.asyncio
    async def test_sends_delete_files_param_true_by_default(self) -> None:
        """Should send deleteFiles=true by default."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_radarr_movie(
                "https://radarr.example.com",
                "test-api-key",
                radarr_id=123,
            )

            call_args = mock_client.delete.call_args
            params = call_args[1].get("params", {})
            assert params.get("deleteFiles") == "true"

    @pytest.mark.asyncio
    async def test_sends_delete_files_param_false_when_specified(self) -> None:
        """Should send deleteFiles=false when specified."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_radarr_movie(
                "https://radarr.example.com",
                "test-api-key",
                radarr_id=123,
                delete_files=False,
            )

            call_args = mock_client.delete.call_args
            params = call_args[1].get("params", {})
            assert params.get("deleteFiles") == "false"

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200_response(self) -> None:
        """Should return False when API returns non-200 status."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.delete.return_value = mock_response

            result = await delete_radarr_movie(
                "https://radarr.example.com",
                "test-api-key",
                radarr_id=999,  # Non-existent
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False on timeout."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.delete.side_effect = httpx.TimeoutException("Request timed out")

            result = await delete_radarr_movie(
                "https://slow.example.com",
                "test-api-key",
                radarr_id=123,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False on connection error."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.delete.side_effect = httpx.RequestError("Connection refused")

            result = await delete_radarr_movie(
                "https://nonexistent.example.com",
                "test-api-key",
                radarr_id=123,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.radarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_radarr_movie(
                "https://radarr.example.com/",  # Trailing slash
                "test-api-key",
                radarr_id=123,
            )

            call_args = mock_client.delete.call_args
            url = call_args[0][0]
            assert "//api" not in url


class TestDeleteMovieByTmdbId:
    """Tests for delete_movie_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_returns_success_when_found_and_deleted(self) -> None:
        """Should return (True, success message) when movie is found and deleted."""
        with patch("app.services.radarr.get_radarr_movie_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.radarr.delete_radarr_movie") as mock_delete:
                mock_delete.return_value = True

                success, message = await delete_movie_by_tmdb_id(
                    "https://radarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                )

                assert success is True
                assert "successfully" in message.lower()

    @pytest.mark.asyncio
    async def test_returns_failure_when_not_found(self) -> None:
        """Should return (False, not found message) when TMDB ID not found."""
        with patch("app.services.radarr.get_radarr_movie_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = None

            success, message = await delete_movie_by_tmdb_id(
                "https://radarr.example.com",
                "test-api-key",
                tmdb_id=99999,
            )

            assert success is False
            assert "not found" in message.lower()
            assert "99999" in message

    @pytest.mark.asyncio
    async def test_returns_failure_when_delete_fails(self) -> None:
        """Should return (False, failure message) when delete operation fails."""
        with patch("app.services.radarr.get_radarr_movie_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.radarr.delete_radarr_movie") as mock_delete:
                mock_delete.return_value = False

                success, message = await delete_movie_by_tmdb_id(
                    "https://radarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                )

                assert success is False
                assert "failed" in message.lower()

    @pytest.mark.asyncio
    async def test_passes_delete_files_parameter(self) -> None:
        """Should pass delete_files parameter to delete function."""
        with patch("app.services.radarr.get_radarr_movie_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.radarr.delete_radarr_movie") as mock_delete:
                mock_delete.return_value = True

                await delete_movie_by_tmdb_id(
                    "https://radarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                    delete_files=False,
                )

                mock_delete.assert_called_once_with(
                    "https://radarr.example.com",
                    "test-api-key",
                    123,
                    False,
                )

    @pytest.mark.asyncio
    async def test_default_delete_files_is_true(self) -> None:
        """Should default to delete_files=True."""
        with patch("app.services.radarr.get_radarr_movie_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.radarr.delete_radarr_movie") as mock_delete:
                mock_delete.return_value = True

                await delete_movie_by_tmdb_id(
                    "https://radarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                )

                mock_delete.assert_called_once_with(
                    "https://radarr.example.com",
                    "test-api-key",
                    123,
                    True,
                )
