"""
Authentication service for user registration, login, and token management.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.services.base_service import BaseService
from app.core.utils.validators import validate_email
from app.modules.auth.models.email_verification import EmailVerificationToken
from app.modules.auth.models.password_history import PasswordHistory
from app.modules.auth.models.password_reset import PasswordResetToken
from app.modules.auth.models.user import User
from app.modules.auth.models.user_session import UserSession
from app.modules.auth.schemas.user import UserCreate, UserUpdate
from app.modules.auth.utils.jwt import blacklist_token, create_user_tokens
from app.modules.auth.utils.password import (
    check_password_history,
    validate_password_strength_detailed,
)
from app.modules.auth.utils.security import (
    generate_password_reset_token_secure,
    generate_session_token,
    generate_verification_token,
    hash_password,
    mask_email,
    verify_password_secure,
)


class AuthService(BaseService[User, UserCreate, UserUpdate]):
    """Service for authentication operations."""

    def __init__(self, db: Session):
        super().__init__(User)
        self.db = db

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None
    ) -> tuple[bool, str, User | None]:
        """
        Register a new user.

        Args:
            email: User email address
            username: Unique username
            password: Plain text password
            first_name: Optional first name
            last_name: Optional last name

        Returns:
            Tuple of (success, message, user_object)
        """
        try:
            # Validate email format
            if not validate_email(email):
                return False, "Invalid email format", None

            # Validate password strength
            password_validation = validate_password_strength_detailed(password)
            if not password_validation["is_valid"]:
                errors = ", ".join(password_validation["errors"])
                return False, f"Password validation failed: {errors}", None

            # Check if email already exists
            existing_user = self.db.query(User).filter(User.email == email.lower()).first()
            if existing_user:
                return False, "Email address is already registered", None

            # Check if username already exists
            existing_username = self.db.query(User).filter(User.username == username.lower()).first()
            if existing_username:
                return False, "Username is already taken", None

            # Hash password
            hashed_password = hash_password(password)

            # Create user
            user = User(
                email=email.lower(),
                username=username.lower(),
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                email_verified=False,
                is_active=True
            )

            self.db.add(user)
            self.db.flush()  # Get the user ID

            # Create password history entry
            password_history = PasswordHistory(
                user_id=user.id,
                password_hash=hashed_password,
                changed_at=datetime.utcnow()
            )
            self.db.add(password_history)

            # Generate email verification token
            verification_token = EmailVerificationToken(
                user_id=user.id,
                token=generate_verification_token(),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            self.db.add(verification_token)

            self.db.commit()

            return True, "User registered successfully", user

        except IntegrityError:
            self.db.rollback()
            return False, "Email or username already exists", None
        except Exception as e:
            self.db.rollback()
            return False, f"Registration failed: {str(e)}", None

    async def authenticate_user(
        self,
        email_or_username: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None
    ) -> tuple[bool, str, dict | None]:
        """
        Authenticate a user and create session.

        Args:
            email_or_username: Email or username
            password: Plain text password
            user_agent: User agent string
            ip_address: IP address

        Returns:
            Tuple of (success, message, token_data)
        """
        try:
            # Find user by email or username
            user = self.db.query(User).filter(
                (User.email == email_or_username.lower()) |
                (User.username == email_or_username.lower())
            ).first()

            if not user:
                return False, "Invalid credentials", None

            # Check if user is active
            if not user.is_active:
                return False, "Account is deactivated", None

            # Verify password
            if not verify_password_secure(password, user.hashed_password):
                return False, "Invalid credentials", None

            # Update last login
            user.update_last_login()

            # Create JWT tokens
            token_data = create_user_tokens(
                user_id=user.id,
                email=user.email,
                username=user.username,
                email_verified=user.email_verified
            )

            # Create user session
            session = UserSession(
                user_id=user.id,
                session_token=generate_session_token(),
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True
            )
            self.db.add(session)

            self.db.commit()

            return True, "Login successful", token_data

        except Exception as e:
            self.db.rollback()
            return False, f"Authentication failed: {str(e)}", None

    async def logout_user(
        self,
        user_id: UUID,
        access_token: str,
        session_token: str | None = None
    ) -> tuple[bool, str]:
        """
        Logout a user by blacklisting tokens and deactivating session.

        Args:
            user_id: User UUID
            access_token: Access token to blacklist
            session_token: Optional session token to deactivate

        Returns:
            Tuple of (success, message)
        """
        try:
            # Blacklist the access token
            blacklist_success = blacklist_token(
                token=access_token,
                db=self.db,
                reason="User logout"
            )

            if not blacklist_success:
                return False, "Failed to blacklist token"

            # Deactivate session if provided
            if session_token:
                session = self.db.query(UserSession).filter(
                    UserSession.user_id == user_id,
                    UserSession.session_token == session_token,
                    UserSession.is_active
                ).first()

                if session:
                    session.deactivate()

            self.db.commit()
            return True, "Logout successful"

        except Exception as e:
            self.db.rollback()
            return False, f"Logout failed: {str(e)}"

    async def request_password_reset(
        self,
        email: str
    ) -> tuple[bool, str, str | None]:
        """
        Request a password reset token.

        Args:
            email: User email address

        Returns:
            Tuple of (success, message, masked_email)
        """
        try:
            user = self.db.query(User).filter(User.email == email.lower()).first()

            if not user:
                # Don't reveal if email exists for security
                return True, "If the email exists, a reset link has been sent", mask_email(email)

            if not user.is_active:
                return False, "Account is deactivated", None

            # Deactivate any existing reset tokens
            existing_tokens = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.user_id == user.id,
                not PasswordResetToken.is_used,
                PasswordResetToken.expires_at > datetime.utcnow()
            ).all()

            for token in existing_tokens:
                token.mark_as_used()

            # Create new reset token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=generate_password_reset_token_secure(),
                expires_at=datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
            )
            self.db.add(reset_token)

            self.db.commit()

            return True, "Password reset link has been sent", mask_email(email)

        except Exception as e:
            self.db.rollback()
            return False, f"Password reset request failed: {str(e)}", None

    async def reset_password(
        self,
        token: str,
        new_password: str
    ) -> tuple[bool, str]:
        """
        Reset password using a reset token.

        Args:
            token: Password reset token
            new_password: New plain text password

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find valid reset token
            reset_token = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.token == token,
                not PasswordResetToken.is_used,
                PasswordResetToken.expires_at > datetime.utcnow()
            ).first()

            if not reset_token:
                return False, "Invalid or expired reset token"

            user = self.db.query(User).filter(User.id == reset_token.user_id).first()
            if not user:
                return False, "User not found"

            # Validate new password strength
            password_validation = validate_password_strength_detailed(new_password)
            if not password_validation["is_valid"]:
                errors = ", ".join(password_validation["errors"])
                return False, f"Password validation failed: {errors}"

            # Check password history
            password_history = self.db.query(PasswordHistory).filter(
                PasswordHistory.user_id == user.id
            ).order_by(PasswordHistory.changed_at.desc()).limit(5).all()

            history_hashes = [ph.password_hash for ph in password_history]
            is_allowed, history_error = check_password_history(
                new_password=new_password,
                password_history=history_hashes,
                history_limit=5
            )

            if not is_allowed:
                return False, history_error

            # Hash new password
            new_hashed_password = hash_password(new_password)

            # Update user password
            user.hashed_password = new_hashed_password

            # Add to password history
            password_history_entry = PasswordHistory(
                user_id=user.id,
                password_hash=new_hashed_password,
                changed_at=datetime.utcnow()
            )
            self.db.add(password_history_entry)

            # Mark reset token as used
            reset_token.mark_as_used()

            self.db.commit()

            return True, "Password reset successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Password reset failed: {str(e)}"

    async def verify_email(
        self,
        token: str
    ) -> tuple[bool, str]:
        """
        Verify user email using verification token.

        Args:
            token: Email verification token

        Returns:
            Tuple of (success, message)
        """
        try:
            # Find valid verification token
            verification_token = self.db.query(EmailVerificationToken).filter(
                EmailVerificationToken.token == token,
                not EmailVerificationToken.is_used,
                EmailVerificationToken.expires_at > datetime.utcnow()
            ).first()

            if not verification_token:
                return False, "Invalid or expired verification token"

            user = self.db.query(User).filter(User.id == verification_token.user_id).first()
            if not user:
                return False, "User not found"

            # Verify email
            user.verify_email()
            verification_token.mark_as_used()

            self.db.commit()

            return True, "Email verified successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Email verification failed: {str(e)}"

    async def resend_verification_email(
        self,
        email: str
    ) -> tuple[bool, str]:
        """
        Resend email verification token.

        Args:
            email: User email address

        Returns:
            Tuple of (success, message)
        """
        try:
            user = self.db.query(User).filter(User.email == email.lower()).first()

            if not user:
                return False, "User not found"

            if user.email_verified:
                return False, "Email is already verified"

            if not user.is_active:
                return False, "Account is deactivated"

            # Deactivate existing verification tokens
            existing_tokens = self.db.query(EmailVerificationToken).filter(
                EmailVerificationToken.user_id == user.id,
                not EmailVerificationToken.is_used
            ).all()

            for token in existing_tokens:
                token.mark_as_used()

            # Create new verification token
            verification_token = EmailVerificationToken(
                user_id=user.id,
                token=generate_verification_token(),
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            self.db.add(verification_token)

            self.db.commit()

            return True, "Verification email sent"

        except Exception as e:
            self.db.rollback()
            return False, f"Failed to resend verification email: {str(e)}"
