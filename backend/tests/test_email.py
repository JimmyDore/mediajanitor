"""Unit tests for email service."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.email import send_password_reset_email


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email function."""

    def test_sends_email_with_correct_parameters(self) -> None:
        """Test that email is sent with correct subject, sender, and recipient."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user@example.com"
            mock_settings.smtp_password = "password123"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://mediajanitor.com/reset-password?token=abc123",
                    user_email="user@example.com",
                )

                mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
                mock_smtp.starttls.assert_called_once()
                mock_smtp.login.assert_called_once_with("user@example.com", "password123")
                mock_smtp.sendmail.assert_called_once()

                # Check sendmail args
                call_args = mock_smtp.sendmail.call_args[0]
                assert call_args[0] == "noreply@mediajanitor.com"  # from
                assert call_args[1] == "user@example.com"  # to

    def test_email_contains_reset_url(self) -> None:
        """Test that the email body contains the reset URL."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                reset_url = "https://mediajanitor.com/reset-password?token=abc123"
                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url=reset_url,
                    user_email="user@example.com",
                )

                # Get the email body
                email_body = mock_smtp.sendmail.call_args[0][2]
                assert reset_url in email_body

    def test_email_contains_user_email(self) -> None:
        """Test that the email body contains the user's email for reference."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                user_email = "testuser@example.com"
                send_password_reset_email(
                    to_email=user_email,
                    reset_url="https://example.com/reset",
                    user_email=user_email,
                )

                email_body = mock_smtp.sendmail.call_args[0][2]
                assert user_email in email_body

    def test_email_contains_expiration_time(self) -> None:
        """Test that the email mentions the 15 minute expiration time."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://example.com/reset",
                    user_email="user@example.com",
                )

                email_body = mock_smtp.sendmail.call_args[0][2]
                assert "15 minutes" in email_body

    def test_email_subject_is_correct(self) -> None:
        """Test that the email has the correct subject line."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://example.com/reset",
                    user_email="user@example.com",
                )

                email_body = mock_smtp.sendmail.call_args[0][2]
                assert "Subject: Reset Your Media Janitor Password" in email_body

    def test_raises_http_exception_when_smtp_not_configured(self) -> None:
        """Test that HTTPException 500 is raised when SMTP is not configured."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = ""
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

    def test_raises_http_exception_on_smtp_authentication_error(self) -> None:
        """Test that HTTPException 500 is raised on SMTP authentication error."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "wrongpassword"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp
                mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(
                    535, b"Authentication failed"
                )

                with pytest.raises(HTTPException) as exc_info:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                assert exc_info.value.status_code == 500
                assert "authentication" in exc_info.value.detail.lower()

    def test_raises_http_exception_on_smtp_error(self) -> None:
        """Test that HTTPException 500 is raised on general SMTP error."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp
                mock_smtp.sendmail.side_effect = smtplib.SMTPException("SMTP error")

                with pytest.raises(HTTPException) as exc_info:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                assert exc_info.value.status_code == 500
                assert "Failed to send email" in exc_info.value.detail

    def test_raises_http_exception_on_unexpected_error(self) -> None:
        """Test that HTTPException 500 is raised on unexpected error."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp_class.return_value.__enter__.side_effect = Exception(
                    "Connection refused"
                )

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
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "user"
            mock_settings.smtp_password = "pass"
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                with patch("app.services.email.logger") as mock_logger:
                    send_password_reset_email(
                        to_email="user@example.com",
                        reset_url="https://example.com/reset",
                        user_email="user@example.com",
                    )

                    mock_logger.info.assert_called_once()
                    assert "user@example.com" in mock_logger.info.call_args[0][0]

    def test_skips_login_when_credentials_empty(self) -> None:
        """Test that SMTP login is skipped when username/password are empty."""
        with patch("app.services.email.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = ""
            mock_settings.smtp_password = ""
            mock_settings.smtp_from_email = "noreply@mediajanitor.com"
            mock_get_settings.return_value = mock_settings

            with patch("app.services.email.smtplib.SMTP") as mock_smtp_class:
                mock_smtp = MagicMock()
                mock_smtp_class.return_value.__enter__.return_value = mock_smtp

                send_password_reset_email(
                    to_email="user@example.com",
                    reset_url="https://example.com/reset",
                    user_email="user@example.com",
                )

                mock_smtp.login.assert_not_called()
                mock_smtp.sendmail.assert_called_once()


class TestEmailConfig:
    """Tests for email configuration settings."""

    def test_smtp_host_defaults_to_empty(self) -> None:
        """Test that smtp_host defaults to empty string."""
        settings = Settings()
        assert settings.smtp_host == ""

    def test_smtp_port_defaults_to_587(self) -> None:
        """Test that smtp_port defaults to 587 (TLS)."""
        settings = Settings()
        assert settings.smtp_port == 587

    def test_smtp_username_defaults_to_empty(self) -> None:
        """Test that smtp_username defaults to empty string."""
        settings = Settings()
        assert settings.smtp_username == ""

    def test_smtp_password_defaults_to_empty(self) -> None:
        """Test that smtp_password defaults to empty string."""
        settings = Settings()
        assert settings.smtp_password == ""

    def test_smtp_from_email_defaults_to_empty(self) -> None:
        """Test that smtp_from_email defaults to empty string."""
        settings = Settings()
        assert settings.smtp_from_email == ""

    def test_frontend_url_defaults_to_localhost(self) -> None:
        """Test that frontend_url defaults to localhost."""
        settings = Settings()
        assert settings.frontend_url == "http://localhost:5173"

    def test_smtp_settings_are_optional(self) -> None:
        """Test that SMTP settings being empty is valid - they're optional."""
        settings = Settings()
        # Empty strings are falsy, so we can check if configured
        assert not settings.smtp_host
        assert not settings.smtp_from_email
