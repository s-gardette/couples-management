"""
Tests for authentication services.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.services.user_service import UserService
from app.modules.auth.models.user import User
from app.modules.auth.schemas.auth import LoginRequest


class TestAuthService:
    """Test cases for AuthService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        db.rollback = Mock()
        db.flush = Mock()
        return db
    
    @pytest.fixture
    def auth_service(self, mock_db):
        """Create an AuthService instance."""
        return AuthService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        user = User()
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.hashed_password = "hashed_password"
        user.is_active = True
        user.email_verified = True
        return user
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db):
        """Test successful user registration."""
        # Setup
        email = "test@example.com"
        username = "testuser"
        password = "StrongPass123!"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing user
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                    with patch('app.modules.auth.services.auth_service.generate_verification_token') as mock_token:
                        mock_validate_email.return_value = True
                        mock_validate_password.return_value = {"is_valid": True, "errors": []}
                        mock_hash.return_value = "hashed_password"
                        mock_token.return_value = "verification_token"
                        
                        success, message, user = await auth_service.register_user(
                            email=email,
                            username=username,
                            password=password
                        )
        
        # Assertions
        assert success is True
        assert "successfully" in message
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, auth_service, mock_db, sample_user):
        """Test registration with existing email."""
        # Setup
        email = "test@example.com"
        username = "testuser"
        password = "StrongPass123!"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user  # Existing user
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            mock_validate_email.return_value = True
            
            success, message, user = await auth_service.register_user(
                email=email,
                username=username,
                password=password
            )
        
        # Assertions
        assert success is False
        assert "already registered" in message
        assert user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service, mock_db):
        """Test authentication with invalid credentials."""
        # Setup
        email_or_username = "test@example.com"
        password = "wrong_password"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # User not found
        
        success, message, token_data = await auth_service.authenticate_user(
            email_or_username=email_or_username,
            password=password
        )
        
        # Assertions
        assert success is False
        assert "Invalid credentials" in message
        assert token_data is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_service, mock_db, sample_user):
        """Test authentication with inactive user."""
        # Setup
        sample_user.is_active = False
        email_or_username = "test@example.com"
        password = "correct_password"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        success, message, token_data = await auth_service.authenticate_user(
            email_or_username=email_or_username,
            password=password
        )
        
        # Assertions
        assert success is False
        assert "deactivated" in message
        assert token_data is None


class TestUserService:
    """Test cases for UserService."""
    
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
        return db
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create a UserService instance."""
        return UserService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        user = User()
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_active = True
        return user
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, user_service, mock_db, sample_user):
        """Test getting user by email when found."""
        # Setup
        email = "test@example.com"
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        # Test
        result = await user_service.get_user_by_email(email)
        
        # Assertions
        assert result == sample_user
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_found(self, user_service, mock_db, sample_user):
        """Test getting user by username when found."""
        # Setup
        username = "testuser"
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        # Test
        result = await user_service.get_user_by_username(username)
        
        # Assertions
        assert result == sample_user
    
    @pytest.mark.asyncio
    async def test_search_users_by_email(self, user_service, mock_db, sample_user):
        """Test searching users by email."""
        # Setup
        search_term = "test"
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_user]
        
        # Test
        result = await user_service.search_users(search_term)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == sample_user 