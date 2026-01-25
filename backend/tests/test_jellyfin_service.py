"""Unit tests for Jellyfin service functions (US-60.3).

Tests for:
- validate_jellyfin_connection() success and failure paths
- save_jellyfin_settings() create new and update existing
- get_user_jellyfin_settings()
- get_decrypted_jellyfin_api_key() null handling
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.database import UserSettings
from app.services.jellyfin import (
    get_decrypted_jellyfin_api_key,
    get_user_jellyfin_settings,
    save_jellyfin_settings,
    validate_jellyfin_connection,
)
from tests.conftest import TestingAsyncSessionLocal


class TestValidateJellyfinConnection:
    """Tests for validate_jellyfin_connection function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200_success(self) -> None:
        """Should return True when Jellyfin returns 200 status."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            result = await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "test-api-key",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_uses_system_info_endpoint(self) -> None:
        """Should call /System/Info endpoint for validation."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "test-api-key",
            )

            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            url = call_args[0][0]
            assert "/System/Info" in url
            assert url == "https://jellyfin.example.com/System/Info"

    @pytest.mark.asyncio
    async def test_sends_api_key_header(self) -> None:
        """Should send X-Emby-Token header with request."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "my-secret-api-key",
            )

            call_args = mock_client.get.call_args
            headers = call_args[1].get("headers", {})
            assert headers.get("X-Emby-Token") == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            await validate_jellyfin_connection(
                "https://jellyfin.example.com/",  # Trailing slash
                "test-api-key",
            )

            call_args = mock_client.get.call_args
            url = call_args[0][0]
            # Should not have double slashes
            assert "//System" not in url
            assert url == "https://jellyfin.example.com/System/Info"

    @pytest.mark.asyncio
    async def test_returns_false_on_401_unauthorized(self) -> None:
        """Should return False when API key is invalid (401)."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_client.get.return_value = mock_response

            result = await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "invalid-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_403_forbidden(self) -> None:
        """Should return False when access is forbidden (403)."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 403
            mock_client.get.return_value = mock_response

            result = await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "limited-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_404_not_found(self) -> None:
        """Should return False when endpoint not found (404)."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            result = await validate_jellyfin_connection(
                "https://not-jellyfin.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_500_server_error(self) -> None:
        """Should return False when server returns 500."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_client.get.return_value = mock_response

            result = await validate_jellyfin_connection(
                "https://jellyfin.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Should return False on timeout."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            result = await validate_jellyfin_connection(
                "https://slow.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self) -> None:
        """Should return False on connection error."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection refused")

            result = await validate_jellyfin_connection(
                "https://nonexistent.example.com",
                "test-api-key",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_dns_error(self) -> None:
        """Should return False on DNS resolution failure."""
        with patch("app.services.jellyfin.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Name or service not known")

            result = await validate_jellyfin_connection(
                "https://invalid-hostname.local",
                "test-api-key",
            )

            assert result is False


class TestGetUserJellyfinSettings:
    """Tests for get_user_jellyfin_settings function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_settings(self) -> None:
        """Should return None when user has no settings."""
        async with TestingAsyncSessionLocal() as session:
            result = await get_user_jellyfin_settings(session, user_id=999)
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

            result = await get_user_jellyfin_settings(session, user_id=1)
            assert result is not None
            assert result.jellyfin_server_url == "http://jellyfin:8096"
            assert result.jellyfin_api_key_encrypted == "encrypted_key"

    @pytest.mark.asyncio
    async def test_returns_correct_user_settings(self) -> None:
        """Should return settings for the correct user only (user isolation)."""
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

            result = await get_user_jellyfin_settings(session, user_id=2)
            assert result is not None
            assert result.jellyfin_server_url == "http://user2-jellyfin:8096"


class TestSaveJellyfinSettings:
    """Tests for save_jellyfin_settings function."""

    @pytest.mark.asyncio
    async def test_creates_new_settings(self) -> None:
        """Should create new UserSettings when none exist."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096",
                api_key="test-api-key",
            )
            await session.commit()

            assert result is not None
            assert result.user_id == 1
            assert result.jellyfin_server_url == "http://jellyfin:8096"
            assert result.jellyfin_api_key_encrypted is not None
            # API key should be encrypted, not plain text
            assert result.jellyfin_api_key_encrypted != "test-api-key"

    @pytest.mark.asyncio
    async def test_updates_existing_settings(self) -> None:
        """Should update existing UserSettings."""
        async with TestingAsyncSessionLocal() as session:
            # Create initial settings
            initial_settings = UserSettings(
                user_id=1,
                jellyfin_server_url="http://old-jellyfin:8096",
                jellyfin_api_key_encrypted="old_encrypted_key",
            )
            session.add(initial_settings)
            await session.commit()

            # Update settings
            result = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://new-jellyfin:8096",
                api_key="new-api-key",
            )
            await session.commit()

            assert result.jellyfin_server_url == "http://new-jellyfin:8096"
            # API key should be updated and encrypted
            assert result.jellyfin_api_key_encrypted != "old_encrypted_key"
            assert result.jellyfin_api_key_encrypted != "new-api-key"

    @pytest.mark.asyncio
    async def test_normalizes_trailing_slash(self) -> None:
        """Should remove trailing slash from server URL."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096/",  # Trailing slash
                api_key="test-api-key",
            )
            await session.commit()

            # Trailing slash should be removed
            assert result.jellyfin_server_url == "http://jellyfin:8096"

    @pytest.mark.asyncio
    async def test_encrypts_api_key(self) -> None:
        """Should encrypt the API key before storing."""
        async with TestingAsyncSessionLocal() as session:
            result = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096",
                api_key="my-secret-api-key",
            )
            await session.commit()

            # The stored value should not be the plain text key
            assert result.jellyfin_api_key_encrypted != "my-secret-api-key"
            # It should be a non-empty encrypted string
            assert result.jellyfin_api_key_encrypted is not None
            assert len(result.jellyfin_api_key_encrypted) > 0

    @pytest.mark.asyncio
    async def test_preserves_user_isolation(self) -> None:
        """Should only update settings for the specified user."""
        async with TestingAsyncSessionLocal() as session:
            # Create settings for two users
            settings1 = UserSettings(
                user_id=1,
                jellyfin_server_url="http://user1-jellyfin:8096",
                jellyfin_api_key_encrypted="user1_key",
            )
            settings2 = UserSettings(
                user_id=2,
                jellyfin_server_url="http://user2-jellyfin:8096",
                jellyfin_api_key_encrypted="user2_key",
            )
            session.add_all([settings1, settings2])
            await session.commit()

            # Update only user 1's settings
            await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://user1-new-jellyfin:8096",
                api_key="new-api-key",
            )
            await session.commit()

            # User 2's settings should be unchanged
            user2_settings = await get_user_jellyfin_settings(session, user_id=2)
            assert user2_settings is not None
            assert user2_settings.jellyfin_server_url == "http://user2-jellyfin:8096"


class TestGetDecryptedJellyfinApiKey:
    """Tests for get_decrypted_jellyfin_api_key function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_encrypted_key(self) -> None:
        """Should return None when jellyfin_api_key_encrypted is None."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                jellyfin_server_url="http://jellyfin:8096",
                jellyfin_api_key_encrypted=None,  # No API key set
            )
            session.add(settings)
            await session.commit()

            result = get_decrypted_jellyfin_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_decrypted_key(self) -> None:
        """Should return the decrypted API key when encrypted key exists."""
        async with TestingAsyncSessionLocal() as session:
            # Use save_jellyfin_settings to properly encrypt the key
            settings = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096",
                api_key="my-secret-api-key",
            )
            await session.commit()

            result = get_decrypted_jellyfin_api_key(settings)
            assert result == "my-secret-api-key"

    @pytest.mark.asyncio
    async def test_handles_empty_string_key(self) -> None:
        """Should handle empty string as encrypted key (returns empty or None)."""
        async with TestingAsyncSessionLocal() as session:
            settings = UserSettings(
                user_id=1,
                jellyfin_server_url="http://jellyfin:8096",
                jellyfin_api_key_encrypted="",  # Empty string
            )
            session.add(settings)
            await session.commit()

            # Empty string is falsy, so should return None
            result = get_decrypted_jellyfin_api_key(settings)
            assert result is None

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_special_characters(self) -> None:
        """Should correctly decrypt API keys with special characters."""
        async with TestingAsyncSessionLocal() as session:
            special_key = "abc!@#$%^&*()_+{}|:<>?-=[]\\;',./`~"
            settings = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096",
                api_key=special_key,
            )
            await session.commit()

            result = get_decrypted_jellyfin_api_key(settings)
            assert result == special_key

    @pytest.mark.asyncio
    async def test_decrypts_correctly_with_unicode(self) -> None:
        """Should correctly decrypt API keys with unicode characters."""
        async with TestingAsyncSessionLocal() as session:
            unicode_key = "api-key-with-émojis-🔐-and-汉字"
            settings = await save_jellyfin_settings(
                session,
                user_id=1,
                server_url="http://jellyfin:8096",
                api_key=unicode_key,
            )
            await session.commit()

            result = get_decrypted_jellyfin_api_key(settings)
            assert result == unicode_key
