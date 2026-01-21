"""Authentication service for password hashing and user operations."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import RefreshToken, User, get_db

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_user_by_email_sync(db: Session, email: str) -> User | None:
    """Get a user by email address (sync version)."""
    result = db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_email_async(db: AsyncSession, email: str) -> User | None:
    """Get a user by email address (async version)."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def create_user_sync(db: Session, email: str, password: str) -> User:
    """Create a new user with hashed password (sync version)."""
    hashed_password = hash_password(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


async def create_user_async(db: AsyncSession, email: str, password: str) -> User:
    """Create a new user with hashed password (async version)."""
    hashed_password = hash_password(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def create_user(db: Session | AsyncSession, email: str, password: str) -> User:
    """Create a new user with hashed password (sync version for compatibility)."""
    hashed_password = hash_password(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_token(db: AsyncSession, user_id: int) -> str:
    """Create a new refresh token for a user and store its hash in the database."""
    settings = get_settings()
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    await db.flush()

    return token


async def validate_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    """Validate a refresh token and return the database record if valid."""
    token_hash = hash_refresh_token(token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def invalidate_refresh_token(db: AsyncSession, token_hash: str) -> None:
    """Invalidate (delete) a refresh token by its hash."""
    await db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))


async def invalidate_user_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    """Invalidate all refresh tokens for a user (logout from all devices)."""
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))


async def rotate_refresh_token(db: AsyncSession, old_token: str) -> tuple[str, int] | None:
    """
    Rotate a refresh token: validate, invalidate the old one, and create a new one.

    Returns a tuple of (new_token, user_id) if successful, None if token is invalid.
    """
    token_record = await validate_refresh_token(db, old_token)
    if not token_record:
        return None

    user_id = token_record.user_id

    # Invalidate the old token
    await invalidate_refresh_token(db, token_record.token_hash)

    # Create a new token
    new_token = await create_refresh_token(db, user_id)

    return new_token, user_id


async def get_user_by_id_async(db: AsyncSession, user_id: int) -> User | None:
    """Get a user by ID (async version)."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user_async(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user by email and password (async version)."""
    user = await get_user_by_email_async(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Raises HTTPException 401 if:
    - No token provided
    - Token is invalid or expired
    - User doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email_async(db, email)
    if user is None:
        raise credentials_exception

    return user
