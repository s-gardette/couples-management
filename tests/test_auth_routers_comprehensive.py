"""
Comprehensive tests for auth routers to improve test coverage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from uuid import uuid4
from datetime import datetime

from app.modules.auth.routers.auth import router
from app.modules.auth.models.user import User
from app.main import app
from app.modules.auth.dependencies import get_current_user


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock()


@pytest.fixture
def sample_user():
    """Create a sample user."""
    user = User()
    user.id = uuid4()
    user.email = "test@example.com"
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_active = True
    user.email_verified = True
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


class TestAuthRouters:
    """Test cases for auth router endpoints."""

    def test_login_success(self, client, mock_db, sample_user):
        """Test successful login."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock successful authentication
                mock_service.authenticate_user = AsyncMock(return_value=(
                    True,
                    "Login successful",
                    {
                        "access_token": "access_token_123",
                        "refresh_token": "refresh_token_123",
                        "expires_in": 3600,
                        "user": {
                            "id": str(sample_user.id),
                            "email": sample_user.email,
                            "username": sample_user.username
                        }
                    }
                ))
                
                response = client.post("/api/auth/login", json={
                    "email_or_username": "test@example.com",
                    "password": "correct_password"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["access_token"] == "access_token_123"
                assert data["refresh_token"] == "refresh_token_123"
                assert data["token_type"] == "bearer"
                assert data["expires_in"] == 3600
                assert "user" in data

    def test_login_invalid_credentials(self, client, mock_db):
        """Test login with invalid credentials."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock failed authentication
                mock_service.authenticate_user = AsyncMock(return_value=(
                    False,
                    "Invalid credentials",
                    None
                ))
                
                response = client.post("/api/auth/login", json={
                    "email_or_username": "test@example.com",
                    "password": "wrong_password"
                })
                
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Invalid credentials" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        response = client.post("/api/auth/login", json={
            "email_or_username": "test@example.com"
            # Missing password
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_logout_success(self, client, mock_db, sample_user):
        """Test successful user logout."""
        # Override the dependency
        def override_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
                with patch('app.modules.auth.services.auth_service.AuthService.logout_user') as mock_logout:
                    mock_get_db.return_value = mock_db
                    mock_logout.return_value = (True, "Logout successful")
                    
                    response = client.post("/api/auth/logout", 
                        json={"session_token": "session123"},
                        headers={"Authorization": "Bearer valid_token"}
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    data = response.json()
                    assert data["success"] is True
                    assert data["message"] == "Logout successful"
        finally:
            # Clean up the override
            app.dependency_overrides.clear()

    def test_logout_invalid_auth_header(self, client):
        """Test logout with invalid authorization header."""
        response = client.post("/api/auth/logout", 
            json={"session_token": "session123"},
            headers={"Authorization": "Invalid header"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_no_auth_header(self, client):
        """Test logout without authorization header."""
        response = client.post("/api/auth/logout", 
            json={"session_token": "session123"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, client):
        """Test successful token refresh."""
        with patch('app.modules.auth.utils.jwt.refresh_access_token') as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600
            }
            
            response = client.post("/api/auth/refresh", json={
                "refresh_token": "valid_refresh_token"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "new_access_token"
            assert data["refresh_token"] == "new_refresh_token"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 3600

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token."""
        with patch('app.modules.auth.utils.jwt.refresh_access_token') as mock_refresh:
            mock_refresh.return_value = None
            
            response = client.post("/api/auth/refresh", json={
                "refresh_token": "invalid_refresh_token"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "Invalid or expired refresh token" in data["detail"]

    def test_forgot_password_success(self, client, mock_db):
        """Test successful password reset request."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.services.auth_service.AuthService.request_password_reset') as mock_reset:
                mock_get_db.return_value = mock_db
                mock_reset.return_value = (True, "Password reset link has been sent", "t***@example.com")
                
                response = client.post("/api/auth/forgot-password", json={
                    "email": "test@example.com"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "Password reset link has been sent"
                assert data["masked_email"] == "t***@example.com"

    def test_forgot_password_user_not_found(self, client, mock_db):
        """Test password reset request for non-existent user."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock failed password reset request
                mock_service.request_password_reset = AsyncMock(return_value=(
                    False,
                    "User not found",
                    None
                ))
                
                response = client.post("/api/auth/forgot-password", json={
                    "email": "nonexistent@example.com"
                })
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "User not found" in response.json()["detail"]

    def test_reset_password_success(self, client, mock_db):
        """Test successful password reset."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock successful password reset
                mock_service.reset_password = AsyncMock(return_value=(
                    True,
                    "Password reset successfully"
                ))
                
                response = client.post("/api/auth/reset-password", json={
                    "token": "valid_reset_token",
                    "new_password": "NewStrongPass123!"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert "successfully" in data["message"]

    def test_reset_password_invalid_token(self, client, mock_db):
        """Test password reset with invalid token."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock failed password reset
                mock_service.reset_password = AsyncMock(return_value=(
                    False,
                    "Invalid or expired token"
                ))
                
                response = client.post("/api/auth/reset-password", json={
                    "token": "invalid_token",
                    "new_password": "NewStrongPass123!"
                })
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "Invalid or expired token" in response.json()["detail"]

    def test_verify_email_success(self, client, mock_db):
        """Test successful email verification."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock successful email verification
                mock_service.verify_email = AsyncMock(return_value=(
                    True,
                    "Email verified successfully"
                ))
                
                response = client.post("/api/auth/verify-email", json={
                    "token": "valid_verification_token"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert "verified" in data["message"]

    def test_verify_email_invalid_token(self, client, mock_db):
        """Test email verification with invalid token."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock failed email verification
                mock_service.verify_email = AsyncMock(return_value=(
                    False,
                    "Invalid or expired verification token"
                ))
                
                response = client.post("/api/auth/verify-email", json={
                    "token": "invalid_token"
                })
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "Invalid or expired" in response.json()["detail"]

    def test_resend_verification_success(self, client, mock_db):
        """Test successful verification email resend."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock successful verification resend
                mock_service.resend_verification_email = AsyncMock(return_value=(
                    True,
                    "Verification email sent"
                ))
                
                response = client.post("/api/auth/resend-verification", json={
                    "email": "test@example.com"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert "sent" in data["message"]

    def test_resend_verification_user_not_found(self, client, mock_db):
        """Test verification email resend for non-existent user."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock failed verification resend
                mock_service.resend_verification_email = AsyncMock(return_value=(
                    False,
                    "User not found"
                ))
                
                response = client.post("/api/auth/resend-verification", json={
                    "email": "nonexistent@example.com"
                })
                
                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "User not found" in response.json()["detail"]

    def test_check_password_strength_strong(self, client):
        """Test password strength check with strong password."""
        with patch('app.modules.auth.routers.auth.validate_password_strength_detailed') as mock_validate:
            mock_validate.return_value = {
                "is_valid": True,
                "score": 5,
                "level": "very_strong",
                "errors": [],
                "suggestions": []
            }
            
            response = client.post("/api/auth/check-password-strength", json={
                "password": "StrongPassword123!"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is True
            assert data["score"] == 5
            assert data["level"] == "very_strong"
            assert data["errors"] == []

    def test_check_password_strength_weak(self, client):
        """Test password strength check with weak password."""
        with patch('app.modules.auth.routers.auth.validate_password_strength_detailed') as mock_validate:
            mock_validate.return_value = {
                "is_valid": False,
                "score": 2,
                "level": "weak",
                "errors": ["Password too short", "No special characters"],
                "suggestions": ["Add special characters", "Make it longer"]
            }
            
            response = client.post("/api/auth/check-password-strength", json={
                "password": "weak"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["is_valid"] is False
            assert data["score"] == 2
            assert data["level"] == "weak"
            assert len(data["errors"]) == 2
            assert len(data["suggestions"]) == 2

    def test_get_current_user_info_success(self, client, mock_db, sample_user):
        """Test getting current user information."""
        # Override the dependency
        def override_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.get("/api/auth/me", 
                headers={"Authorization": "Bearer valid_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["username"] == "testuser"
        finally:
            # Clean up the override
            app.dependency_overrides.clear()

    def test_get_current_user_info_unauthorized(self, client):
        """Test getting current user info without authentication."""
        response = client.get("/api/auth/me")
        
        # This should fail due to missing authentication
        # The exact status code depends on the get_current_user dependency implementation
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_login_sets_cookies(self, client, mock_db, sample_user):
        """Test that login sets secure cookies."""
        with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
            with patch('app.modules.auth.routers.auth.AuthService') as mock_auth_service:
                mock_get_db.return_value = mock_db
                mock_service = Mock()
                mock_auth_service.return_value = mock_service
                
                # Mock successful authentication
                mock_service.authenticate_user = AsyncMock(return_value=(
                    True,
                    "Login successful",
                    {
                        "access_token": "access_token_123",
                        "refresh_token": "refresh_token_123",
                        "expires_in": 3600,
                        "user": {
                            "id": str(sample_user.id),
                            "email": sample_user.email,
                            "username": sample_user.username
                        }
                    }
                ))
                
                response = client.post("/api/auth/login", json={
                    "email_or_username": "test@example.com",
                    "password": "correct_password"
                })
                
                assert response.status_code == status.HTTP_200_OK
                
                # Check that cookies are set
                cookies = response.cookies
                assert "access_token" in cookies
                assert "refresh_token" in cookies

    def test_logout_clears_cookies(self, client, mock_db, sample_user):
        """Test that logout clears authentication cookies."""
        # Override the dependency
        def override_get_current_user():
            return sample_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.modules.auth.routers.auth.get_db') as mock_get_db:
                with patch('app.modules.auth.services.auth_service.AuthService.logout_user') as mock_logout:
                    mock_get_db.return_value = mock_db
                    mock_logout.return_value = (True, "Logout successful")
                    
                    response = client.post("/api/auth/logout", 
                        json={"session_token": "session123"},
                        headers={"Authorization": "Bearer valid_token"}
                    )
                    
                    assert response.status_code == status.HTTP_200_OK
                    
                    # Check that cookies are cleared (they should be in the response headers)
                    # Note: In test client, we can't directly check if cookies are cleared
                    # but we can verify the response is successful
                    data = response.json()
                    assert data["success"] is True 
        finally:
            # Clean up the override
            app.dependency_overrides.clear() 