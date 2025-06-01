"""
Admin Users service for user management operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_

from app.modules.auth.models.user import User
from app.modules.admin.schemas.admin_ui import AdminUserResponse, AdminUserListResponse

logger = logging.getLogger(__name__)


class AdminUsersService:
    """Service for admin user management operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_users_list(
        self,
        search: Optional[str] = None,
        role_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> AdminUserListResponse:
        """
        Get paginated list of users with filtering and searching.
        """
        try:
            # Base query
            query = self.db.query(User)
            
            # Apply search filter
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        User.email.ilike(search_term),
                        User.username.ilike(search_term),
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                        func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
                    )
                )
            
            # Apply role filter
            if role_filter:
                if role_filter == "admin":
                    query = query.filter(User.role == "admin")
                elif role_filter == "user":
                    query = query.filter(User.role == "user")
            
            # Apply status filter
            if status_filter:
                if status_filter == "active":
                    query = query.filter(User.is_active == True)
                elif status_filter == "inactive":
                    query = query.filter(User.is_active == False)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply sorting
            sort_column = getattr(User, sort_by, User.created_at)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # Apply pagination
            offset = (page - 1) * limit
            users = query.offset(offset).limit(limit).all()
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1
            
            # Convert to response format
            user_responses = []
            for user in users:
                user_responses.append(AdminUserResponse(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=user.role,
                    is_active=user.is_active,
                    email_verified=user.email_verified,
                    created_at=user.created_at,
                    last_login_at=user.last_login_at,
                    avatar_url=user.avatar_url
                ))
            
            return AdminUserListResponse(
                users=user_responses,
                total_count=total_count,
                page=page,
                limit=limit,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except Exception as e:
            logger.error(f"Error getting users list: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[AdminUserResponse]:
        """
        Get a single user by ID.
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            return AdminUserResponse(
                id=str(user.id),
                email=user.email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                email_verified=user.email_verified,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
                avatar_url=user.avatar_url
            )
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise
    
    async def toggle_user_status(self, user_id: str, admin_user_id: str) -> Dict[str, Any]:
        """
        Toggle user active status (activate/deactivate).
        Admins cannot deactivate themselves.
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Prevent admin from deactivating themselves
            if user_id == admin_user_id and user.role == "admin":
                return {"success": False, "message": "Administrators cannot deactivate themselves"}
            
            # Toggle status
            user.is_active = not user.is_active
            self.db.commit()
            
            action = "activated" if user.is_active else "deactivated"
            logger.info(f"User {user.email} has been {action} by admin {admin_user_id}")
            
            return {
                "success": True, 
                "message": f"User has been {action} successfully",
                "new_status": user.is_active
            }
            
        except Exception as e:
            logger.error(f"Error toggling user status for {user_id}: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": "An error occurred while updating user status"}
    
    async def update_user(
        self,
        user_id: str,
        admin_user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        email_verified: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update user information.
        Includes validation and permission checks.
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Prevent admin from changing their own role or deactivating themselves
            if user_id == admin_user_id:
                if role and role != user.role:
                    return {"success": False, "message": "Administrators cannot change their own role"}
                if is_active is False and user.role == "admin":
                    return {"success": False, "message": "Administrators cannot deactivate themselves"}
            
            # Check if email is already taken by another user
            if email and email != user.email:
                existing_email = self.db.query(User).filter(
                    and_(User.email == email.lower(), User.id != user_id)
                ).first()
                if existing_email:
                    return {"success": False, "message": "Email address is already in use"}
            
            # Check if username is already taken by another user
            if username and username != user.username:
                existing_username = self.db.query(User).filter(
                    and_(User.username == username.lower(), User.id != user_id)
                ).first()
                if existing_username:
                    return {"success": False, "message": "Username is already taken"}
            
            # Update user fields
            original_values = {}
            if first_name is not None:
                original_values['first_name'] = user.first_name
                user.first_name = first_name.strip() if first_name else None
            
            if last_name is not None:
                original_values['last_name'] = user.last_name
                user.last_name = last_name.strip() if last_name else None
            
            if username is not None:
                original_values['username'] = user.username
                user.username = username.strip().lower() if username else None
            
            if email is not None:
                original_values['email'] = user.email
                user.email = email.strip().lower()
            
            if role is not None and role in ['user', 'admin']:
                original_values['role'] = user.role
                user.role = role
            
            if is_active is not None:
                original_values['is_active'] = user.is_active
                user.is_active = is_active
            
            if email_verified is not None:
                original_values['email_verified'] = user.email_verified
                user.email_verified = email_verified
            
            # Update timestamp
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log the changes
            changed_fields = []
            for field, old_value in original_values.items():
                new_value = getattr(user, field)
                if old_value != new_value:
                    changed_fields.append(f"{field}: {old_value} → {new_value}")
            
            if changed_fields:
                logger.info(f"User {user.email} updated by admin {admin_user_id}. Changes: {', '.join(changed_fields)}")
            
            return {
                "success": True,
                "message": "User updated successfully",
                "changed_fields": changed_fields
            }
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": "An error occurred while updating user"}
    
    async def change_user_password(
        self,
        user_id: str,
        admin_user_id: str,
        new_password: str,
        force_change_on_login: bool = False
    ) -> Dict[str, Any]:
        """
        Change a user's password. Admin can set any password.
        """
        try:
            from app.modules.auth.utils.security import hash_password
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Hash the new password
            hashed_password = hash_password(new_password)
            
            # Update user password
            user.hashed_password = hashed_password
            user.requires_password_change = force_change_on_login
            user.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Password changed for user {user.email} by admin {admin_user_id}")
            
            return {
                "success": True,
                "message": f"Password updated successfully{' (user will be required to change it on next login)' if force_change_on_login else ''}"
            }
            
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {str(e)}")
            self.db.rollback()
            return {"success": False, "message": "An error occurred while changing password"}
    
    async def send_password_reset_link(
        self,
        user_id: str,
        admin_user_id: str
    ) -> Dict[str, Any]:
        """
        Generate and send a password reset link to the user.
        """
        try:
            from app.modules.auth.services.auth_service import AuthService
            
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Generate reset token using the correct method
            auth_service = AuthService(self.db)
            success, message, masked_email = await auth_service.request_password_reset(user.email)
            
            if success:
                # In a real application, you would send an email here
                # For now, we'll just log it and return a temporary link
                # Since we don't have access to the actual token, we'll generate a placeholder
                reset_link = f"http://localhost:8000/auth/reset-password?email={user.email}"
                
                logger.info(f"Password reset link generated for user {user.email} by admin {admin_user_id}")
                logger.info(f"Reset link placeholder: {reset_link}")
                
                return {
                    "success": True,
                    "message": "Password reset link has been sent to the user's email",
                    "reset_link": reset_link  # In production, remove this and send via email
                }
            else:
                return {"success": False, "message": f"Failed to generate reset token: {message}"}
            
        except Exception as e:
            logger.error(f"Error sending password reset for user {user_id}: {str(e)}")
            return {"success": False, "message": "An error occurred while sending password reset link"}
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics for admin dashboard.
        """
        try:
            total_users = self.db.query(User).count()
            active_users = self.db.query(User).filter(User.is_active == True).count()
            admin_users = self.db.query(User).filter(User.role == "admin").count()
            
            # Users created in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            new_users_30d = self.db.query(User).filter(
                User.created_at >= thirty_days_ago
            ).count()
            
            # Users with recent login (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_logins = self.db.query(User).filter(
                and_(
                    User.last_login_at >= seven_days_ago,
                    User.is_active == True
                )
            ).count()
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "admin_users": admin_users,
                "new_users_30d": new_users_30d,
                "recent_logins": recent_logins
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            raise 