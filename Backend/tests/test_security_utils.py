"""
Tests for security utilities.
"""

import pytest
from unittest.mock import Mock, patch
import secrets
import string
from datetime import datetime, timedelta
import jwt

from app.core.utils.security import (
    create_access_token, create_refresh_token, verify_token,
    get_password_hash, verify_password, generate_password_reset_token,
    verify_password_reset_token, generate_random_string, generate_invite_code
)


class TestJWTTokens:
    """Test cases for JWT token functions."""
    
    @patch('app.core.utils.security.settings')
    def test_create_access_token_default_expiry(self, mock_settings):
        """Test access token creation with default expiry."""
        mock_settings.jwt_access_token_expire_minutes = 30
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        token = create_access_token("user123")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert "exp" in payload
    
    @patch('app.core.utils.security.settings')
    def test_create_access_token_custom_expiry(self, mock_settings):
        """Test access token creation with custom expiry."""
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        custom_delta = timedelta(hours=2)
        token = create_access_token("user123", expires_delta=custom_delta)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token expiry
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        exp_time = datetime.utcfromtimestamp(payload["exp"])  # Use utcfromtimestamp for UTC time
        expected_time = datetime.utcnow() + custom_delta
        
        # Allow 1 minute tolerance for test execution time
        assert abs((exp_time - expected_time).total_seconds()) < 60
    
    @patch('app.core.utils.security.settings')
    def test_create_refresh_token(self, mock_settings):
        """Test refresh token creation."""
        mock_settings.jwt_refresh_token_expire_days = 7
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        token = create_refresh_token("user123")
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "exp" in payload
    
    @patch('app.core.utils.security.settings')
    def test_verify_token_valid(self, mock_settings):
        """Test token verification with valid token."""
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        # Create a token first
        token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
            "test_secret",
            algorithm="HS256"
        )
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
    
    @patch('app.core.utils.security.settings')
    def test_verify_token_invalid(self, mock_settings):
        """Test token verification with invalid token."""
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    @patch('app.core.utils.security.settings')
    def test_verify_token_expired(self, mock_settings):
        """Test token verification with expired token."""
        mock_settings.jwt_secret_key = "test_secret"
        mock_settings.jwt_algorithm = "HS256"
        
        # Create an expired token
        expired_token = jwt.encode(
            {"sub": "user123", "exp": datetime.utcnow() - timedelta(hours=1)},
            "test_secret",
            algorithm="HS256"
        )
        
        payload = verify_token(expired_token)
        
        assert payload is None


class TestPasswordHashing:
    """Test cases for password hashing functions."""
    
    def test_get_password_hash(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
        assert hashed.startswith("$2b$")  # bcrypt hash format
    
    def test_get_password_hash_consistency(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(password, hashed)
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        is_valid = verify_password(wrong_password, hashed)
        assert is_valid is False
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "testpassword123"
        invalid_hash = "invalid_hash"
        
        is_valid = verify_password(password, invalid_hash)
        assert is_valid is False
    
    def test_verify_password_empty_inputs(self):
        """Test password verification with empty inputs."""
        assert verify_password("", "") is False
        assert verify_password("password", "") is False
        assert verify_password("", "hash") is False


class TestPasswordResetTokens:
    """Test cases for password reset token functions."""
    
    @patch('app.core.utils.security.settings')
    def test_generate_password_reset_token(self, mock_settings):
        """Test password reset token generation."""
        mock_settings.email_reset_token_expire_hours = 24
        mock_settings.secret_key = "test_secret"
        
        email = "test@example.com"
        token = generate_password_reset_token(email)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
        assert payload["sub"] == email
        assert "exp" in payload
        assert "nbf" in payload
    
    @patch('app.core.utils.security.settings')
    def test_verify_password_reset_token_valid(self, mock_settings):
        """Test password reset token verification with valid token."""
        mock_settings.email_reset_token_expire_hours = 24
        mock_settings.secret_key = "test_secret"
        
        email = "test@example.com"
        token = generate_password_reset_token(email)
        
        verified_email = verify_password_reset_token(token)
        assert verified_email == email
    
    @patch('app.core.utils.security.settings')
    def test_verify_password_reset_token_invalid(self, mock_settings):
        """Test password reset token verification with invalid token."""
        mock_settings.secret_key = "test_secret"
        
        invalid_token = "invalid.token.here"
        verified_email = verify_password_reset_token(invalid_token)
        
        assert verified_email is None
    
    @patch('app.core.utils.security.settings')
    def test_verify_password_reset_token_expired(self, mock_settings):
        """Test password reset token verification with expired token."""
        mock_settings.secret_key = "test_secret"
        
        # Create an expired token manually
        now = datetime.utcnow()
        expires = now - timedelta(hours=1)  # Expired 1 hour ago
        exp = expires.timestamp()
        
        expired_token = jwt.encode(
            {"exp": exp, "nbf": now - timedelta(hours=2), "sub": "test@example.com"},
            "test_secret",
            algorithm="HS256"
        )
        
        verified_email = verify_password_reset_token(expired_token)
        assert verified_email is None


class TestRandomStringGeneration:
    """Test cases for random string generation functions."""
    
    def test_generate_random_string_default_length(self):
        """Test random string generation with default length."""
        random_str = generate_random_string()
        
        assert isinstance(random_str, str)
        assert len(random_str) == 32  # Default length
        # Should contain only letters and digits
        assert all(c in string.ascii_letters + string.digits for c in random_str)
    
    def test_generate_random_string_custom_length(self):
        """Test random string generation with custom length."""
        length = 16
        random_str = generate_random_string(length)
        
        assert isinstance(random_str, str)
        assert len(random_str) == length
    
    def test_generate_random_string_uniqueness(self):
        """Test that generated strings are unique."""
        strings = [generate_random_string() for _ in range(100)]
        
        # All strings should be unique
        assert len(set(strings)) == 100
    
    def test_generate_invite_code_default_length(self):
        """Test invite code generation with default length."""
        invite_code = generate_invite_code()
        
        assert isinstance(invite_code, str)
        assert len(invite_code) == 8  # Default length
        # Should contain only uppercase letters and digits
        assert all(c in string.ascii_uppercase + string.digits for c in invite_code)
    
    def test_generate_invite_code_custom_length(self):
        """Test invite code generation with custom length."""
        length = 12
        invite_code = generate_invite_code(length)
        
        assert isinstance(invite_code, str)
        assert len(invite_code) == length
    
    def test_generate_invite_code_uniqueness(self):
        """Test that generated invite codes are unique."""
        codes = [generate_invite_code() for _ in range(100)]
        
        # Most codes should be unique (allowing for small chance of collision)
        assert len(set(codes)) > 95
    
    def test_generate_invite_code_format(self):
        """Test invite code format (uppercase and digits only)."""
        invite_code = generate_invite_code(20)
        
        # Should not contain lowercase letters
        assert not any(c.islower() for c in invite_code)
        # Should not contain special characters
        assert not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in invite_code) 