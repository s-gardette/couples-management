"""
Comprehensive tests for UserService to improve test coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from app.modules.auth.services.user_service import UserService
from app.modules.auth.models.user import User
from app.modules.auth.models.password_history import PasswordHistory
from app.modules.auth.schemas.user import UserCreate, UserUpdate


class TestUserServiceComprehensive:
    """Comprehensive test cases for UserService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        db.get = Mock()
        db.rollback = Mock()
        db.flush = Mock()
        return db
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create a UserService instance."""
        service = UserService(mock_db)
        service.get_by_id = Mock()
        return service
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        user = User()
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.hashed_password = "hashed_password"
        user.is_active = True
        user.email_verified = True
        user.avatar_url = None
        user.created_at = datetime.utcnow()
        return user

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, user_service, sample_user):
        """Test successful user profile retrieval."""
        user_service.get_by_id.return_value = sample_user
        
        result = await user_service.get_user_profile(sample_user.id)
        
        assert result == sample_user
        user_service.get_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self, user_service):
        """Test user profile retrieval when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        result = await user_service.get_user_profile(user_id)
        
        assert result is None
        user_service.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self, user_service, mock_db, sample_user):
        """Test successful user profile update."""
        user_service.get_by_id.return_value = sample_user
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing user with same email/username
        
        with patch('app.modules.auth.services.user_service.validate_email') as mock_validate:
            mock_validate.return_value = True
            
            success, message, user = await user_service.update_user_profile(
                user_id=sample_user.id,
                first_name="Updated",
                last_name="Name",
                email="new@example.com",
                username="newusername"
            )
        
        assert success is True
        assert "successfully" in message
        assert user == sample_user
        assert sample_user.first_name == "Updated"
        assert sample_user.last_name == "Name"
        assert sample_user.email == "new@example.com"
        assert sample_user.username == "newusername"
        assert sample_user.email_verified is False  # Should reset verification
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_profile_user_not_found(self, user_service):
        """Test user profile update when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        success, message, user = await user_service.update_user_profile(
            user_id=user_id,
            first_name="Updated"
        )
        
        assert success is False
        assert "User not found" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_profile_invalid_email(self, user_service, sample_user):
        """Test user profile update with invalid email."""
        user_service.get_by_id.return_value = sample_user
        
        with patch('app.modules.auth.services.user_service.validate_email') as mock_validate:
            mock_validate.return_value = False
            
            success, message, user = await user_service.update_user_profile(
                user_id=sample_user.id,
                email="invalid-email"
            )
        
        assert success is False
        assert "Invalid email format" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_profile_email_exists(self, user_service, mock_db, sample_user):
        """Test user profile update with existing email."""
        user_service.get_by_id.return_value = sample_user
        existing_user = User()
        existing_user.id = uuid4()
        existing_user.email = "existing@example.com"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_user
        
        with patch('app.modules.auth.services.user_service.validate_email') as mock_validate:
            mock_validate.return_value = True
            
            success, message, user = await user_service.update_user_profile(
                user_id=sample_user.id,
                email="existing@example.com"
            )
        
        assert success is False
        assert "already in use" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_profile_username_exists(self, user_service, mock_db, sample_user):
        """Test user profile update with existing username."""
        user_service.get_by_id.return_value = sample_user
        existing_user = User()
        existing_user.id = uuid4()
        existing_user.username = "existinguser"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = existing_user
        
        success, message, user = await user_service.update_user_profile(
            user_id=sample_user.id,
            username="existinguser"
        )
        
        assert success is False
        assert "already taken" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_update_user_profile_exception(self, user_service, mock_db, sample_user):
        """Test user profile update with database exception."""
        user_service.get_by_id.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")
        
        success, message, user = await user_service.update_user_profile(
            user_id=sample_user.id,
            first_name="Updated"
        )
        
        assert success is False
        assert "Profile update failed" in message
        assert user is None
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_db, sample_user):
        """Test successful password change."""
        user_service.get_by_id.return_value = sample_user
        
        # Mock password history query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        with patch('app.modules.auth.services.user_service.validate_password_change') as mock_validate:
            with patch('app.modules.auth.services.user_service.hash_password') as mock_hash:
                mock_validate.return_value = {"is_valid": True, "errors": []}
                mock_hash.return_value = "new_hashed_password"
                
                success, message = await user_service.change_password(
                    user_id=sample_user.id,
                    current_password="current_pass",
                    new_password="new_pass"
                )
        
        assert success is True
        assert "successfully" in message
        assert sample_user.hashed_password == "new_hashed_password"
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self, user_service):
        """Test password change when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        success, message = await user_service.change_password(
            user_id=user_id,
            current_password="current_pass",
            new_password="new_pass"
        )
        
        assert success is False
        assert "User not found" in message

    @pytest.mark.asyncio
    async def test_change_password_validation_failed(self, user_service, mock_db, sample_user):
        """Test password change with validation failure."""
        user_service.get_by_id.return_value = sample_user
        
        # Mock password history query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        with patch('app.modules.auth.services.user_service.validate_password_change') as mock_validate:
            mock_validate.return_value = {
                "is_valid": False, 
                "errors": ["Password too weak", "Password reused"]
            }
            
            success, message = await user_service.change_password(
                user_id=sample_user.id,
                current_password="current_pass",
                new_password="weak"
            )
        
        assert success is False
        assert "Password change failed" in message
        assert "Password too weak" in message

    @pytest.mark.asyncio
    async def test_change_password_exception(self, user_service, mock_db, sample_user):
        """Test password change with database exception."""
        user_service.get_by_id.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")
        
        # Mock password history query
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        with patch('app.modules.auth.services.user_service.validate_password_change') as mock_validate:
            with patch('app.modules.auth.services.user_service.hash_password') as mock_hash:
                mock_validate.return_value = {"is_valid": True, "errors": []}
                mock_hash.return_value = "new_hashed_password"
                
                success, message = await user_service.change_password(
                    user_id=sample_user.id,
                    current_password="current_pass",
                    new_password="new_pass"
                )
        
        assert success is False
        assert "Password change failed" in message
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_avatar_success(self, user_service, mock_db, sample_user):
        """Test successful avatar update."""
        user_service.get_by_id.return_value = sample_user
        avatar_url = "https://example.com/avatar.jpg"
        
        success, message = await user_service.update_avatar(
            user_id=sample_user.id,
            avatar_url=avatar_url
        )
        
        assert success is True
        assert "successfully" in message
        assert sample_user.avatar_url == avatar_url
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_avatar_user_not_found(self, user_service):
        """Test avatar update when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        success, message = await user_service.update_avatar(
            user_id=user_id,
            avatar_url="https://example.com/avatar.jpg"
        )
        
        assert success is False
        assert "User not found" in message

    @pytest.mark.asyncio
    async def test_update_avatar_exception(self, user_service, mock_db, sample_user):
        """Test avatar update with database exception."""
        user_service.get_by_id.return_value = sample_user
        mock_db.commit.side_effect = Exception("Database error")
        
        success, message = await user_service.update_avatar(
            user_id=sample_user.id,
            avatar_url="https://example.com/avatar.jpg"
        )
        
        assert success is False
        assert "Avatar update failed" in message
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_service, mock_db, sample_user):
        """Test successful user activation."""
        sample_user.is_active = False
        user_service.get_by_id.return_value = sample_user
        
        success, message = await user_service.activate_user(sample_user.id)
        
        assert success is True
        assert "activated" in message
        assert sample_user.is_active is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_not_found(self, user_service):
        """Test user activation when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        success, message = await user_service.activate_user(user_id)
        
        assert success is False
        assert "User not found" in message

    @pytest.mark.asyncio
    async def test_activate_user_already_active(self, user_service, sample_user):
        """Test activation of already active user."""
        sample_user.is_active = True
        user_service.get_by_id.return_value = sample_user
        
        success, message = await user_service.activate_user(sample_user.id)
        
        assert success is True
        assert "activated" in message

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, mock_db, sample_user):
        """Test successful user deactivation."""
        sample_user.is_active = True
        user_service.get_by_id.return_value = sample_user
        
        success, message = await user_service.deactivate_user(sample_user.id)
        
        assert success is True
        assert "deactivated" in message
        assert sample_user.is_active is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_users_with_query(self, user_service, mock_db, sample_user):
        """Test user search with query."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]
        
        result = await user_service.search_users(
            query="test",
            email_verified=True,
            is_active=True,
            limit=10,
            offset=0
        )
        
        assert result == [sample_user]
        mock_query.filter.assert_called()
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, mock_db, sample_user):
        """Test getting user by email."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        result = await user_service.get_user_by_email("test@example.com")
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, user_service, mock_db, sample_user):
        """Test getting user by username."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        result = await user_service.get_user_by_username("testuser")
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_check_email_availability_available(self, user_service, mock_db):
        """Test email availability check when available."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = await user_service.check_email_availability("new@example.com")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_check_email_availability_taken(self, user_service, mock_db, sample_user):
        """Test email availability check when taken."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        result = await user_service.check_email_availability("test@example.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_check_username_availability_available(self, user_service, mock_db):
        """Test username availability check when available."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        result = await user_service.check_username_availability("newuser")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_service, mock_db):
        """Test getting user statistics."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 100
        mock_query.filter.return_value = mock_query
        
        result = await user_service.get_user_stats()
        
        assert isinstance(result, dict)
        assert "total_users" in result
        assert "active_users" in result
        assert "verified_users" in result

    @pytest.mark.asyncio
    async def test_get_recent_users(self, user_service, mock_db, sample_user):
        """Test getting recent users."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]
        
        result = await user_service.get_recent_users(limit=5)
        
        assert result == [sample_user]
        mock_query.limit.assert_called_with(5)

    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_db, sample_user):
        """Test successful user deletion."""
        user_service.get_by_id.return_value = sample_user
        
        # Mock the base service delete method to avoid the database session issue
        with patch.object(user_service, 'delete') as mock_delete:
            mock_delete.return_value = sample_user
            
            success, message = await user_service.delete_user(sample_user.id)
            
            assert success is True
            assert "deleted" in message
            # The actual implementation calls self.delete(user_id) without db session
            mock_delete.assert_called_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service):
        """Test user deletion when user not found."""
        user_service.get_by_id.return_value = None
        user_id = uuid4()
        
        success, message = await user_service.delete_user(user_id)
        
        assert success is False
        assert "User not found" in message 