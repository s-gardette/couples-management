"""
Admin-specific schemas for user management.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.schemas.user import UserResponse


class AdminUserCreateRequest(BaseModel):
    """Schema for admin user creation request."""
    
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, description="User password")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    role: Optional[str] = Field("user", description="User role (admin or user)")
    require_password_change: bool = Field(False, description="Force password change on first login")
    send_invitation_email: bool = Field(True, description="Send invitation email to user")
    send_temporary_password: bool = Field(False, description="Include temporary password in response")


class AdminUserCreateResponse(BaseModel):
    """Schema for admin user creation response."""
    
    message: str = Field(..., description="Success message")
    user_id: str = Field(..., description="Created user ID")
    temporary_password: Optional[str] = Field(None, description="Temporary password if requested")
    invitation_sent: bool = Field(..., description="Whether invitation email was sent")


class AdminUserListResponse(BaseModel):
    """Schema for admin user list response."""
    
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of users skipped")
    limit: int = Field(..., description="Maximum number of users returned")


class AdminUserStatsResponse(BaseModel):
    """Schema for admin user statistics response."""
    
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    inactive_users: int = Field(..., description="Number of inactive users")
    admin_users: int = Field(..., description="Number of admin users")
    regular_users: int = Field(..., description="Number of regular users")
    verified_users: int = Field(..., description="Number of email verified users")
    unverified_users: int = Field(..., description="Number of unverified users")
    users_created_today: int = Field(..., description="Users created today")
    users_created_this_week: int = Field(..., description="Users created this week")
    users_created_this_month: int = Field(..., description="Users created this month")


class AdminUserInviteRequest(BaseModel):
    """Schema for admin user invitation request."""
    
    email: EmailStr = Field(..., description="Email address to invite")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    role: Optional[str] = Field("user", description="User role (admin or user)")
    custom_message: Optional[str] = Field(None, max_length=500, description="Custom invitation message")
    expires_in_days: int = Field(7, ge=1, le=30, description="Invitation expiry in days")


class AdminUserInviteResponse(BaseModel):
    """Schema for admin user invitation response."""
    
    message: str = Field(..., description="Success message")
    invitation_token: str = Field(..., description="Invitation token")
    expires_at: str = Field(..., description="Invitation expiry date")


class AdminBulkUserImportRequest(BaseModel):
    """Schema for admin bulk user import request."""
    
    users_data: List[dict] = Field(..., description="List of user data to import")
    default_role: str = Field("user", description="Default role for imported users")
    send_invitations: bool = Field(True, description="Send invitation emails")
    require_password_change: bool = Field(True, description="Force password change on first login")


class AdminBulkUserImportResponse(BaseModel):
    """Schema for admin bulk user import response."""
    
    message: str = Field(..., description="Import result message")
    imported_count: int = Field(..., description="Number of users successfully imported")
    failed_count: int = Field(..., description="Number of users that failed to import")
    errors: List[str] = Field(..., description="List of import errors")


class AdminUserActivityLog(BaseModel):
    """Schema for admin user activity log."""
    
    id: UUID = Field(..., description="Log entry ID")
    user_id: UUID = Field(..., description="User ID")
    admin_id: UUID = Field(..., description="Admin who performed the action")
    action: str = Field(..., description="Action performed")
    details: Optional[dict] = Field(None, description="Additional action details")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    created_at: datetime = Field(..., description="When the action was performed")


class AdminUserActivityResponse(BaseModel):
    """Schema for admin user activity response."""
    
    activities: List[AdminUserActivityLog] = Field(..., description="List of user activities")
    total: int = Field(..., description="Total number of activities")
    skip: int = Field(..., description="Number of activities skipped")
    limit: int = Field(..., description="Maximum number of activities returned")


class AdminSystemSettingsRequest(BaseModel):
    """Schema for admin system settings update request."""
    
    enable_default_login: Optional[bool] = Field(None, description="Enable default login")
    default_user_id: Optional[str] = Field(None, description="Default user ID")
    require_authentication_for_all: Optional[bool] = Field(None, description="Require auth for all routes")
    admin_contact_email: Optional[EmailStr] = Field(None, description="Admin contact email")
    admin_contact_message: Optional[str] = Field(None, description="Admin contact message")


class AdminSystemSettingsResponse(BaseModel):
    """Schema for admin system settings response."""
    
    message: str = Field(..., description="Update result message")
    settings: dict = Field(..., description="Updated settings")


class AdminDashboardStats(BaseModel):
    """Schema for admin dashboard statistics."""
    
    user_stats: AdminUserStatsResponse = Field(..., description="User statistics")
    system_health: dict = Field(..., description="System health information")
    recent_activities: List[AdminUserActivityLog] = Field(..., description="Recent user activities")
    security_alerts: List[dict] = Field(..., description="Security alerts")


class AdminAccessRestrictedResponse(BaseModel):
    """Schema for access restricted page response."""
    
    message: str = Field(..., description="Access restriction message")
    admin_contact_email: str = Field(..., description="Admin contact email")
    admin_contact_message: str = Field(..., description="Contact message")
    support_info: dict = Field(..., description="Additional support information") 