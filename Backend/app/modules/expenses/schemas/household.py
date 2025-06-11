"""
Pydantic schemas for household-related API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.modules.expenses.models.household import UserHouseholdRole


class HouseholdBase(BaseModel):
    """Base schema for household data."""
    name: str = Field(..., min_length=1, max_length=100, description="Household name")
    description: Optional[str] = Field(None, max_length=500, description="Household description")


class HouseholdCreate(HouseholdBase):
    """Schema for creating a new household."""
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Household settings")


class HouseholdUpdate(BaseModel):
    """Schema for updating a household."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Household name")
    description: Optional[str] = Field(None, max_length=500, description="Household description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Household settings")


class UserHouseholdResponse(BaseModel):
    """Schema for user household membership information."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    household_id: UUID
    role: UserHouseholdRole
    nickname: Optional[str] = None
    joined_at: datetime
    is_active: bool


class HouseholdResponse(HouseholdBase):
    """Schema for household response data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    invite_code: str
    created_by: UUID
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    # Optional member information
    members: Optional[List[UserHouseholdResponse]] = None
    member_count: Optional[int] = None
    admin_count: Optional[int] = None


class HouseholdListResponse(BaseModel):
    """Schema for household list response."""
    households: List[HouseholdResponse]
    total: int
    page: int
    per_page: int


class JoinHouseholdRequest(BaseModel):
    """Schema for joining a household by invite code."""
    invite_code: str = Field(..., min_length=6, max_length=10, description="Household invite code")
    nickname: Optional[str] = Field(None, max_length=50, description="Display name in household")


class UpdateMemberRoleRequest(BaseModel):
    """Schema for updating a member's role."""
    role: UserHouseholdRole = Field(..., description="New role for the member")


class HouseholdSettingsUpdate(BaseModel):
    """Schema for updating household settings."""
    settings: Dict[str, Any] = Field(..., description="Updated household settings")


class InviteCodeResponse(BaseModel):
    """Schema for invite code response."""
    invite_code: str
    household_id: UUID
    household_name: str


class HouseholdStatsResponse(BaseModel):
    """Schema for household statistics."""
    member_count: int
    admin_count: int
    created_at: datetime
    settings: Dict[str, Any]
    invite_code: str
    total_expenses: Optional[int] = None
    total_amount: Optional[float] = None
    categories_count: Optional[int] = None


class HouseholdMemberResponse(BaseModel):
    """Schema for household member information."""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    username: str
    email: str
    role: UserHouseholdRole
    nickname: Optional[str] = None
    joined_at: datetime
    is_active: bool


class HouseholdMembersResponse(BaseModel):
    """Schema for household members list."""
    members: List[HouseholdMemberResponse]
    total: int
    household_id: UUID
    household_name: str 