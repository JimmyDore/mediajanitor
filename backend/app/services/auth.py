"""Authentication service for password hashing and user operations."""

from typing import Union

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.database import User


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
