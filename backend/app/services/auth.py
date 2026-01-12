"""Authentication service for password hashing and user operations."""

from datetime import datetime, timedelta, timezone
from typing import Union

import bcrypt
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import User

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_user_by_email_sync(db: Session, email: str) -> User | None:
    """Get a user by email address (sync version)."""
    result = db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_email_async(db: AsyncSession, email: str) -> User | None:
    """Get a user by email address (async version)."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def get_user_by_email(db: Union[Session, AsyncSession], email: str) -> User | None:
    """Get a user by email address (sync version for compatibility)."""
    result = db.execute(select(User).where(User.email == email))
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


def create_user(db: Union[Session, AsyncSession], email: str, password: str) -> User:
    """Create a new user with hashed password (sync version for compatibility)."""
    hashed_password = hash_password(password)
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user_async(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """Authenticate a user by email and password (async version)."""
    user = await get_user_by_email_async(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
