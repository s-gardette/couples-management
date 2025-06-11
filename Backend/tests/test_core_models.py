"""
Tests for core models.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import Session

from app.core.models.base import BaseModel, UUIDMixin, TimestampMixin, SoftDeleteMixin
from app.core.models.mixins import (
    NameMixin, DescriptionMixin, ActiveMixin, SlugMixin, OrderMixin
)


class MockModel(BaseModel, SoftDeleteMixin, NameMixin, DescriptionMixin, 
                ActiveMixin, SlugMixin, OrderMixin):
    """Mock model combining all mixins for testing."""
    __tablename__ = "mock_models"
    
    # Additional test field
    test_field = Column(String(100))


class TestUUIDMixin:
    """Test cases for UUID mixin."""
    
    def test_uuid_mixin_has_id_column(self):
        """Test that UUID mixin adds id column."""
        assert hasattr(MockModel, 'id')
        assert MockModel.id.type.python_type == type(uuid4())
    
    def test_uuid_mixin_id_is_primary_key(self):
        """Test that id is primary key."""
        assert MockModel.id.primary_key is True


class TestTimestampMixin:
    """Test cases for timestamp mixin."""
    
    def test_timestamp_mixin_has_columns(self):
        """Test that timestamp mixin adds required columns."""
        assert hasattr(MockModel, 'created_at')
        assert hasattr(MockModel, 'updated_at')
        assert MockModel.created_at.type.python_type == datetime
        assert MockModel.updated_at.type.python_type == datetime


class TestSoftDeleteMixin:
    """Test cases for soft delete mixin."""
    
    def test_soft_delete_mixin_has_columns(self):
        """Test that soft delete mixin adds required columns."""
        assert hasattr(MockModel, 'is_deleted')
        assert hasattr(MockModel, 'deleted_at')
        assert MockModel.is_deleted.type.python_type == bool
        assert MockModel.deleted_at.type.python_type == datetime
    
    def test_soft_delete_functionality(self):
        """Test soft delete methods."""
        # Create instance with default values
        model = MockModel()
        
        # Test soft delete
        model.soft_delete()
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)
        
        # Test restore
        model.restore()
        assert model.is_deleted is False
        assert model.deleted_at is None


class TestNameMixin:
    """Test cases for name mixin."""
    
    def test_name_mixin_has_column(self):
        """Test that name mixin adds name column."""
        assert hasattr(MockModel, 'name')
        assert MockModel.name.type.python_type == str


class TestDescriptionMixin:
    """Test cases for description mixin."""
    
    def test_description_mixin_has_column(self):
        """Test that description mixin adds description column."""
        assert hasattr(MockModel, 'description')
        # Text columns don't have a direct python_type, so check the column exists


class TestActiveMixin:
    """Test cases for active mixin."""
    
    def test_active_mixin_has_column(self):
        """Test that active mixin adds is_active column."""
        assert hasattr(MockModel, 'is_active')
        assert MockModel.is_active.type.python_type == bool
        # Test default value
        assert MockModel.is_active.default.arg is True


class TestSlugMixin:
    """Test cases for slug mixin."""
    
    def test_slug_mixin_has_column(self):
        """Test that slug mixin adds slug column."""
        assert hasattr(MockModel, 'slug')
        assert MockModel.slug.type.python_type == str
        assert MockModel.slug.unique is True


class TestOrderMixin:
    """Test cases for order mixin."""
    
    def test_order_mixin_has_column(self):
        """Test that order mixin adds order column."""
        assert hasattr(MockModel, 'order')
        assert MockModel.order.type.python_type == int
        # Test default value
        assert MockModel.order.default.arg == 0


class TestBaseModel:
    """Test cases for base model."""
    
    def test_base_model_inheritance(self):
        """Test that base model includes required mixins."""
        assert issubclass(MockModel, BaseModel)
        assert issubclass(MockModel, UUIDMixin)
        assert issubclass(MockModel, TimestampMixin)
    
    def test_base_model_to_dict(self):
        """Test to_dict method."""
        model = MockModel()
        
        # Set some values
        model.name = "Test"
        model.description = "Test description"
        model.test_field = "test value"
        model.is_active = True
        model.order = 5
        
        data = model.to_dict()
        
        assert isinstance(data, dict)
        assert data["name"] == "Test"
        assert data["description"] == "Test description"
        assert data["test_field"] == "test value"
        assert data["is_active"] is True
        assert data["order"] == 5
    
    def test_base_model_update(self):
        """Test update method."""
        model = MockModel()
        model.name = "Original Name"
        model.test_field = "original value"
        
        model.update(
            name="Updated Name",
            description="New description"
        )
        
        assert model.name == "Updated Name"
        assert model.description == "New description"
        assert model.test_field == "original value"  # Unchanged
    
    def test_base_model_update_invalid_attribute(self):
        """Test update method with invalid attribute."""
        model = MockModel()
        
        # Should not raise error, just ignore invalid attributes
        model.update(
            name="Valid Name",
            invalid_attribute="Should be ignored"
        )
        
        assert model.name == "Valid Name"
        assert not hasattr(model, "invalid_attribute")
    
    def test_base_model_has_table_name(self):
        """Test that model has table name."""
        assert MockModel.__tablename__ == "mock_models"
    
    def test_base_model_abstract_flag(self):
        """Test that BaseModel is abstract."""
        assert BaseModel.__abstract__ is True 