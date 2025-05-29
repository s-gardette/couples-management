"""
Tests for authentication utility functions.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
from uuid import uuid4

from app.modules.auth.utils.jwt import JWTManager, create_user_tokens
from app.core.utils.security import get_password_hash, verify_password


class TestJWTManager:
    """Test cases for JWT Manager."""
    
    @pytest.fixture
    def jwt_manager(self):
        """Create a JWT manager instance."""
        return JWTManager()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        return db
    
    def test_create_access_token(self, jwt_manager):
        """Test access token creation."""
        user_id = uuid4()
        
        token, jti = jwt_manager.create_access_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(jti, str)
        assert len(jti) > 0
    
    def test_create_refresh_token(self, jwt_manager):
        """Test refresh token creation."""
        user_id = uuid4()
        
        token, jti = jwt_manager.create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(jti, str)
        assert len(jti) > 0
    
    def test_create_token_pair(self, jwt_manager):
        """Test creating token pair."""
        user_id = uuid4()
        
        result = jwt_manager.create_token_pair(user_id)
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        assert result["token_type"] == "bearer"
    
    def test_verify_token_valid(self, jwt_manager, mock_db):
        """Test token verification with valid token."""
        user_id = uuid4()
        
        # Mock TokenBlacklist.is_token_blacklisted to return False
        with patch('app.modules.auth.utils.jwt.TokenBlacklist.is_token_blacklisted', return_value=False):
            token, jti = jwt_manager.create_access_token(user_id)
            payload = jwt_manager.verify_token(token, mock_db)
        
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_token_invalid(self, jwt_manager, mock_db):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = jwt_manager.verify_token(invalid_token, mock_db)
        
        assert payload is None
    
    def test_verify_token_blacklisted(self, jwt_manager, mock_db):
        """Test token verification with blacklisted token."""
        user_id = uuid4()
        
        # Mock TokenBlacklist.is_token_blacklisted to return True
        with patch('app.modules.auth.utils.jwt.TokenBlacklist.is_token_blacklisted', return_value=True):
            token, jti = jwt_manager.create_access_token(user_id)
            payload = jwt_manager.verify_token(token, mock_db)
        
        assert payload is None
    
    def test_refresh_access_token_success(self, jwt_manager, mock_db):
        """Test successful token refresh."""
        user_id = uuid4()
        
        # Mock TokenBlacklist.is_token_blacklisted to return False
        with patch('app.modules.auth.utils.jwt.TokenBlacklist.is_token_blacklisted', return_value=False):
            refresh_token, _ = jwt_manager.create_refresh_token(user_id)
            result = jwt_manager.refresh_access_token(refresh_token, mock_db)
        
        assert result is not None
        assert "access_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer"
    
    def test_refresh_access_token_invalid(self, jwt_manager, mock_db):
        """Test token refresh with invalid token."""
        invalid_token = "invalid.refresh.token"
        
        result = jwt_manager.refresh_access_token(invalid_token, mock_db)
        
        assert result is None


class TestSecurityUtils:
    """Test cases for security utility functions."""
    
    def test_get_password_hash(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(password, hashed)
        
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(wrong_password, hashed)
        
        assert is_valid is False
    
    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_create_user_tokens(self):
        """Test user token creation utility function."""
        user_id = uuid4()
        
        result = create_user_tokens(user_id)
        
        assert isinstance(result, dict)
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert result["token_type"] == "bearer" 