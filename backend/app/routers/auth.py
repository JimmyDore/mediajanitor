"""Authentication router for user registration and login."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import PasswordResetToken, User, get_db
from app.models.user import (
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenWithRefresh,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth import (
    authenticate_user_async,
    create_access_token,
    create_refresh_token,
    create_user_async,
    get_current_user,
    get_user_by_email_async,
    get_user_by_id_async,
    hash_refresh_token,
    invalidate_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
)
from app.services.email import send_password_reset_email
from app.services.rate_limit import login_rate_limiter, password_reset_rate_limiter, register_rate_limiter
from app.services.slack import send_slack_message

if TYPE_CHECKING:
    from app.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie settings for refresh token
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


def _is_testing() -> bool:
    """Check if we're running in test environment."""
    import os
    return os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


def _get_client_ip(request: Request) -> str:
    """
    Get the client IP address from the request.

    Handles X-Forwarded-For header for requests behind a proxy.
    """
    # Check for forwarded IP (from reverse proxy like nginx)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, first is the client
        return forwarded_for.split(",")[0].strip()
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request, limiter: RateLimiter) -> None:
    """
    Check rate limit and raise HTTPException if exceeded.

    Args:
        request: FastAPI request object
        limiter: The rate limiter instance to use

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    client_ip = _get_client_ip(request)
    is_limited, retry_after = limiter.is_rate_limited(client_ip)

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


async def get_total_user_count(db: AsyncSession) -> int:
    """Get the total number of registered users."""
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar() or 0


async def send_signup_notification(email: str, user_id: int, total_users: int) -> None:
    """
    Send a Slack notification about a new user signup.

    This is a fire-and-forget function - it logs errors but never raises.
    """
    settings = get_settings()
    webhook_url = settings.slack_webhook_new_users

    if not webhook_url:
        # Webhook not configured, silently skip
        return

    signup_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Create message in Slack Block Kit format
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎉 New User Signup",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Email:*\n{email}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*User ID:*\n{user_id}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Signup Time:*\n{signup_time}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Users:*\n{total_users}"
                    }
                ]
            }
        ],
        "text": f"New user signup: {email} (Total users: {total_users})"  # Fallback text
    }

    try:
        await send_slack_message(webhook_url, message)
    except Exception as e:
        # Log but don't raise - this is fire-and-forget
        logger.warning(f"Failed to send signup notification for {email}: {e}")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user."""
    # Check rate limit
    _check_rate_limit(request, register_rate_limiter)

    # Check if email already exists
    existing_user = await get_user_by_email_async(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = await create_user_async(db, user_data.email, user_data.password)

    # Get total user count for notification (after this user is created)
    total_users = await get_total_user_count(db)

    # Send Slack notification (fire-and-forget using background task)
    try:
        background_tasks.add_task(
            send_signup_notification,
            email=user.email,
            user_id=user.id,
            total_users=total_users,
        )
    except Exception:
        # Don't let notification failures affect registration
        pass

    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenWithRefresh)
