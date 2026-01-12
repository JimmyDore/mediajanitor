"""Authentication router for user registration and login."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models.user import UserCreate, UserResponse
from app.services.auth import create_user, get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Any = Depends(get_db)) -> UserResponse:
    """Register a new user."""
    # Check if email already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    user = create_user(db, user_data.email, user_data.password)
    return UserResponse.model_validate(user)
