"""
Comprehensive tests for the BaseService class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.services.base_service import BaseService
from app.core.models.base import BaseModel


# Mock model for testing
class MockModel:
    __tablename__ = "mock_table"
    __name__ = "MockModel"
    id = Mock()  # Add class-level id attribute for SQLAlchemy queries
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)


# Mock schema classes
class MockCreateSchema:
    def __init__(self, **kwargs):
        self._data = kwargs
    
    def dict(self):
        return self._data


class MockUpdateSchema:
    def __init__(self, **kwargs):
        self._data = kwargs
    
    def dict(self, exclude_unset=False):
        return self._data


class TestBaseService:
    """Test cases for BaseService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = BaseService(MockModel)
        self.mock_db = Mock(spec=Session)
        self.test_id = uuid4()

    def test_init(self):
        """Test service initialization."""
        service = BaseService(MockModel)
        assert service.model == MockModel

    def test_get_success(self):
        """Test successful get operation."""
        mock_obj = MockModel(id=self.test_id, name="test")
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        
        result = self.service.get(self.mock_db, self.test_id)
        
        assert result == mock_obj
        self.mock_db.query.assert_called_once_with(MockModel)

    def test_get_not_found(self):
        """Test get operation when record not found."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.get(self.mock_db, self.test_id)
        
        assert result is None

    def test_get_database_error(self):
        """Test get operation with database error."""
        self.mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get(self.mock_db, self.test_id)
        
        assert exc_info.value.status_code == 500
        assert "Database error occurred" in str(exc_info.value.detail)

    def test_get_or_404_success(self):
        """Test successful get_or_404 operation."""
        mock_obj = MockModel(id=self.test_id, name="test")
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_obj
        
        result = self.service.get_or_404(self.mock_db, self.test_id)
        
        assert result == mock_obj

    def test_get_or_404_not_found(self):
        """Test get_or_404 operation when record not found."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_or_404(self.mock_db, self.test_id)
        
        assert exc_info.value.status_code == 404
        assert "MockModel not found" in str(exc_info.value.detail)

    def test_get_multi_success(self):
        """Test successful get_multi operation."""
        mock_objs = [MockModel(id=uuid4(), name=f"test{i}") for i in range(3)]
        query_mock = self.mock_db.query.return_value
        query_mock.offset.return_value.limit.return_value.all.return_value = mock_objs
        
        result = self.service.get_multi(self.mock_db, skip=0, limit=10)
        
        assert result == mock_objs
        query_mock.offset.assert_called_once_with(0)
        query_mock.offset.return_value.limit.assert_called_once_with(10)

    def test_get_multi_with_filters(self):
        """Test get_multi operation with filters."""
        mock_objs = [MockModel(id=uuid4(), name="test", active=True)]
        query_mock = self.mock_db.query.return_value
        query_mock.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_objs
        
        # Create a mock model with the active attribute
        mock_model = Mock()
        mock_model.active = Mock()
        
        with patch.object(self.service, 'model', mock_model):
            result = self.service.get_multi(
                self.mock_db, 
                skip=0, 
                limit=10, 
                filters={"active": True}
            )
        
        assert result == mock_objs

    def test_get_multi_database_error(self):
        """Test get_multi operation with database error."""
        self.mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.get_multi(self.mock_db)
        
        assert exc_info.value.status_code == 500

    def test_create_success(self):
        """Test successful create operation."""
        create_data = MockCreateSchema(name="test", email="test@example.com")
        mock_obj = MockModel(id=self.test_id, name="test", email="test@example.com")
        
        # Mock the model constructor to return our mock object
        with patch.object(self.service, 'model') as mock_model_class:
            mock_model_class.return_value = mock_obj
            mock_model_class.__name__ = "MockModel"
            
            self.mock_db.add.return_value = None
            self.mock_db.commit.return_value = None
            self.mock_db.refresh.return_value = None
            
            result = self.service.create(self.mock_db, obj_in=create_data)
        
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    def test_create_with_dict_input(self):
        """Test create operation with dictionary input."""
        create_data = {"name": "test", "email": "test@example.com"}
        mock_obj = MockModel(id=self.test_id, name="test", email="test@example.com")
        
        with patch.object(self.service, 'model') as mock_model_class:
            mock_model_class.return_value = mock_obj
            mock_model_class.__name__ = "MockModel"
            
            self.mock_db.add.return_value = None
            self.mock_db.commit.return_value = None
            self.mock_db.refresh.return_value = None
            
            result = self.service.create(self.mock_db, obj_in=create_data)
        
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    def test_create_integrity_error(self):
        """Test create operation with integrity error."""
        create_data = MockCreateSchema(name="test")
        
        with patch.object(self.service, 'model') as mock_model_class:
            mock_model_class.__name__ = "MockModel"
            self.mock_db.add.side_effect = IntegrityError("", "", "")
            
            with pytest.raises(HTTPException) as exc_info:
                self.service.create(self.mock_db, obj_in=create_data)
        
        assert exc_info.value.status_code == 400
        assert "Data integrity error" in str(exc_info.value.detail)
        self.mock_db.rollback.assert_called_once()

    def test_create_database_error(self):
        """Test create operation with database error."""
        create_data = MockCreateSchema(name="test")
        
        with patch.object(self.service, 'model') as mock_model_class:
            mock_model_class.__name__ = "MockModel"
            self.mock_db.add.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                self.service.create(self.mock_db, obj_in=create_data)
        
        assert exc_info.value.status_code == 500
        self.mock_db.rollback.assert_called_once()

    def test_update_success(self):
        """Test successful update operation."""
        db_obj = MockModel(id=self.test_id, name="old_name")
        update_data = MockUpdateSchema(name="new_name")
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Mock hasattr to return True for the name attribute
        with patch('builtins.hasattr') as mock_hasattr:
            mock_hasattr.return_value = True
            result = self.service.update(self.mock_db, db_obj=db_obj, obj_in=update_data)
        
        # Check that the attribute was set
        assert db_obj.name == "new_name"
        self.mock_db.add.assert_called_once_with(db_obj)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(db_obj)

    def test_update_with_dict_input(self):
        """Test update operation with dictionary input."""
        db_obj = MockModel(id=self.test_id, name="old_name")
        update_data = {"name": "new_name"}
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # Mock hasattr to return False for dict (since dict doesn't have dict() method)
        # and True for db_obj attributes
        def mock_hasattr_side_effect(obj, attr):
            if obj is update_data and attr == 'dict':
                return False
            elif obj is db_obj and attr == 'name':
                return True
            return hasattr(obj, attr)
        
        with patch('builtins.hasattr', side_effect=mock_hasattr_side_effect):
            result = self.service.update(self.mock_db, db_obj=db_obj, obj_in=update_data)
        
        assert db_obj.name == "new_name"

    def test_update_integrity_error(self):
        """Test update operation with integrity error."""
        db_obj = MockModel(id=self.test_id, name="old_name")
        update_data = MockUpdateSchema(name="new_name")
        
        self.mock_db.add.side_effect = IntegrityError("", "", "")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update(self.mock_db, db_obj=db_obj, obj_in=update_data)
        
        assert exc_info.value.status_code == 400
        self.mock_db.rollback.assert_called_once()

    def test_update_database_error(self):
        """Test update operation with database error."""
        db_obj = MockModel(id=self.test_id, name="old_name")
        update_data = MockUpdateSchema(name="new_name")
        
        self.mock_db.add.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.update(self.mock_db, db_obj=db_obj, obj_in=update_data)
        
        assert exc_info.value.status_code == 500
        self.mock_db.rollback.assert_called_once()

    def test_delete_success(self):
        """Test successful delete operation."""
        mock_obj = MockModel(id=self.test_id, name="test")
        
        with patch.object(self.service, 'get_or_404', return_value=mock_obj):
            self.mock_db.delete.return_value = None
            self.mock_db.commit.return_value = None
            
            result = self.service.delete(self.mock_db, id=self.test_id)
        
        assert result == mock_obj
        self.mock_db.delete.assert_called_once_with(mock_obj)
        self.mock_db.commit.assert_called_once()

    def test_delete_database_error(self):
        """Test delete operation with database error."""
        mock_obj = MockModel(id=self.test_id, name="test")
        
        with patch.object(self.service, 'get_or_404', return_value=mock_obj):
            self.mock_db.delete.side_effect = SQLAlchemyError("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                self.service.delete(self.mock_db, id=self.test_id)
        
        assert exc_info.value.status_code == 500
        self.mock_db.rollback.assert_called_once()

    def test_count_success(self):
        """Test successful count operation."""
        self.mock_db.query.return_value.count.return_value = 5
        
        result = self.service.count(self.mock_db)
        
        assert result == 5
        self.mock_db.query.assert_called_once_with(MockModel)

    def test_count_with_filters(self):
        """Test count operation with filters."""
        query_mock = self.mock_db.query.return_value
        query_mock.filter.return_value.count.return_value = 3
        
        # Create a mock model with the active attribute
        mock_model = Mock()
        mock_model.active = Mock()
        
        with patch.object(self.service, 'model', mock_model):
            result = self.service.count(self.mock_db, filters={"active": True})
        
        assert result == 3

    def test_count_database_error(self):
        """Test count operation with database error."""
        self.mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            self.service.count(self.mock_db)
        
        assert exc_info.value.status_code == 500 