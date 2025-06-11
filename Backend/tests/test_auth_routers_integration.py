"""
Integration tests for authentication routers.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from uuid import uuid4
import json
from datetime import datetime

from app.main import app
from app.modules.auth.models.user import User, UserRole
from app.modules.auth.dependencies import (
    get_current_user_from_cookie_or_header, 
    get_current_admin_user,
    get_current_user,
    get_current_verified_user,
    get_current_active_user,
    require_authentication
)


class TestAuthRouterIntegration:
    """Integration tests for authentication router endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
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
        user.email_verified = True
        user.role = UserRole.USER
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        return user
    
    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        user = User()
        user.id = uuid4()
        user.email = "admin@example.com"
        user.username = "admin"
        user.first_name = "Admin"
        user.last_name = "User"
        user.is_active = True
        user.email_verified = True
        user.role = UserRole.ADMIN
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        return user

    @patch('app.modules.auth.services.auth_service.AuthService.authenticate_user')
    def test_login_success(self, mock_authenticate, client, sample_user):
        """Test successful login."""
        # Mock successful authentication
        token_data = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "user": {
                "id": str(sample_user.id),
                "email": sample_user.email,
                "username": sample_user.username
            }
        }
        mock_authenticate.return_value = (True, "Login successful", token_data)
        
        response = client.post(
            "/api/auth/login",
            json={
                "email_or_username": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "test_access_token"
        assert data["refresh_token"] == "test_refresh_token"
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    @patch('app.modules.auth.services.auth_service.AuthService.authenticate_user')
    def test_login_failure(self, mock_authenticate, client):
        """Test login with invalid credentials."""
        mock_authenticate.return_value = (False, "Invalid credentials", None)
        
        response = client.post(
            "/api/auth/login",
            json={
                "email_or_username": "test@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid credentials"

    @patch('app.modules.auth.services.auth_service.AuthService.logout_user')
    def test_logout_success(self, mock_logout, client, sample_user):
        """Test successful logout."""
        # Override the base dependency to return our sample user
        app.dependency_overrides[get_current_user] = lambda: sample_user
        
        mock_logout.return_value = (True, "Logged out successfully")
        
        try:
            response = client.post(
                "/api/auth/logout",
                json={"session_token": "test_session"},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "Logged out successfully"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_logout_invalid_header(self, client, sample_user):
        """Test logout with invalid authorization header."""
        # Override the base dependency to return our sample user
        app.dependency_overrides[get_current_user] = lambda: sample_user
        
        try:
            response = client.post(
                "/api/auth/logout",
                json={"session_token": "test_session"},
                headers={"Authorization": "Invalid header"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid authorization header" in response.json()["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.utils.jwt.refresh_access_token')
    def test_refresh_token_success(self, mock_refresh, client):
        """Test successful token refresh."""
        token_data = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        mock_refresh.return_value = token_data
        
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "valid_refresh_token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new_access_token"
        assert data["refresh_token"] == "new_refresh_token"

    @patch('app.modules.auth.utils.jwt.refresh_access_token')
    def test_refresh_token_failure(self, mock_refresh, client):
        """Test token refresh with invalid token."""
        mock_refresh.return_value = None
        
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired refresh token" in response.json()["detail"]

    @patch('app.modules.auth.services.auth_service.AuthService.request_password_reset')
    def test_forgot_password_success(self, mock_reset, client):
        """Test successful password reset request."""
        mock_reset.return_value = (True, "Reset email sent", "t***@example.com")
        
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Reset email sent"
        assert data["masked_email"] == "t***@example.com"

    @patch('app.modules.auth.services.auth_service.AuthService.request_password_reset')
    def test_forgot_password_failure(self, mock_reset, client):
        """Test password reset request for non-existent email."""
        mock_reset.return_value = (False, "Email not found", None)
        
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email not found"

    @patch('app.modules.auth.services.auth_service.AuthService.reset_password')
    def test_reset_password_success(self, mock_reset, client):
        """Test successful password reset."""
        mock_reset.return_value = (True, "Password reset successfully")
        
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "valid_reset_token",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset successfully"

    @patch('app.modules.auth.services.auth_service.AuthService.reset_password')
    def test_reset_password_failure(self, mock_reset, client):
        """Test password reset with invalid token."""
        mock_reset.return_value = (False, "Invalid or expired token")
        
        response = client.post(
            "/api/auth/reset-password",
            json={
                "token": "invalid_token",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid or expired token"

    @patch('app.modules.auth.services.auth_service.AuthService.verify_email')
    def test_verify_email_success(self, mock_verify, client):
        """Test successful email verification."""
        mock_verify.return_value = (True, "Email verified successfully")
        
        response = client.post(
            "/api/auth/verify-email",
            json={"token": "valid_verification_token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Email verified successfully"

    @patch('app.modules.auth.services.auth_service.AuthService.verify_email')
    def test_verify_email_failure(self, mock_verify, client):
        """Test email verification with invalid token."""
        mock_verify.return_value = (False, "Invalid or expired token")
        
        response = client.post(
            "/api/auth/verify-email",
            json={"token": "invalid_token"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Invalid or expired token"

    @patch('app.modules.auth.services.auth_service.AuthService.resend_verification_email')
    def test_resend_verification_success(self, mock_resend, client):
        """Test successful verification email resend."""
        mock_resend.return_value = (True, "Verification email sent")
        
        response = client.post(
            "/api/auth/resend-verification",
            json={"email": "test@example.com"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Verification email sent"

    @patch('app.modules.auth.routers.auth.validate_password_strength_detailed')
    def test_check_password_strength_strong(self, mock_validate, client):
        """Test password strength check for strong password."""
        mock_validate.return_value = {
            "is_valid": True,
            "score": 85,
            "level": "strong",
            "errors": [],
            "suggestions": ["Your password meets all requirements!"]
        }
        
        response = client.post(
            "/api/auth/check-password-strength",
            json={"password": "StrongPassword123!"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["score"] == 85
        assert data["level"] == "strong"

    @patch('app.modules.auth.routers.auth.validate_password_strength_detailed')
    def test_check_password_strength_weak(self, mock_validate, client):
        """Test password strength check for weak password."""
        mock_validate.return_value = {
            "is_valid": False,
            "score": 25,
            "level": "weak",
            "errors": ["Password too short", "No special characters"],
            "suggestions": ["Use at least 8 characters", "Add special characters"]
        }
        
        response = client.post(
            "/api/auth/check-password-strength",
            json={"password": "weak"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is False
        assert data["score"] == 25
        assert data["level"] == "weak"

    def test_get_current_user_info(self, client, sample_user):
        """Test getting current user information."""
        # Override the base dependency to return our sample user
        app.dependency_overrides[get_current_user] = lambda: sample_user
        
        try:
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == sample_user.email
            assert data["username"] == sample_user.username
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()


class TestAdminRouterIntegration:
    """Integration tests for admin router endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        user = User()
        user.id = uuid4()
        user.email = "admin@example.com"
        user.username = "admin"
        user.first_name = "Admin"
        user.last_name = "User"
        user.is_active = True
        user.email_verified = True
        user.role = UserRole.ADMIN
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        return user

    @patch('app.modules.auth.services.auth_service.AuthService.register_user')
    @patch('app.modules.auth.services.user_service.UserService.get_by_email')
    @patch('app.modules.auth.services.user_service.UserService.get_by_username')
    def test_create_user_by_admin_success(self, mock_get_by_username, 
                                        mock_get_by_email, mock_register, client, admin_user):
        """Test successful user creation by admin."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        mock_get_by_email.return_value = None  # Email not taken
        mock_get_by_username.return_value = None  # Username not taken
        
        new_user = User()
        new_user.id = uuid4()
        new_user.email = "newuser@example.com"
        new_user.username = "newuser"
        
        mock_register.return_value = (True, "User created", new_user)
        
        try:
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "password": "temppassword123",
                    "first_name": "New",
                    "last_name": "User",
                    "role": "user",
                    "require_password_change": True,
                    "send_invitation_email": True
                },
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["message"] == "User created successfully"
            assert data["user_id"] == str(new_user.id)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.get_by_email')
    def test_create_user_email_exists(self, mock_get_by_email, client, admin_user):
        """Test user creation with existing email."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        mock_get_by_email.return_value = User()  # Email already exists
        
        try:
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "existing@example.com",
                    "username": "newuser",
                    "password": "temppassword123",
                    "first_name": "New",
                    "last_name": "User"
                },
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Email already registered" in response.json()["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.list_users_with_filters')
    def test_list_users(self, mock_list_users, client, admin_user):
        """Test listing users with pagination."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        users = []
        for i in range(5):
            user = User()
            user.id = uuid4()
            user.email = f"user{i}@example.com"
            user.username = f"user{i}"
            user.first_name = f"User{i}"
            user.last_name = "Test"
            user.is_active = True
            user.email_verified = True
            user.role = UserRole.USER
            user.created_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()
            users.append(user)
        
        mock_list_users.return_value = (users, 5)
        
        try:
            response = client.get(
                "/api/admin/users?skip=0&limit=10",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 5
            assert len(data["users"]) == 5
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.get_by_id')
    def test_get_user_by_admin(self, mock_get_by_id, client, admin_user):
        """Test getting user by ID."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        target_user = User()
        target_user.id = uuid4()
        target_user.email = "target@example.com"
        target_user.username = "target"
        target_user.first_name = "Target"
        target_user.last_name = "User"
        target_user.is_active = True
        target_user.email_verified = True
        target_user.role = UserRole.USER
        target_user.created_at = datetime.utcnow()
        target_user.updated_at = datetime.utcnow()
        
        mock_get_by_id.return_value = target_user
        
        try:
            response = client.get(
                f"/api/admin/users/{target_user.id}",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["email"] == target_user.email
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.get_by_id')
    def test_get_user_not_found(self, mock_get_by_id, client, admin_user):
        """Test getting non-existent user."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        mock_get_by_id.return_value = None
        
        try:
            response = client.get(
                f"/api/admin/users/{uuid4()}",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in response.json()["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.activate_user')
    def test_activate_user(self, mock_activate, client, admin_user):
        """Test user activation."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        mock_activate.return_value = (True, "User activated successfully")
        
        user_id = uuid4()
        
        try:
            response = client.put(
                f"/api/admin/users/{user_id}/activate",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "User activated successfully"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('app.modules.auth.services.user_service.UserService.deactivate_user')
    def test_deactivate_user(self, mock_deactivate, client, admin_user):
        """Test user deactivation."""
        # Override the base dependencies to return our admin user
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_active_user] = lambda: admin_user
        app.dependency_overrides[get_current_verified_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user
        app.dependency_overrides[require_authentication] = lambda: admin_user
        
        mock_deactivate.return_value = (True, "User deactivated successfully")
        
        user_id = uuid4()
        
        try:
            response = client.put(
                f"/api/admin/users/{user_id}/deactivate",
                headers={"Authorization": "Bearer admin_token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "User deactivated successfully"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear() 