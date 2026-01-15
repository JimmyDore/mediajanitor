"""Authentication router for user registration and login."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import User, get_db
from app.models.user import RefreshTokenRequest, TokenWithRefresh, UserCreate, UserLogin, UserResponse
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

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Cookie settings for refresh token
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days in seconds


def _is_testing() -> bool:
    """Check if we're running in test environment."""
    import os
    return os.environ.get("TESTING", "").lower() in ("1", "true", "yes")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Register a new user."""
    # Check if email already exists
    existing_user = await get_user_by_email_async(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = await create_user_async(db, user_data.email, user_data.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenWithRefresh)
async def login(
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenWithRefresh:
    """Login and return JWT access token with refresh token in httpOnly cookie."""
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
