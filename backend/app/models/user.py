"""Pydantic schemas for user authentication."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""

    id: int
    email: EmailStr

    model_config = {"from_attributes": True}