async def login(
    request: Request,
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenWithRefresh:
    """Login and return JWT access token with refresh token in httpOnly cookie."""
    # Check rate limit
    _check_rate_limit(request, login_rate_limiter)

    user = await authenticate_user_async(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Create refresh token and set as httpOnly cookie
    refresh_token = await create_refresh_token(db, user.id)
    testing = _is_testing()
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        secure=not testing,  # Only sent over HTTPS (disabled for tests)
        samesite="lax",  # CSRF protection
        path="/" if testing else "/api/auth",  # Root path for tests, restricted in prod
    )

    return TokenWithRefresh(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,  # Convert to seconds
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=TokenWithRefresh)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
    body: RefreshTokenRequest | None = None,
) -> TokenWithRefresh:
    """
    Refresh access token using refresh token.

    The refresh token can be provided via:
    1. httpOnly cookie (preferred, automatic)
    2. Request body (for clients that can't use cookies)

    Returns new access token and rotates the refresh token.
    """
    # Try cookie first, then body
    token = refresh_token or (body.refresh_token if body else None)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rotate the refresh token (validates, invalidates old, creates new)
    result = await rotate_refresh_token(db, token)
    if not result:
        # Clear the invalid cookie
        testing = _is_testing()
        response.delete_cookie(
            key=REFRESH_TOKEN_COOKIE_NAME,
            path="/" if testing else "/api/auth",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_refresh_token, user_id = result

    # Get user email for access token
    user = await get_user_by_id_async(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Set new refresh token as cookie
    testing = _is_testing()
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        secure=not testing,
        samesite="lax",
        path="/" if testing else "/api/auth",
    )

    return TokenWithRefresh(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None, alias=REFRESH_TOKEN_COOKIE_NAME),
) -> None:
    """
    Logout by invalidating the refresh token and clearing the cookie.

    Does not require authentication - the refresh token is enough to identify
    the session to invalidate.
    """
    if refresh_token:
        # Invalidate the refresh token in the database
        token_record = await validate_refresh_token(db, refresh_token)
        if token_record:
            await invalidate_refresh_token(db, token_record.token_hash)

    # Always clear the cookie, even if the token was invalid
    testing = _is_testing()
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/" if testing else "/api/auth",
    )


def _check_password_reset_rate_limit(email: str) -> None:
    """
    Check password reset rate limit by email address.

    Args:
        email: Email address to check

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    is_limited, retry_after = password_reset_rate_limiter.is_rate_limited(email.lower())

    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset requests. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


@router.post("/request-password-reset", response_model=PasswordResetResponse)
async def request_password_reset(
    request_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    """
    Request a password reset email.

    Always returns 200 OK to prevent email enumeration attacks.
    If the email exists, sends a reset link. If not, silently succeeds.
    """
    import secrets

    import bcrypt

    email = request_data.email.lower()

    # Check rate limit by email (not IP)
    _check_password_reset_rate_limit(email)

    # Look up user
    user = await get_user_by_email_async(db, email)

    if user:
        # Delete any existing unused tokens for this user
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used == False,  # noqa: E712
            )
        )
        existing_tokens = result.scalars().all()
        for token in existing_tokens:
            await db.delete(token)

        # Generate secure random token (32 bytes, URL-safe base64)
        raw_token = secrets.token_urlsafe(32)

        # Hash the token for storage
        token_hash = bcrypt.hashpw(raw_token.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Create expiration (15 minutes from now)
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Create token record
        password_reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            used=False,
        )
        db.add(password_reset_token)
        await db.commit()

        # Build reset URL
        settings = get_settings()
        reset_url = f"{settings.frontend_url}/reset-password?token={raw_token}"

        # Send email
        try:
            send_password_reset_email(
                to_email=email,
                reset_url=reset_url,
                user_email=email,
            )
        except HTTPException:
            # Email service error - log but don't reveal to user
            logger.error(f"Failed to send password reset email to {email}")
        except Exception as e:
            logger.error(f"Unexpected error sending password reset email: {e}")

    # Always return success to prevent email enumeration
    return PasswordResetResponse()


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> ResetPasswordResponse:
    """
    Reset password using a valid reset token.

    Returns 200 OK on success, 400 if token is invalid/expired/used.
    """
    import bcrypt

    # Find all non-used, non-expired tokens
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
    )
    tokens = result.scalars().all()

    # Check incoming token against each stored hash
    matching_token = None
    for token_record in tokens:
        if bcrypt.checkpw(
            request_data.token.encode("utf-8"),
            token_record.token_hash.encode("utf-8"),
        ):
            matching_token = token_record
            break

    if not matching_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Get the user
    user_result = await db.execute(
        select(User).where(User.id == matching_token.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update user's password
    new_hashed_password = bcrypt.hashpw(
        request_data.new_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")
    user.hashed_password = new_hashed_password

    # Mark token as used
    matching_token.used = True

    await db.commit()

    logger.info(f"Password reset successful for user {user.email}")

    return ResetPasswordResponse()
