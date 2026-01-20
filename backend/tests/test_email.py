"""Unit tests for email service."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.email import send_password_reset_email


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email function."""

    def test_sends_email_with_correct_parameters(self) -> None:
        """Test that email is sent with correct API payload."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 1}}
                mock_client.post.return_value = mock_response

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://mediajanitor.com/reset-password?token=abc123",
                    user_email="user@example.com",
                )

                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "https://api.smtp2go.com/v3/email/send"
                payload = call_args[1]["json"]
                assert payload["api_key"] == "api-test-key"
                assert payload["to"] == ["user@example.com"]
                assert payload["sender"] == "noreply@mediajanitor.com"
                assert payload["subject"] == "Reset Your Media Janitor Password"

    def test_email_contains_reset_url(self) -> None:
        """Test that the email body contains the reset URL."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 1}}
                mock_client.post.return_value = mock_response

                reset_url = "https://mediajanitor.com/reset-password?token=abc123"
                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url=reset_url,
                    user_email="user@example.com",
                )

                payload = mock_client.post.call_args[1]["json"]
                assert reset_url in payload["html_body"]
                assert reset_url in payload["text_body"]

    def test_email_contains_user_email(self) -> None:
        """Test that the email body contains the user's email for reference."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 1}}
                mock_client.post.return_value = mock_response

                user_email = "testuser@example.com"
                send_password_reset_email(
                    to_email=user_email,
                    reset_url="https://example.com/reset",
                    user_email=user_email,
                )

                payload = mock_client.post.call_args[1]["json"]
                assert user_email in payload["html_body"]
                assert user_email in payload["text_body"]

    def test_email_contains_expiration_time(self) -> None:
        """Test that the email mentions the 15 minute expiration time."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 1}}
                mock_client.post.return_value = mock_response

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://example.com/reset",
                    user_email="user@example.com",
                )

                payload = mock_client.post.call_args[1]["json"]
                assert "15 minutes" in payload["html_body"]
                assert "15 minutes" in payload["text_body"]

    def test_raises_http_exception_when_not_configured(self) -> None:
        """Test that HTTPException 500 is raised when SMTP2GO is not configured."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = ""
            mock_settings.smtp_from_email = ""
            mock_get_settings.return_value = mock_settings

            with pytest.raises(HTTPException) as exc_info:
                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://example.com/reset",
                    user_email="user@example.com",
                )

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail

    def test_raises_http_exception_on_api_failure(self) -> None:
        """Test that HTTPException 500 is raised when API returns failure."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 0, "failed": 1}}
                mock_client.post.return_value = mock_response

                with pytest.raises(HTTPException) as exc_info:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                assert exc_info.value.status_code == 500

    def test_raises_http_exception_on_http_error(self) -> None:
        """Test that HTTPException 500 is raised on HTTP error."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_client.post.return_value = mock_response

                with pytest.raises(HTTPException) as exc_info:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                assert exc_info.value.status_code == 500

    def test_raises_http_exception_on_request_error(self) -> None:
        """Test that HTTPException 500 is raised on request error."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.side_effect = httpx.RequestError("Connection failed")

                with pytest.raises(HTTPException) as exc_info:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                assert exc_info.value.status_code == 500

    def test_logs_success_message(self) -> None:
        """Test that a success message is logged when email is sent."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp2go_api_key = "api-test-key"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": {"succeeded": 1}}
                mock_client.post.return_value = mock_response

                with patch("app.services.email.logger") as mock_logger:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                    mock_logger.info.assert_called_once()
                    assert "user@example.com" in mock_logger.info.call_args[0][0]


class TestEmailConfig:
    """Tests for email configuration settings."""

    def test_smtp2go_api_key_defaults_to_empty(self) -> None:
        """Test that smtp2go_api_key defaults to empty string."""
        settings = Settings()
        assert settings.smtp2go_api_key == ""

    def test_smtp_from_email_defaults_to_empty(self) -> None:
        """Test that smtp_from_email defaults to empty string."""
        settings = Settings()
        assert settings.smtp_from_email == ""

    def test_frontend_url_defaults_to_localhost(self) -> None:
        """Test that frontend_url defaults to localhost."""
        settings = Settings()
        assert settings.frontend_url == "http://localhost:5173"

    def test_email_settings_are_optional(self) -> None:
        """Test that email settings being empty is valid - they're optional."""
        settings = Settings()
        assert not settings.smtp2go_api_key
        assert not settings.smtp_from_email
