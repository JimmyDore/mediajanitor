"""Pydantic schemas for user authentication."""

from pydantic import BaseModel, EmailStr, Field, field_validator


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


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetResponse(BaseModel):
    """Schema for password reset response.

    Always returns success to prevent email enumeration.
    """

    message: str = "If that email exists, a reset link has been sent. Check your inbox."


def validate_password_strength(password: str) -> str:
    """
    Validate password meets requirements: 8+ chars, uppercase, lowercase, number.

    Raises ValueError if requirements not met.
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    return password


class ResetPasswordRequest(BaseModel):
    """Schema for reset password with token."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class ResetPasswordResponse(BaseModel):
    """Schema for successful password reset response."""

    message: str = "Password has been reset successfully."


class ChangePasswordRequest(BaseModel):
    """Schema for change password request (for logged-in users)."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)


class ChangePasswordResponse(BaseModel):
    """Schema for successful password change response."""

    message: str = "Password has been changed successfully."
