"""Pydantic schemas for user authentication."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response (excludes password)."""

    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenWithRefresh(BaseModel):
    """Schema for JWT token response with refresh token (login response)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration in seconds


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request (optional - can use cookie)."""

    refresh_token: str | None = None
