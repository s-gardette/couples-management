"""
Household service for managing households and their members.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.services.base_service import BaseService
from app.core.utils.security import generate_invite_code
from app.modules.expenses.models.household import Household, UserHouseholdRole
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.category import Category

logger = logging.getLogger(__name__)


class HouseholdService(BaseService[Household, dict, dict]):
    """Service for household management operations."""

    def __init__(self, db: Session):
        super().__init__(Household)
        self.db = db

    async def create_household(
        self,
        name: str,
        description: Optional[str],
        created_by: UUID,
        settings: Optional[dict] = None
    ) -> Tuple[bool, str, Optional[Household]]:
        """
        Create a new household and add the creator as an admin.

        Args:
            name: Household name
            description: Optional description
            created_by: UUID of the user creating the household
            settings: Optional household settings

        Returns:
            Tuple of (success, message, household_object)
        """
        try:
            # Generate unique invite code
            invite_code = self._generate_unique_invite_code()

            # Create household
            household = Household(
                name=name.strip(),
                description=description.strip() if description else None,
                invite_code=invite_code,
                created_by=created_by,
                settings=settings or {},
                is_active=True
            )

            self.db.add(household)
            self.db.flush()  # Get the household ID

            # Add creator as admin member
            user_household = UserHousehold(
                user_id=created_by,
                household_id=household.id,
                role=UserHouseholdRole.ADMIN,
                is_active=True
            )
            self.db.add(user_household)

            # Create default categories for the household
            await self._create_default_categories(household.id)

            self.db.commit()
            logger.info(f"Created household {household.id} by user {created_by}")

            return True, "Household created successfully", household

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating household: {e}")
            return False, "Failed to create household due to data conflict", None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating household: {e}")
            return False, f"Failed to create household: {str(e)}", None

    async def get_user_households(
        self,
        user_id: UUID,
        include_inactive: bool = False
    ) -> List[Household]:
        """
        Get all households for a user.

        Args:
            user_id: User ID
            include_inactive: Whether to include inactive households

        Returns:
            List of households
        """
        try:
            query = (
                self.db.query(Household)
                .join(UserHousehold)
                .filter(UserHousehold.user_id == user_id)
            )

            if not include_inactive:
                query = query.filter(
                    Household.is_active == True,
                    UserHousehold.is_active == True
                )

            return query.all()

        except SQLAlchemyError as e:
            logger.error(f"Error getting households for user {user_id}: {e}")
            return []

    async def get_household_with_members(self, household_id: UUID) -> Optional[Household]:
        """
        Get household with all member information loaded.

        Args:
            household_id: Household ID

        Returns:
            Household with members or None
        """
        try:
            return (
                self.db.query(Household)
                .filter(Household.id == household_id, Household.is_active == True)
                .first()
            )
        except SQLAlchemyError as e:
            logger.error(f"Error getting household {household_id}: {e}")
            return None

    async def join_household_by_invite(
        self,
        user_id: UUID,
        invite_code: str,
        nickname: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Household]]:
        """
        Join a household using an invite code.

        Args:
            user_id: User ID
            invite_code: Household invite code
            nickname: Optional nickname for the household

        Returns:
            Tuple of (success, message, household_object)
        """
        try:
            # Find household by invite code
            household = (
                self.db.query(Household)
                .filter(
                    Household.invite_code == invite_code.upper(),
                    Household.is_active == True
                )
                .first()
            )

            if not household:
                return False, "Invalid invite code", None

            # Check if user is already a member
            existing_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household.id
                )
                .first()
            )

            if existing_membership:
                if existing_membership.is_active:
                    return False, "You are already a member of this household", None
                else:
                    # Reactivate membership
                    existing_membership.rejoin_household()
                    if nickname:
                        existing_membership.set_nickname(nickname)
                    self.db.commit()
                    return True, "Rejoined household successfully", household

            # Create new membership
            user_household = UserHousehold(
                user_id=user_id,
                household_id=household.id,
                role=UserHouseholdRole.MEMBER,
                nickname=nickname,
                is_active=True
            )
            self.db.add(user_household)
            self.db.commit()

            logger.info(f"User {user_id} joined household {household.id}")
            return True, "Joined household successfully", household

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error joining household: {e}")
            return False, f"Failed to join household: {str(e)}", None

    async def leave_household(
        self,
        user_id: UUID,
        household_id: UUID
    ) -> Tuple[bool, str]:
        """
        Leave a household.

        Args:
            user_id: User ID
            household_id: Household ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household"

            # Check if user is the only admin
            admin_count = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.household_id == household_id,
                    UserHousehold.role == UserHouseholdRole.ADMIN,
                    UserHousehold.is_active == True
                )
                .count()
            )

            if membership.role == UserHouseholdRole.ADMIN and admin_count == 1:
                return False, "Cannot leave household as the only admin. Transfer admin role first."

            # Leave household
            membership.leave_household()
            self.db.commit()

            logger.info(f"User {user_id} left household {household_id}")
            return True, "Left household successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error leaving household: {e}")
            return False, f"Failed to leave household: {str(e)}"

    async def update_member_role(
        self,
        admin_user_id: UUID,
        household_id: UUID,
        target_user_id: UUID,
        new_role: UserHouseholdRole
    ) -> Tuple[bool, str]:
        """
        Update a member's role in the household.

        Args:
            admin_user_id: ID of admin performing the action
            household_id: Household ID
            target_user_id: ID of user whose role is being changed
            new_role: New role to assign

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify admin permissions
            admin_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == admin_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.role == UserHouseholdRole.ADMIN,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not admin_membership:
                return False, "You don't have permission to change member roles"

            # Find target membership
            target_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == target_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not target_membership:
                return False, "Target user is not a member of this household"

            # Prevent demoting the last admin
            if (target_membership.role == UserHouseholdRole.ADMIN and 
                new_role == UserHouseholdRole.MEMBER):
                admin_count = (
                    self.db.query(UserHousehold)
                    .filter(
                        UserHousehold.household_id == household_id,
                        UserHousehold.role == UserHouseholdRole.ADMIN,
                        UserHousehold.is_active == True
                    )
                    .count()
                )
                if admin_count == 1:
                    return False, "Cannot demote the last admin"

            # Update role
            target_membership.role = new_role
            self.db.commit()

            logger.info(f"Updated role for user {target_user_id} in household {household_id}")
            return True, "Member role updated successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating member role: {e}")
            return False, f"Failed to update member role: {str(e)}"

    async def remove_member(
        self,
        admin_user_id: UUID,
        household_id: UUID,
        target_user_id: UUID
    ) -> Tuple[bool, str]:
        """
        Remove a member from the household.

        Args:
            admin_user_id: ID of admin performing the action
            household_id: Household ID
            target_user_id: ID of user to remove

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify admin permissions
            admin_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == admin_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.role == UserHouseholdRole.ADMIN,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not admin_membership:
                return False, "You don't have permission to remove members"

            # Cannot remove yourself
            if admin_user_id == target_user_id:
                return False, "Cannot remove yourself. Use leave household instead."

            # Find target membership
            target_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == target_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not target_membership:
                return False, "Target user is not a member of this household"

            # Remove member
            target_membership.leave_household()
            self.db.commit()

            logger.info(f"Removed user {target_user_id} from household {household_id}")
            return True, "Member removed successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing member: {e}")
            return False, f"Failed to remove member: {str(e)}"

    async def update_household_settings(
        self,
        user_id: UUID,
        household_id: UUID,
        settings: dict
    ) -> Tuple[bool, str, Optional[Household]]:
        """
        Update household settings.

        Args:
            user_id: User ID (must be admin)
            household_id: Household ID
            settings: New settings

        Returns:
            Tuple of (success, message, household_object)
        """
        try:
            # Verify admin permissions
            admin_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.role == UserHouseholdRole.ADMIN,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not admin_membership:
                return False, "You don't have permission to update household settings", None

            # Get household
            household = self.get(self.db, household_id)
            if not household:
                return False, "Household not found", None

            # Update settings
            current_settings = household.settings or {}
            current_settings.update(settings)
            household.settings = current_settings

            self.db.commit()
            logger.info(f"Updated settings for household {household_id}")

            return True, "Household settings updated successfully", household

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating household settings: {e}")
            return False, f"Failed to update settings: {str(e)}", None

    async def regenerate_invite_code(
        self,
        user_id: UUID,
        household_id: UUID
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Regenerate the invite code for a household.

        Args:
            user_id: User ID (must be admin)
            household_id: Household ID

        Returns:
            Tuple of (success, message, new_invite_code)
        """
        try:
            # Verify admin permissions
            admin_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.role == UserHouseholdRole.ADMIN,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not admin_membership:
                return False, "You don't have permission to regenerate invite code", None

            # Get household
            household = self.get(self.db, household_id)
            if not household:
                return False, "Household not found", None

            # Generate new invite code
            new_invite_code = self._generate_unique_invite_code()
            household.invite_code = new_invite_code

            self.db.commit()
            logger.info(f"Regenerated invite code for household {household_id}")

            return True, "Invite code regenerated successfully", new_invite_code

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error regenerating invite code: {e}")
            return False, f"Failed to regenerate invite code: {str(e)}", None

    def _generate_unique_invite_code(self) -> str:
        """Generate a unique invite code."""
        max_attempts = 10
        for _ in range(max_attempts):
            code = generate_invite_code()
            existing = (
                self.db.query(Household)
                .filter(Household.invite_code == code)
                .first()
            )
            if not existing:
                return code
        
        # Fallback with timestamp if all attempts fail
        return generate_invite_code() + str(int(datetime.now().timestamp()))[-4:]

    async def _create_default_categories(self, household_id: UUID) -> None:
        """Create default categories for a new household."""
        default_categories = Category.get_default_categories()
        
        for cat_data in default_categories:
            category = Category.create_household_category(
                name=cat_data["name"],
                household_id=str(household_id),
                icon=cat_data["icon"],
                color=cat_data["color"],
                is_default=cat_data["is_default"]
            )
            self.db.add(category)

    async def get_household_stats(self, household_id: UUID) -> dict:
        """
        Get statistics for a household.

        Args:
            household_id: Household ID

        Returns:
            Dictionary with household statistics
        """
        try:
            household = self.get(self.db, household_id)
            if not household:
                return {}

            return {
                "member_count": household.member_count,
                "admin_count": household.admin_count,
                "created_at": household.created_at,
                "settings": household.settings or {},
                "invite_code": household.invite_code
            }

        except Exception as e:
            logger.error(f"Error getting household stats: {e}")
            return {}

    async def check_user_permission(
        self,
        user_id: UUID,
        household_id: UUID,
        required_role: Optional[UserHouseholdRole] = None
    ) -> bool:
        """
        Check if user has permission to access household.

        Args:
            user_id: User ID
            household_id: Household ID
            required_role: Required role (None for any member)

        Returns:
            True if user has permission
        """
        try:
            query = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
            )

            if required_role:
                query = query.filter(UserHousehold.role == required_role)

            return query.first() is not None

        except Exception as e:
            logger.error(f"Error checking user permission: {e}")
            return False 