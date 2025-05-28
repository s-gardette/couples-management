"""
Base model classes and mixins for the application.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session

from app.database import Base


class UUIDMixin:
    """Mixin for UUID primary key."""
    
    @declared_attr
    def id(cls):
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            index=True
        )


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False,
            index=True
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    @declared_attr
    def is_deleted(cls):
        return Column(Boolean, default=False, nullable=False, index=True)
    
    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True)
    
    def soft_delete(self):
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model class with UUID primary key and timestamps."""
    
    __abstract__ = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        """Update model instance with provided kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def create(cls, db: Session, **kwargs):
        """Create a new instance and save to database."""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
    
    def save(self, db: Session):
        """Save the current instance to database."""
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
    
    def delete(self, db: Session):
        """Delete the current instance from database."""
        db.delete(self)
        db.commit()


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """Base model class with soft delete functionality."""
    
    __abstract__ = True
    
    @classmethod
    def get_active(cls, db: Session):
        """Get all active (non-deleted) records."""
        return db.query(cls).filter(cls.is_deleted == False)
    
    @classmethod
    def get_deleted(cls, db: Session):
        """Get all soft-deleted records."""
        return db.query(cls).filter(cls.is_deleted == True) 