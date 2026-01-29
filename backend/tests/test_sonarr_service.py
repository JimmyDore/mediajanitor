"""Unit tests for Sonarr service functions (US-60.5).

Tests for:
- validate_sonarr_connection() timeout handling and network errors
- save_sonarr_settings() create vs update paths
- get_sonarr_series_by_tmdb_id() API error handling
- get_sonarr_tmdb_to_slug_map() empty response handling
- get_decrypted_sonarr_api_key() null handling
- get_user_sonarr_settings() database queries
- delete_sonarr_series() deletion handling
- delete_series_by_tmdb_id() combined lookup and delete
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.database import UserSettings
from app.services.sonarr import (
    delete_series_by_tmdb_id,
    delete_sonarr_series,
    get_decrypted_sonarr_api_key,
    get_sonarr_series_by_tmdb_id,
    get_sonarr_tmdb_to_slug_map,
    get_user_sonarr_settings,
    save_sonarr_settings,
    validate_sonarr_connection,
)
from tests.conftest import TestingAsyncSessionLocal


class TestValidateSonarrConnection:
    """Tests for validate_sonarr_connection function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_success(self) -> None:
        """Should return True when Sonarr returns 200 status."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = await validate_sonarr_connection(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_uses_system_status_endpoint(self) -> None:
        """Should call /api/v3/system/status endpoint for validation."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_sonarr_connection(
                "https://sonarr.example.com",
                "test-api-key",
            )

            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/api/v3/system/status" in url
            assert url == "https://sonarr.example.com/api/v3/system/status"

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        """Should send X-Api-Key header with request."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_sonarr_connection(
                "https://sonarr.example.com",
                "my-secret-api-key",
            )

            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Api-Key") == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_sonarr_connection(
                "https://sonarr.example.com/",  # Trailing slash
                "test-api-key",
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            # Should not have double slashes
            assert "//api" not in url
            assert url == "https://sonarr.example.com/api/v3/system/status"

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Should return False when API key is invalid (401)."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await validate_sonarr_connection(
                "https://sonarr.example.com",
                "invalid-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_403_forbidden(self) -> None:
        """Should return False when access is forbidden (403)."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response

            result = await validate_sonarr_connection(
                "https://sonarr.example.com",
                "limited-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_404_not_found(self) -> None:
        """Should return False when endpoint not found (404)."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            result = await validate_sonarr_connection(
                "https://not-sonarr.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_500_server_error(self) -> None:
        """Should return False when server returns 500."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response

            result = await validate_sonarr_connection(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False on timeout."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await validate_sonarr_connection(
                "https://slow.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False on connection error."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await validate_sonarr_connection(
                "https://nonexistent.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_dns_error(self) -> None:
        """Should return False on DNS resolution failure."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Name or service not known")

            result = await validate_sonarr_connection(
                "https://invalid-hostname.local",
                "test-api-key",
            )

            assert result is False


class TestGetUserSonarrSettings:
    """Tests for get_user_sonarr_settings function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_settings(self) -> None:
        """Should return None when user has no settings."""
        async with TestingAsyncSessionLocal() as session:
            result = await get_user_sonarr_settings(session, user_id=999)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_settings_when_exists(self) -> None:
        """Should return UserSettings when they exist."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                sonarr_server_url="http://sonarr:8989",
                sonarr_api_key_encrypted="encrypted_key",
            )
            session.add(settings)
            await session.commit()

            result = await get_user_sonarr_settings(session, user_id=1)
            assert result is not None
            assert result.sonarr_server_url == "http://sonarr:8989"
            assert result.sonarr_api_key_encrypted == "encrypted_key"

    @pytest.mark.asyncio
    async def test_returns_correct_user_settings(self) -> None:
        """Should return settings for the correct user only (user isolation)."""
        async with TestingAsyncSessionLocal() as session:
            settings1 = UserSettings(
                user_id=1,
                sonarr_server_url="http://user1-sonarr:8989",
            )
            settings2 = UserSettings(
                user_id=2,
                sonarr_server_url="http://user2-sonarr:8989",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            result = await get_user_sonarr_settings(session, user_id=2)
            assert result is not None
            assert result.sonarr_server_url == "http://user2-sonarr:8989"


class TestSaveSonarrSettings:
    """Tests for save_sonarr_settings function."""

    @pytest.mark.asyncio
    async def test_creates_new_settings(self) -> None:
        """Should create new UserSettings when none exist."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989",
                api_key="test-api-key",
            )
            await session.commit()

            assert result is not None
            assert result.user_id == 1
            assert result.sonarr_server_url == "http://sonarr:8989"
            assert result.sonarr_api_key_encrypted is not None
            # API key should be encrypted, not plain text
            assert result.sonarr_api_key_encrypted != "test-api-key"

    @pytest.mark.asyncio
    async def test_updates_existing_settings(self) -> None:
        """Should update existing UserSettings."""
        async with TestingAsyncSessionLocal() as session:
            # Create initial settings
            initial_settings = UserSettings(
                user_id=1,
                sonarr_server_url="http://old-sonarr:8989",
                sonarr_api_key_encrypted="old_encrypted_key",
            )
            session.add(initial_settings)
            await session.commit()

            # Update settings
            result = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://new-sonarr:8989",
                api_key="new-api-key",
            )
            await session.commit()

            assert result.sonarr_server_url == "http://new-sonarr:8989"
            # API key should be updated and encrypted
            assert result.sonarr_api_key_encrypted != "old_encrypted_key"
            assert result.sonarr_api_key_encrypted != "new-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989/",  # Trailing slash
                api_key="test-api-key",
            )
            await session.commit()

            # Trailing slash should be removed
            assert result.sonarr_server_url == "http://sonarr:8989"

    @pytest.mark.asyncio
    async def test_encrypts_api_key(self) -> None:
        """Should encrypt the API key before storing."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989",
                api_key="my-secret-api-key",
            )
            await session.commit()

            # The stored value should not be the plain text key
            assert result.sonarr_api_key_encrypted != "my-secret-api-key"
            # It should be a non-empty encrypted string
            assert result.sonarr_api_key_encrypted is not None
            assert len(result.sonarr_api_key_encrypted) > 0

    @pytest.mark.asyncio
    async def test_preserves_user_isolation(self) -> None:
        """Should only update settings for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            # Create settings for two users
            settings1 = UserSettings(
                user_id=1,
                sonarr_server_url="http://user1-sonarr:8989",
                sonarr_api_key_encrypted="user1_key",
            )
            settings2 = UserSettings(
                user_id=2,
                sonarr_server_url="http://user2-sonarr:8989",
                sonarr_api_key_encrypted="user2_key",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            # Update only user 1's settings
            await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://user1-new-sonarr:8989",
                api_key="new-api-key",
            )
            await session.commit()

            # User 2's settings should be unchanged
            user2_settings = await get_user_sonarr_settings(session, user_id=2)
            assert user2_settings is not None
            assert user2_settings.sonarr_server_url == "http://user2-sonarr:8989"


