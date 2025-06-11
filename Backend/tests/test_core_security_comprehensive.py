"""
Comprehensive tests for core security utilities to improve test coverage.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import jwt
import string

from app.core.utils.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_random_string,
    generate_invite_code
)


class TestCoreSecurityUtils:
    """Test cases for core security utilities."""

    def test_create_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiry."""
        subject = "user123"
        expires_delta = timedelta(minutes=30)
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            
            token = create_access_token(subject, expires_delta)
            
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Verify token can be decoded
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["sub"] == subject

    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        subject = "user123"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_access_token_expire_minutes = 15
            
            token = create_access_token(subject)
            
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Verify token can be decoded
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["sub"] == subject

    def test_create_access_token_with_non_string_subject(self):
        """Test creating access token with non-string subject."""
        subject = 12345
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_access_token_expire_minutes = 15
            
            token = create_access_token(subject)
            
            assert isinstance(token, str)
            
            # Verify token can be decoded and subject is converted to string
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["sub"] == "12345"

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        subject = "user123"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.jwt_refresh_token_expire_days = 30
            
            token = create_refresh_token(subject)
            
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Verify token can be decoded
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["sub"] == subject
            assert payload["type"] == "refresh"

    def test_verify_token_valid(self):
        """Test verifying valid token."""
        subject = "user123"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            
            # Create a token first
            expire = datetime.utcnow() + timedelta(minutes=30)
            to_encode = {"exp": expire, "sub": subject}
            token = jwt.encode(to_encode, "test_secret", algorithm="HS256")
            
            # Verify the token
            payload = verify_token(token)
            
            assert payload is not None
            assert payload["sub"] == subject

    def test_verify_token_invalid(self):
        """Test verifying invalid token."""
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            
            # Test with completely invalid token
            payload = verify_token("invalid_token")
            assert payload is None

    def test_verify_token_expired(self):
        """Test verifying expired token."""
        subject = "user123"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "test_secret"
            mock_settings.jwt_algorithm = "HS256"
            
            # Create an expired token
            expire = datetime.utcnow() - timedelta(minutes=30)  # Expired
            to_encode = {"exp": expire, "sub": subject}
            token = jwt.encode(to_encode, "test_secret", algorithm="HS256")
            
            # Verify the token
            payload = verify_token(token)
            assert payload is None

    def test_verify_token_wrong_secret(self):
        """Test verifying token with wrong secret."""
        subject = "user123"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.jwt_secret_key = "wrong_secret"
            mock_settings.jwt_algorithm = "HS256"
            
            # Create a token with different secret
            expire = datetime.utcnow() + timedelta(minutes=30)
            to_encode = {"exp": expire, "sub": subject}
            token = jwt.encode(to_encode, "correct_secret", algorithm="HS256")
            
            # Try to verify with wrong secret
            payload = verify_token(token)
            assert payload is None

    def test_get_password_hash(self):
        """Test password hashing."""
        password = "test_password_123"
        
        hashed = get_password_hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be different from original
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_get_password_hash_different_passwords(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)
        
        assert hash1 != hash2

    def test_get_password_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes due to salt."""
        password = "test_password"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Should be different due to different salts
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        result = verify_password(wrong_password, hashed)
        assert result is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "test_password"
        invalid_hash = "invalid_hash"
        
        result = verify_password(password, invalid_hash)
        assert result is False

    def test_verify_password_empty_password(self):
        """Test password verification with empty password."""
        password = ""
        hashed = get_password_hash("some_password")
        
        result = verify_password(password, hashed)
        assert result is False

    def test_verify_password_empty_hash(self):
        """Test password verification with empty hash."""
        password = "test_password"
        empty_hash = ""
        
        result = verify_password(password, empty_hash)
        assert result is False

    def test_generate_password_reset_token(self):
        """Test generating password reset token."""
        email = "test@example.com"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.email_reset_token_expire_hours = 24
            mock_settings.secret_key = "test_secret"
            
            token = generate_password_reset_token(email)
            
            assert isinstance(token, str)
            assert len(token) > 0
            
            # Verify token can be decoded
            payload = jwt.decode(token, "test_secret", algorithms=["HS256"])
            assert payload["sub"] == email

    def test_verify_password_reset_token_valid(self):
        """Test verifying valid password reset token."""
        email = "test@example.com"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.email_reset_token_expire_hours = 24
            mock_settings.secret_key = "test_secret"
            
            # Generate token
            token = generate_password_reset_token(email)
            
            # Verify token
            result = verify_password_reset_token(token)
            assert result == email

    def test_verify_password_reset_token_invalid(self):
        """Test verifying invalid password reset token."""
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.secret_key = "test_secret"
            
            result = verify_password_reset_token("invalid_token")
            assert result is None

    def test_verify_password_reset_token_expired(self):
        """Test verifying expired password reset token."""
        email = "test@example.com"
        
        with patch('app.core.utils.security.settings') as mock_settings:
            mock_settings.secret_key = "test_secret"
            
            # Create expired token
            now = datetime.utcnow()
            expires = now - timedelta(hours=1)  # Expired
            exp = expires.timestamp()
            token = jwt.encode(
                {"exp": exp, "nbf": now, "sub": email},
                "test_secret",
                algorithm="HS256",
            )
            
            result = verify_password_reset_token(token)
            assert result is None

    def test_generate_random_string_default_length(self):
        """Test generating random string with default length."""
        result = generate_random_string()
        
        assert isinstance(result, str)
        assert len(result) == 32  # Default length
        
        # Check that it only contains valid characters
        valid_chars = string.ascii_letters + string.digits
        assert all(c in valid_chars for c in result)

    def test_generate_random_string_custom_length(self):
        """Test generating random string with custom length."""
        length = 16
        result = generate_random_string(length)
        
        assert isinstance(result, str)
        assert len(result) == length
        
        # Check that it only contains valid characters
        valid_chars = string.ascii_letters + string.digits
        assert all(c in valid_chars for c in result)

    def test_generate_random_string_uniqueness(self):
        """Test that generated random strings are unique."""
        string1 = generate_random_string()
        string2 = generate_random_string()
        
        assert string1 != string2

    def test_generate_random_string_zero_length(self):
        """Test generating random string with zero length."""
        result = generate_random_string(0)
        
        assert isinstance(result, str)
        assert len(result) == 0
        assert result == ""

    def test_generate_invite_code_default_length(self):
        """Test generating invite code with default length."""
        result = generate_invite_code()
        
        assert isinstance(result, str)
        assert len(result) == 8  # Default length
        
        # Check that it only contains valid characters (uppercase letters and digits)
        valid_chars = string.ascii_uppercase + string.digits
        assert all(c in valid_chars for c in result)

    def test_generate_invite_code_custom_length(self):
        """Test generating invite code with custom length."""
        length = 12
        result = generate_invite_code(length)
        
        assert isinstance(result, str)
        assert len(result) == length
        
        # Check that it only contains valid characters
        valid_chars = string.ascii_uppercase + string.digits
        assert all(c in valid_chars for c in result)

    def test_generate_invite_code_uniqueness(self):
        """Test that generated invite codes are unique."""
        code1 = generate_invite_code()
        code2 = generate_invite_code()
        
        assert code1 != code2

    def test_generate_invite_code_uppercase_only(self):
        """Test that invite codes only contain uppercase letters and digits."""
        result = generate_invite_code(100)  # Large sample
        
        # Should not contain any lowercase letters
        assert not any(c in string.ascii_lowercase for c in result)
        
        # Should only contain uppercase letters and digits
        valid_chars = string.ascii_uppercase + string.digits
        assert all(c in valid_chars for c in result) 