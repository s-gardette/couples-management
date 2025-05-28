"""
User service for profile management and user operations.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.services.base_service import BaseService
from app.core.utils.validators import validate_email
from app.modules.auth.models.password_history import PasswordHistory
from app.modules.auth.models.user import User
from app.modules.auth.schemas.user import UserCreate, UserUpdate
from app.modules.auth.utils.password import (
    validate_password_change,
)
from app.modules.auth.utils.security import hash_password


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """Service for user profile management and operations."""

    def __init__(self, db: Session):
        super().__init__(User)
        self.db = db

    async def get_user_profile(self, user_id: UUID) -> User | None:
        """
        Get user profile by ID.

        Args:
            user_id: User UUID

        Returns:
            User object or None if not found
        """
        return self.get_by_id(user_id)

    async def update_user_profile(
        self,
        user_id: UUID,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        username: str | None = None
    ) -> tuple[bool, str, User | None]:
        """
        Update user profile information.

        Args:
            user_id: User UUID
            first_name: Optional new first name
            last_name: Optional new last name
            email: Optional new email
            username: Optional new username

        Returns:
            Tuple of (success, message, updated_user)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found", None

            # Validate email if provided
            if email and email != user.email:
                if not validate_email(email):
                    return False, "Invalid email format", None

                # Check if email already exists
                existing_user = self.db.query(User).filter(
                    and_(User.email == email.lower(), User.id != user_id)
                ).first()
                if existing_user:
                    return False, "Email address is already in use", None

                user.email = email.lower()
                user.email_verified = False  # Reset verification status

            # Validate username if provided
            if username and username != user.username:
                # Check if username already exists
                existing_user = self.db.query(User).filter(
                    and_(User.username == username.lower(), User.id != user_id)
                ).first()
                if existing_user:
                    return False, "Username is already taken", None

                user.username = username.lower()

            # Update other fields
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name

            self.db.commit()

            return True, "Profile updated successfully", user

        except Exception as e:
            self.db.rollback()
            return False, f"Profile update failed: {str(e)}", None

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> tuple[bool, str]:
        """
        Change user password with validation.

        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found"

            # Get password history
            password_history = self.db.query(PasswordHistory).filter(
                PasswordHistory.user_id == user_id
            ).order_by(PasswordHistory.changed_at.desc()).limit(5).all()

            history_hashes = [ph.password_hash for ph in password_history]

            # Validate password change
            validation_result = validate_password_change(
                current_password=current_password,
                new_password=new_password,
                current_password_hash=user.hashed_password,
                password_history=history_hashes
            )

            if not validation_result["is_valid"]:
                errors = ", ".join(validation_result["errors"])
                return False, f"Password change failed: {errors}"

            # Hash new password
            new_hashed_password = hash_password(new_password)

            # Update user password
            user.hashed_password = new_hashed_password

            # Add to password history
            password_history_entry = PasswordHistory(
                user_id=user_id,
                password_hash=new_hashed_password,
                changed_at=datetime.utcnow()
            )
            self.db.add(password_history_entry)

            self.db.commit()

            return True, "Password changed successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Password change failed: {str(e)}"

    async def update_avatar(
        self,
        user_id: UUID,
        avatar_url: str
    ) -> tuple[bool, str]:
        """
        Update user avatar URL.

        Args:
            user_id: User UUID
            avatar_url: New avatar URL

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found"

            user.avatar_url = avatar_url
            self.db.commit()

            return True, "Avatar updated successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Avatar update failed: {str(e)}"

    async def activate_user(self, user_id: UUID) -> tuple[bool, str]:
        """
        Activate a user account.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found"

            user.activate()
            self.db.commit()

            return True, "User activated successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"User activation failed: {str(e)}"

    async def deactivate_user(self, user_id: UUID) -> tuple[bool, str]:
        """
        Deactivate a user account.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found"

            user.deactivate()
            self.db.commit()

            return True, "User deactivated successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"User deactivation failed: {str(e)}"

    async def search_users(
        self,
        query: str | None = None,
        email_verified: bool | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[User]:
        """
        Search and filter users.

        Args:
            query: Search query for username, email, or name
            email_verified: Filter by email verification status
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching users
        """
        query_filter = self.db.query(User)

        # Apply search query
        if query:
            search_filter = or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%")
            )
            query_filter = query_filter.filter(search_filter)

        # Apply filters
        if email_verified is not None:
            query_filter = query_filter.filter(User.email_verified == email_verified)

        if is_active is not None:
            query_filter = query_filter.filter(User.is_active == is_active)

        # Apply pagination
        return query_filter.offset(offset).limit(limit).all()

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: Email address

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.email == email.lower()).first()

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.username == username.lower()).first()

    async def check_email_availability(self, email: str, exclude_user_id: UUID | None = None) -> bool:
        """
        Check if email is available for use.

        Args:
            email: Email to check
            exclude_user_id: Optional user ID to exclude from check

        Returns:
            True if email is available
        """
        query = self.db.query(User).filter(User.email == email.lower())

        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)

        return query.first() is None

    async def check_username_availability(self, username: str, exclude_user_id: UUID | None = None) -> bool:
        """
        Check if username is available for use.

        Args:
            username: Username to check
            exclude_user_id: Optional user ID to exclude from check

        Returns:
            True if username is available
        """
        query = self.db.query(User).filter(User.username == username.lower())

        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)

        return query.first() is None

    async def get_user_stats(self) -> dict[str, int]:
        """
        Get user statistics.

        Returns:
            Dictionary with user statistics
        """
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active).count()
        verified_users = self.db.query(User).filter(User.email_verified).count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "inactive_users": total_users - active_users,
            "unverified_users": total_users - verified_users
        }

    async def get_recent_users(self, limit: int = 10) -> list[User]:
        """
        Get recently registered users.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of recent users
        """
        return self.db.query(User).order_by(User.created_at.desc()).limit(limit).all()

    async def delete_user(self, user_id: UUID) -> tuple[bool, str]:
        """
        Soft delete a user account.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.get_by_id(user_id)
            if not user:
                return False, "User not found"

            # Soft delete using the base model's delete method
            self.delete(user_id)

            return True, "User deleted successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"User deletion failed: {str(e)}"
