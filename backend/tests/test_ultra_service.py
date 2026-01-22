"""Tests for Ultra.cc seedbox service fetch_ultra_stats function (US-48.4)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ultra import fetch_ultra_stats


class TestFetchUltraStats:
    """Tests for fetch_ultra_stats function."""

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_success(self, mock_client_class: MagicMock) -> None:
        """Test successful fetch of Ultra.cc stats."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "service_stats_info": {
                "free_storage_gb": 234.5,
                "traffic_available_percentage": 85.2,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Call the function
        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        # Verify the result
        assert result is not None
        assert result["free_storage_gb"] == 234.5
        assert result["traffic_available_percentage"] == 85.2

        # Verify the API was called correctly
        mock_client.get.assert_called_once_with(
            "https://ultra.cc/api/total-stats",
            headers={"Authorization": "Bearer test-api-key"},
        )

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_strips_trailing_slash(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that URL is normalized by stripping trailing slash."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "service_stats_info": {
                "free_storage_gb": 100.0,
                "traffic_available_percentage": 50.0,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        await fetch_ultra_stats("https://ultra.cc/api/", "test-api-key")

        # Should strip trailing slash
        mock_client.get.assert_called_once_with(
            "https://ultra.cc/api/total-stats",
            headers={"Authorization": "Bearer test-api-key"},
        )

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_http_error(self, mock_client_class: MagicMock) -> None:
        """Test that HTTP error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "invalid-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_request_error(self, mock_client_class: MagicMock) -> None:
        """Test that request error (network issue) returns None."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_timeout_error(self, mock_client_class: MagicMock) -> None:
        """Test that timeout error returns None."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_missing_fields(self, mock_client_class: MagicMock) -> None:
        """Test that missing fields in response returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "service_stats_info": {
                "free_storage_gb": 100.0,
                # Missing traffic_available_percentage
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_missing_service_stats_info(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that missing service_stats_info returns None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "other_field": "value",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_invalid_json(self, mock_client_class: MagicMock) -> None:
        """Test that invalid JSON response returns None."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.ultra.httpx.AsyncClient")
    async def test_fetch_ultra_stats_converts_values_to_float(
        self, mock_client_class: MagicMock
    ) -> None:
        """Test that string or int values are converted to float."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "service_stats_info": {
                "free_storage_gb": "150",  # String value
                "traffic_available_percentage": 75,  # Int value
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await fetch_ultra_stats("https://ultra.cc/api", "test-api-key")

        assert result is not None
        assert result["free_storage_gb"] == 150.0
        assert isinstance(result["free_storage_gb"], float)
        assert result["traffic_available_percentage"] == 75.0
        assert isinstance(result["traffic_available_percentage"], float)
