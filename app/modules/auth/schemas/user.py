"""
User schemas for request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    first_name: str | None = Field(None, max_length=100, description="First name")
    last_name: str | None = Field(None, max_length=100, description="Last name")


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, max_length=128, description="User password")


class UserUpdate(BaseModel):
    """Schema for user profile updates."""

    email: EmailStr | None = Field(None, description="New email address")
    username: str | None = Field(None, min_length=3, max_length=50, description="New username")
    first_name: str | None = Field(None, max_length=100, description="New first name")
    last_name: str | None = Field(None, max_length=100, description="New last name")


class UserResponse(UserBase):
    """Schema for user response data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="User ID")
    avatar_url: str | None = Field(None, description="Avatar URL")
    email_verified: bool = Field(..., description="Email verification status")
    is_active: bool = Field(..., description="Account active status")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    @property
    def display_name(self) -> str:
        """Get user's display name."""
        return self.full_name if (self.first_name or self.last_name) else self.username


class UserProfile(UserResponse):
    """Extended user profile schema with additional details."""

    pass  # Can be extended with additional profile fields in the future


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of users per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class PasswordChange(BaseModel):
    """Schema for password change requests."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class AvatarUpdate(BaseModel):
    """Schema for avatar update requests."""

    avatar_url: str = Field(..., description="New avatar URL")


class UserStats(BaseModel):
    """Schema for user statistics."""

    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    verified_users: int = Field(..., description="Number of verified users")
    inactive_users: int = Field(..., description="Number of inactive users")
    unverified_users: int = Field(..., description="Number of unverified users")


class UserSearch(BaseModel):
    """Schema for user search parameters."""

    query: str | None = Field(None, description="Search query")
    email_verified: bool | None = Field(None, description="Filter by email verification")
    is_active: bool | None = Field(None, description="Filter by active status")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class EmailAvailability(BaseModel):
    """Schema for email availability check."""

    email: EmailStr = Field(..., description="Email to check")


class UsernameAvailability(BaseModel):
    """Schema for username availability check."""

    username: str = Field(..., min_length=3, max_length=50, description="Username to check")


class AvailabilityResponse(BaseModel):
    """Schema for availability check response."""

    available: bool = Field(..., description="Whether the value is available")
    message: str = Field(..., description="Descriptive message")