class TestGetDecryptedSonarrApiKey:
    """Tests for get_decrypted_sonarr_api_key function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_encrypted_key(self) -> None:
        """Should return None when sonarr_api_key_encrypted is None."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                sonarr_server_url="http://sonarr:8989",
                sonarr_api_key_encrypted=None,  # No API key set
            )
            session.add(settings)
            await session.commit()

            result = get_decrypted_sonarr_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_decrypted_key(self) -> None:
        """Should return the decrypted API key when encrypted key exists."""
        async with TestingAsyncSessionLocal() as session:
            # Use save_sonarr_settings to properly encrypt the key
            settings = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989",
                api_key="my-secret-api-key",
            )
            await session.commit()

            result = get_decrypted_sonarr_api_key(settings)
            assert result == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_handles_empty_string_key(self) -> None:
        """Should handle empty string as encrypted key (returns empty or None)."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                sonarr_server_url="http://sonarr:8989",
                sonarr_api_key_encrypted="",  # Empty string
            )
            session.add(settings)
            await session.commit()

            # Empty string is falsy, so should return None
            result = get_decrypted_sonarr_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_special_characters(self) -> None:
        """Should correctly decrypt API keys with special characters."""
        async with TestingAsyncSessionLocal() as session:
            special_key = "abc!@#$%^&*()_+{}|:<>?-=[]\\;',./`~"
            settings = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989",
                api_key=special_key,
            )
            await session.commit()

            result = get_decrypted_sonarr_api_key(settings)
            assert result == special_key

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_unicode(self) -> None:
        """Should correctly decrypt API keys with unicode characters."""
        async with TestingAsyncSessionLocal() as session:
            unicode_key = "api-key-with-émojis-🔐-and-汉字"
            settings = await save_sonarr_settings(
                session,
                user_id=1,
                server_url="http://sonarr:8989",
                api_key=unicode_key,
            )
            await session.commit()

            result = get_decrypted_sonarr_api_key(settings)
            assert result == unicode_key


class TestGetSonarrSeriesByTmdbId:
    """Tests for get_sonarr_series_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_returns_series_id_on_match(self) -> None:
        """Should return Sonarr series ID when TMDB ID matches."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 10, "tmdbId": 12345, "title": "Test Series"},
                {"id": 20, "tmdbId": 67890, "title": "Another Series"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result == 10

    @pytest.mark.asyncio
    async def test_returns_none_when_tmdb_id_not_found(self) -> None:
        """Should return None when TMDB ID is not in series list."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 10, "tmdbId": 12345, "title": "Test Series"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=99999,  # Not in list
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_series_list(self) -> None:
        """Should return None when series list is empty."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_non_200_response(self) -> None:
        """Should return None when API returns non-200 status."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "invalid-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self) -> None:
        """Should return None on timeout."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await get_sonarr_series_by_tmdb_id(
                "https://slow.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self) -> None:
        """Should return None on connection error."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await get_sonarr_series_by_tmdb_id(
                "https://nonexistent.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_uses_series_endpoint(self) -> None:
        """Should call /api/v3/series endpoint."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/api/v3/series" in url

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com/",  # Trailing slash
                "test-api-key",
                tmdb_id=12345,
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "//api" not in url

    @pytest.mark.asyncio
    async def test_handles_series_without_tmdb_id(self) -> None:
        """Should skip series that don't have tmdbId field."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 10, "title": "No TMDB Series"},  # Missing tmdbId
                {"id": 20, "tmdbId": 12345, "title": "With TMDB Series"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result == 20

    @pytest.mark.asyncio
    async def test_handles_series_with_none_id(self) -> None:
        """Should return None when series ID is None."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": None, "tmdbId": 12345, "title": "Series with None ID"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=12345,
            )

            assert result is None


class TestGetSonarrTmdbToSlugMap:
    """Tests for get_sonarr_tmdb_to_slug_map function."""

    @pytest.mark.asyncio
    async def test_returns_mapping_on_success(self) -> None:
        """Should return dict mapping tmdb_id to titleSlug."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"tmdbId": 12345, "titleSlug": "arcane"},
                {"tmdbId": 67890, "titleSlug": "breaking-bad"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {12345: "arcane", 67890: "breaking-bad"}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_empty_response(self) -> None:
        """Should return empty dict when series list is empty."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_non_200_response(self) -> None:
        """Should return empty dict when API returns non-200 status."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_timeout(self) -> None:
        """Should return empty dict on timeout."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await get_sonarr_tmdb_to_slug_map(
                "https://slow.example.com",
                "test-api-key",
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_connection_error(self) -> None:
        """Should return empty dict on connection error."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await get_sonarr_tmdb_to_slug_map(
                "https://nonexistent.example.com",
                "test-api-key",
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_skips_series_without_tmdb_id(self) -> None:
        """Should skip series that don't have tmdbId field."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"titleSlug": "no-tmdb"},  # Missing tmdbId
                {"tmdbId": 12345, "titleSlug": "has-tmdb"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {12345: "has-tmdb"}

    @pytest.mark.asyncio
    async def test_skips_series_without_title_slug(self) -> None:
        """Should skip series that don't have titleSlug field."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"tmdbId": 11111},  # Missing titleSlug
                {"tmdbId": 12345, "titleSlug": "has-slug"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {12345: "has-slug"}

    @pytest.mark.asyncio
    async def test_skips_series_with_empty_title_slug(self) -> None:
        """Should skip series with empty titleSlug."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"tmdbId": 11111, "titleSlug": ""},  # Empty slug
                {"tmdbId": 12345, "titleSlug": "has-slug"},
            ]
            mock_client.get.return_value = mock_response

            result = await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com",
                "test-api-key",
            )

            assert result == {12345: "has-slug"}

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            await get_sonarr_tmdb_to_slug_map(
                "https://sonarr.example.com/",  # Trailing slash
                "test-api-key",
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "//api" not in url


class TestDeleteSonarrSeries:
    """Tests for delete_sonarr_series function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_success(self) -> None:
        """Should return True when deletion succeeds."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            result = await delete_sonarr_series(
                "https://sonarr.example.com",
                "test-api-key",
                sonarr_id=123,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_sends_delete_request_with_correct_url(self) -> None:
        """Should send DELETE request to correct endpoint."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_sonarr_series(
                "https://sonarr.example.com",
                "test-api-key",
                sonarr_id=123,
            )

            mock_client.delete.assert_called_once()
            call_args = mock_client.delete.call_args
            url = call_args[0][0]
            assert url == "https://sonarr.example.com/api/v3/series/123"

    @pytest.mark.asyncio
    async def test_sends_delete_files_param_true_by_default(self) -> None:
        """Should send deleteFiles=true by default."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_sonarr_series(
                "https://sonarr.example.com",
                "test-api-key",
                sonarr_id=123,
            )

            call_args = mock_client.delete.call_args
            params = call_args[1].get("params", {})
            assert params.get("deleteFiles") == "true"

    @pytest.mark.asyncio
    async def test_sends_delete_files_param_false_when_specified(self) -> None:
        """Should send deleteFiles=false when specified."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.delete.return_value = mock_response

            await delete_sonarr_series(
                "https://sonarr.example.com",
                "test-api-key",
                sonarr_id=123,
                delete_files=False,
            )

            call_args = mock_client.delete.call_args
            params = call_args[1].get("params", {})
            assert params.get("deleteFiles") == "false"

    @pytest.mark.asyncio
    async def test_returns_false_on_non_200_response(self) -> None:
        """Should return False when API returns non-200 status."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.delete.return_value = mock_response

            result = await delete_sonarr_series(
                "https://sonarr.example.com",
                "test-api-key",
                sonarr_id=999,  # Non-existent
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False on timeout."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.delete.side_effect = httpx.TimeoutException("Request timed out")

            result = await delete_sonarr_series(
                "https://slow.example.com",
                "test-api-key",
                sonarr_id=123,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False on connection error."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.delete.side_effect = httpx.RequestError("Connection refused")

            result = await delete_sonarr_series(
                "https://nonexistent.example.com",
                "test-api-key",
                sonarr_id=123,
            )

            assert result is False


class TestDeleteSeriesByTmdbId:
    """Tests for delete_series_by_tmdb_id function."""

    @pytest.mark.asyncio
    async def test_returns_success_when_found_and_deleted(self) -> None:
        """Should return (True, success message) when series is found and deleted."""
        with patch("app.services.sonarr.get_sonarr_series_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.sonarr.delete_sonarr_series") as mock_delete:
                mock_delete.return_value = True

                success, message = await delete_series_by_tmdb_id(
                    "https://sonarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                )

                assert success is True
                assert "successfully" in message.lower()

    @pytest.mark.asyncio
    async def test_returns_failure_when_not_found(self) -> None:
        """Should return (False, not found message) when TMDB ID not found."""
        with patch("app.services.sonarr.get_sonarr_series_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = None

            success, message = await delete_series_by_tmdb_id(
                "https://sonarr.example.com",
                "test-api-key",
                tmdb_id=99999,
            )

            assert success is False
            assert "not found" in message.lower()
            assert "99999" in message

    @pytest.mark.asyncio
    async def test_returns_failure_when_delete_fails(self) -> None:
        """Should return (False, failure message) when delete operation fails."""
        with patch("app.services.sonarr.get_sonarr_series_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.sonarr.delete_sonarr_series") as mock_delete:
                mock_delete.return_value = False

                success, message = await delete_series_by_tmdb_id(
                    "https://sonarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                )

                assert success is False
                assert "failed" in message.lower()

    @pytest.mark.asyncio
    async def test_passes_delete_files_parameter(self) -> None:
        """Should pass delete_files parameter to delete function."""
        with patch("app.services.sonarr.get_sonarr_series_by_tmdb_id") as mock_lookup:
            mock_lookup.return_value = 123
            with patch("app.services.sonarr.delete_sonarr_series") as mock_delete:
                mock_delete.return_value = True

                await delete_series_by_tmdb_id(
                    "https://sonarr.example.com",
                    "test-api-key",
                    tmdb_id=12345,
                    delete_files=False,
                )

                mock_delete.assert_called_once_with(
                    "https://sonarr.example.com",
                    "test-api-key",
                    123,
                    False,
                )


class TestGetSonarrHistorySince:
    """Tests for get_sonarr_history_since function (US-63.1)."""

    @pytest.mark.asyncio
    async def test_returns_history_by_tmdb_id(self) -> None:
        """Should return history grouped by TMDB ID."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 12345, "title": "Breaking Bad"},
                    "episode": {
                        "seasonNumber": 2,
                        "episodeNumber": 5,
                        "title": "Breakage",
                    },
                },
                {
                    "id": 2,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 12345, "title": "Breaking Bad"},
                    "episode": {
                        "seasonNumber": 2,
                        "episodeNumber": 6,
                        "title": "Peekaboo",
                    },
                },
            ]
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            assert 12345 in result
            assert len(result[12345]) == 2
            assert result[12345][0]["season"] == 2
            assert result[12345][0]["episode"] == 5

    @pytest.mark.asyncio
    async def test_uses_correct_api_endpoint(self) -> None:
        """Should call /api/v3/history/since with correct parameters."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/api/v3/history/since" in url
            params = call_args[1].get("params", {})
            assert params.get("eventType") == "downloadFolderImported"
            assert params.get("includeSeries") == "true"
            assert params.get("includeEpisode") == "true"

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        """Should send X-Api-Key header."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            await get_sonarr_history_since(
                "https://sonarr.example.com",
                "my-api-key",
                days_back=7,
            )

            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Api-Key") == "my-api-key"

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_empty_response(self) -> None:
        """Should return empty dict when no history."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_non_200_response(self) -> None:
        """Should return empty dict when API returns non-200."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "invalid-key",
                days_back=7,
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_timeout(self) -> None:
        """Should return empty dict on timeout (graceful failure)."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://slow.example.com",
                "test-api-key",
                days_back=7,
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_dict_on_connection_error(self) -> None:
        """Should return empty dict on connection error (graceful failure)."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://nonexistent.example.com",
                "test-api-key",
                days_back=7,
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_skips_entries_without_series_tmdb_id(self) -> None:
        """Should skip history entries that don't have a series TMDB ID."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"title": "No TMDB"},  # Missing tmdbId
                    "episode": {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"},
                },
                {
                    "id": 2,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 12345, "title": "Has TMDB"},
                    "episode": {"seasonNumber": 1, "episodeNumber": 1, "title": "Pilot"},
                },
            ]
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            # Should only have entry for series with TMDB ID
            assert len(result) == 1
            assert 12345 in result

    @pytest.mark.asyncio
    async def test_groups_multiple_series(self) -> None:
        """Should group episodes by their respective series TMDB ID."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 11111, "title": "Series A"},
                    "episode": {"seasonNumber": 1, "episodeNumber": 1, "title": "Ep1"},
                },
                {
                    "id": 2,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 22222, "title": "Series B"},
                    "episode": {"seasonNumber": 1, "episodeNumber": 1, "title": "Ep1"},
                },
                {
                    "id": 3,
                    "date": "2026-01-16T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 11111, "title": "Series A"},
                    "episode": {"seasonNumber": 1, "episodeNumber": 2, "title": "Ep2"},
                },
            ]
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            assert len(result) == 2
            assert 11111 in result
            assert 22222 in result
            assert len(result[11111]) == 2  # Series A has 2 episodes
            assert len(result[22222]) == 1  # Series B has 1 episode

    @pytest.mark.asyncio
    async def test_extracts_episode_details_correctly(self) -> None:
        """Should extract season, episode, title, and added_at correctly."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": 1,
                    "date": "2026-01-15T10:30:00Z",
                    "eventType": "downloadFolderImported",
                    "series": {"tmdbId": 12345, "title": "Test Series"},
                    "episode": {
                        "seasonNumber": 3,
                        "episodeNumber": 7,
                        "title": "The Episode Title",
                    },
                },
            ]
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            result = await get_sonarr_history_since(
                "https://sonarr.example.com",
                "test-api-key",
                days_back=7,
            )

            episode = result[12345][0]
            assert episode["season"] == 3
            assert episode["episode"] == 7
            assert episode["title"] == "The Episode Title"
            assert episode["added_at"] == "2026-01-15T10:30:00Z"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.sonarr.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response

            from app.services.sonarr import get_sonarr_history_since

            await get_sonarr_history_since(
                "https://sonarr.example.com/",  # Trailing slash
                "test-api-key",
                days_back=7,
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "//api" not in url
