"""
Password history model for authentication module (optional).
"""

from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, relationship

from app.core.models.base import BaseModel


class PasswordHistory(BaseModel):
    """Model for tracking password history to prevent reuse."""

    __tablename__ = "password_history"

    # Foreign key to user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Password information
    password_hash = Column(
        String(255),
        nullable=False
    )

    # Metadata
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    change_reason = Column(String(100), nullable=True)  # manual, expired, reset, etc.

    # Relationship to user
    user = relationship("User", back_populates="password_history")

    def __repr__(self) -> str:
        return f"<PasswordHistory(id={self.id}, user_id={self.user_id}, changed_at={self.changed_at})>"

    @classmethod
    def add_password_to_history(
        cls,
        db: Session,
        user_id: UUID,
        password_hash: str,
        change_reason: str | None = None,
        max_history: int = 5
    ) -> None:
        """
        Add a password to user's history and maintain history limit.

        Args:
            db: Database session
            user_id: User UUID
            password_hash: Hashed password
            change_reason: Reason for password change
            max_history: Maximum number of passwords to keep in history
        """
        # Add new password to history
        new_entry = cls(
            user_id=user_id,
            password_hash=password_hash,
            change_reason=change_reason
        )
        db.add(new_entry)

        # Clean up old entries if we exceed the limit
        existing_count = db.query(cls).filter(cls.user_id == user_id).count()

        if existing_count >= max_history:
            # Get oldest entries to delete
            oldest_entries = (
                db.query(cls)
                .filter(cls.user_id == user_id)
                .order_by(cls.changed_at.asc())
                .limit(existing_count - max_history + 1)
                .all()
            )

            for entry in oldest_entries:
                db.delete(entry)

        db.commit()

    @classmethod
    def get_user_password_history(
        cls,
        db: Session,
        user_id: UUID,
        limit: int = 5
    ) -> list[str]:
        """
        Get user's recent password hashes.

        Args:
            db: Database session
            user_id: User UUID
            limit: Number of recent passwords to retrieve

        Returns:
            List of recent password hashes
        """
        entries = (
            db.query(cls)
            .filter(cls.user_id == user_id)
            .order_by(cls.changed_at.desc())
            .limit(limit)
            .all()
        )

        return [entry.password_hash for entry in entries]

    @classmethod
    def cleanup_old_history(
        cls,
        db: Session,
        days_to_keep: int = 365
    ) -> int:
        """
        Clean up old password history entries.

        Args:
            db: Database session
            days_to_keep: Number of days to keep history

        Returns:
            Number of entries deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_count = (
            db.query(cls)
            .filter(cls.changed_at < cutoff_date)
            .delete()
        )

        db.commit()
        return deleted_count
