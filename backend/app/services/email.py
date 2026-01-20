"""Email service for sending transactional emails via SMTP2GO HTTP API."""

import logging

import httpx
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)

SMTP2GO_API_URL = "https://api.smtp2go.com/v3/email/send"


def send_password_reset_email(to_email: str, reset_url: str, user_email: str) -> None:
    """
    Send a password reset email to the user.

    Args:
        to_email: The recipient's email address.
        reset_url: The full URL for resetting the password (includes token).
        user_email: The user's email for reference in the email body.

    Raises:
        HTTPException: If email sending fails (status 500).
    """
    settings = get_settings()

    if not settings.smtp2go_api_key or not settings.smtp_from_email:
        logger.error("SMTP2GO not configured. Cannot send password reset email.")
        raise HTTPException(
            status_code=500, detail="Email service is not configured"
        )

    subject = "Reset Your Media Janitor Password"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
        <h1 style="color: #1a1a1a; margin-top: 0; margin-bottom: 20px;">Password Reset Request</h1>
        <p>You requested a password reset for your Media Janitor account associated with:</p>
        <p style="background-color: #e9ecef; padding: 10px; border-radius: 4px; font-family: monospace;">{user_email}</p>
        <p>Click the button below to reset your password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">Reset Password</a>
        </p>
        <p style="color: #666; font-size: 14px;">This link will expire in <strong>15 minutes</strong>.</p>
        <p style="color: #666; font-size: 14px;">If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
    <p style="color: #999; font-size: 12px; text-align: center;">
        This email was sent by Media Janitor. If you have any questions, please contact support.
    </p>
</body>
</html>
"""

    text_body = f"""Password Reset Request

You requested a password reset for your Media Janitor account associated with:
{user_email}

Click the link below to reset your password:
{reset_url}

This link will expire in 15 minutes.

If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged.

---
This email was sent by Media Janitor.
"""

    payload = {
        "api_key": settings.smtp2go_api_key,
        "to": [to_email],
        "sender": settings.smtp_from_email,
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(SMTP2GO_API_URL, json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("data", {}).get("succeeded", 0) > 0:
                logger.info(f"Password reset email sent to {to_email}")
                return
            else:
                logger.error(f"SMTP2GO API returned failure: {data}")
                raise HTTPException(
                    status_code=500, detail="Failed to send email"
                )
        else:
            logger.error(f"SMTP2GO API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=500, detail="Failed to send email"
            )

    except httpx.RequestError as e:
        logger.error(f"HTTP error sending password reset email: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send email"
        )
    except Exception as e:
        logger.error(f"Unexpected error sending password reset email: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send email"
        )
