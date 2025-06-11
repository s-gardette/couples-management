"""
Authentication schemas for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for user login requests."""

    email_or_username: str = Field(..., description="Email address or username")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: dict = Field(..., description="User information")


class RegisterRequest(BaseModel):
    """Schema for user registration requests."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    first_name: str | None = Field(None, max_length=100, description="First name")
    last_name: str | None = Field(None, max_length=100, description="Last name")


class RegisterResponse(BaseModel):
    """Schema for registration response."""

    message: str = Field(..., description="Registration status message")
    user_id: str | None = Field(None, description="Created user ID")
    email_verification_required: bool = Field(True, description="Whether email verification is required")


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh requests."""

    refresh_token: str = Field(..., description="Valid refresh token")


class TokenRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class LogoutRequest(BaseModel):
    """Schema for logout requests."""

    session_token: str | None = Field(None, description="Optional session token to invalidate")


class PasswordResetRequest(BaseModel):
    """Schema for password reset requests."""

    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetResponse(BaseModel):
    """Schema for password reset response."""

    message: str = Field(..., description="Password reset status message")
    masked_email: str | None = Field(None, description="Masked email address")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class EmailVerificationRequest(BaseModel):
    """Schema for email verification requests."""

    token: str = Field(..., description="Email verification token")


class EmailVerificationResend(BaseModel):
    """Schema for resending email verification."""

    email: EmailStr = Field(..., description="Email address to resend verification")


class AuthResponse(BaseModel):
    """Generic authentication response schema."""

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    data: dict | None = Field(None, description="Additional response data")


class TokenInfo(BaseModel):
    """Schema for token information."""

    token_type: str = Field(..., description="Type of token (access/refresh)")
    expires_at: datetime = Field(..., description="Token expiration time")
    issued_at: datetime = Field(..., description="Token issue time")
    user_id: str = Field(..., description="User ID associated with token")


class SessionInfo(BaseModel):
    """Schema for session information."""

    session_id: str = Field(..., description="Session ID")
    user_agent: str | None = Field(None, description="User agent string")
    ip_address: str | None = Field(None, description="IP address")
    created_at: datetime = Field(..., description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    is_active: bool = Field(..., description="Session active status")


class PasswordStrengthCheck(BaseModel):
    """Schema for password strength checking."""

    password: str = Field(..., description="Password to check")


class PasswordStrengthResponse(BaseModel):
    """Schema for password strength response."""

    is_valid: bool = Field(..., description="Whether password meets requirements")
    score: int = Field(..., description="Password strength score (0-100)")
    level: str = Field(..., description="Password strength level")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


class TwoFactorSetup(BaseModel):
    """Schema for two-factor authentication setup (future feature)."""

    method: str = Field(..., description="2FA method (totp, sms, email)")
    phone_number: str | None = Field(None, description="Phone number for SMS 2FA")


class TwoFactorVerify(BaseModel):
    """Schema for two-factor authentication verification (future feature)."""

    code: str = Field(..., description="2FA verification code")
    method: str = Field(..., description="2FA method used")


class DeviceInfo(BaseModel):
    """Schema for device information."""

    device_name: str | None = Field(None, description="Device name")
    device_type: str | None = Field(None, description="Device type")
    user_agent: str | None = Field(None, description="User agent string")
    ip_address: str | None = Field(None, description="IP address")


class SecurityEvent(BaseModel):
    """Schema for security events."""

    event_type: str = Field(..., description="Type of security event")
    description: str = Field(..., description="Event description")
    ip_address: str | None = Field(None, description="IP address")
    user_agent: str | None = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Event timestamp")
    severity: str = Field(..., description="Event severity level")
