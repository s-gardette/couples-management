"""
User session model for authentication module.
"""

from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.models.base import BaseModel


class UserSession(BaseModel):
    """Model for tracking user sessions."""

    __tablename__ = "user_sessions"

    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Session information
    session_token = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    refresh_token = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True
    )

    # Session metadata
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Device/browser information
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)
    device_info = Column(String(255), nullable=True)

    # Session termination
    logged_out_at = Column(DateTime, nullable=True)
    logout_reason = Column(String(100), nullable=True)  # manual, expired, security, etc.

    # Relationship to user
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"

    @classmethod
    def create_for_user(
        cls,
        user_id: UUID,
        session_token: str,
        expires_in_minutes: int = 30,
        refresh_token: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None
    ):
        """Create a new session for a user."""
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        return cls(
            user_id=user_id,
            session_token=session_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info
        )

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the session is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity_at = datetime.utcnow()

    def extend_session(self, minutes: int = 30) -> None:
        """Extend the session expiration time."""
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.update_activity()

    def terminate_session(self, reason: str = "manual") -> None:
        """Terminate the session."""
        self.is_active = False
        self.logged_out_at = datetime.utcnow()
        self.logout_reason = reason

    def refresh_session(self, new_session_token: str, new_refresh_token: str | None = None) -> None:
        """Refresh the session with new tokens."""
        self.session_token = new_session_token
        if new_refresh_token:
            self.refresh_token = new_refresh_token
        self.update_activity()
