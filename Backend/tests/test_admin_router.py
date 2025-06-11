"""
Comprehensive tests for the admin router endpoints.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.modules.auth.routers.admin import router
from app.modules.auth.models.user import User, UserRole
from app.modules.auth.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserInviteRequest,
    AdminBulkUserImportRequest
)
from app.modules.auth.dependencies import get_current_admin_user
from app.database import get_db


# Create a test app
app = FastAPI()
app.include_router(router)

client = TestClient(app)


def create_mock_user(user_id=None, email="test@example.com", username="testuser", role=UserRole.USER):
    """Helper function to create a properly mocked User object."""
    if user_id is None:
        user_id = uuid4()
    
    user = User(
        id=user_id,
        email=email,
        username=username,
        role=role,
        email_verified=True,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    # Add mock methods
    user.set_created_by_admin = Mock()
    user.require_password_change = Mock()
    user.verify_email = Mock()
    user.activate = Mock()
    return user


class TestAdminRouter:
    """Test cases for admin router endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.admin_user = create_mock_user(
            user_id=uuid4(),
            email="admin@example.com",
            username="admin",
            role=UserRole.ADMIN
        )
        self.test_user_id = uuid4()

    def test_create_user_by_admin_success(self):
        """Test successful user creation by admin."""
        # Mock database
        mock_db = Mock(spec=Session)
        
        # Mock services
        mock_user_service_instance = Mock()
        mock_user_service_instance.get_by_email = AsyncMock(return_value=None)
        mock_user_service_instance.get_by_username = AsyncMock(return_value=None)
        
        mock_auth_service_instance = Mock()
        new_user = create_mock_user(
            user_id=self.test_user_id,
            email="newuser@example.com",
            username="newuser",
            role=UserRole.USER
        )
        
        mock_auth_service_instance.register_user = AsyncMock(
            return_value=(True, "Success", new_user)
        )
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        # Patch the service classes
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service, \
             patch('app.modules.auth.routers.admin.AuthService') as mock_auth_service:
            
            mock_user_service.return_value = mock_user_service_instance
            mock_auth_service.return_value = mock_auth_service_instance
            
            # Test data
            user_data = {
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": "user",
                "require_password_change": False,
                "send_temporary_password": False,
                "send_invitation_email": True
            }
            
            response = client.post("/admin/users", json=user_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["message"] == "User created successfully"
            assert data["user_id"] == str(self.test_user_id)
            assert data["invitation_sent"] is True
        
        # Clean up dependency overrides
        app.dependency_overrides.clear()

    def test_create_user_email_exists(self):
        """Test user creation when email already exists."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        existing_user = create_mock_user(email="existing@example.com")
        mock_user_service_instance.get_by_email = AsyncMock(return_value=existing_user)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            user_data = {
                "email": "existing@example.com",
                "username": "newuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User"
            }
            
            response = client.post("/admin/users", json=user_data)
            
            assert response.status_code == 400
            assert "Email already registered" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_create_user_username_exists(self):
        """Test user creation when username already exists."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.get_by_email = AsyncMock(return_value=None)
        existing_user = create_mock_user(username="existinguser")
        mock_user_service_instance.get_by_username = AsyncMock(return_value=existing_user)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            user_data = {
                "email": "new@example.com",
                "username": "existinguser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User"
            }
            
            response = client.post("/admin/users", json=user_data)
            
            assert response.status_code == 400
            assert "Username already taken" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_create_user_registration_failure(self):
        """Test user creation when registration fails."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.get_by_email = AsyncMock(return_value=None)
        mock_user_service_instance.get_by_username = AsyncMock(return_value=None)
        
        mock_auth_service_instance = Mock()
        mock_auth_service_instance.register_user = AsyncMock(
            return_value=(False, "Registration failed", None)
        )
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service, \
             patch('app.modules.auth.routers.admin.AuthService') as mock_auth_service:
            
            mock_user_service.return_value = mock_user_service_instance
            mock_auth_service.return_value = mock_auth_service_instance
            
            user_data = {
                "email": "new@example.com",
                "username": "newuser",
                "password": "password123",
                "first_name": "New",
                "last_name": "User"
            }
            
            response = client.post("/admin/users", json=user_data)
            
            assert response.status_code == 400
            assert "Registration failed" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_list_users_success(self):
        """Test successful user listing."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        users = [
            create_mock_user(user_id=uuid4(), email="user1@example.com", username="user1"),
            create_mock_user(user_id=uuid4(), email="user2@example.com", username="user2")
        ]
        mock_user_service_instance.list_users_with_filters = AsyncMock(
            return_value=(users, 2)
        )
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.get("/admin/users?skip=0&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["users"]) == 2
            assert data["skip"] == 0
            assert data["limit"] == 10
        
        app.dependency_overrides.clear()

    def test_list_users_with_filters(self):
        """Test user listing with filters."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        users = [create_mock_user(user_id=uuid4(), email="admin@example.com", username="admin")]
        mock_user_service_instance.list_users_with_filters = AsyncMock(
            return_value=(users, 1)
        )
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.get("/admin/users?role=admin&is_active=true&search=admin")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
        
        app.dependency_overrides.clear()

    def test_get_user_by_admin_success(self):
        """Test successful user retrieval by admin."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        user = create_mock_user(
            user_id=self.test_user_id,
            email="user@example.com",
            username="user"
        )
        mock_user_service_instance.get_by_id = AsyncMock(return_value=user)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.get(f"/admin/users/{self.test_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "user@example.com"
            assert data["username"] == "user"
        
        app.dependency_overrides.clear()

    def test_get_user_by_admin_not_found(self):
        """Test user retrieval when user not found."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.get_by_id = AsyncMock(return_value=None)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.get(f"/admin/users/{self.test_user_id}")
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_update_user_by_admin_success(self):
        """Test successful user update by admin."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        updated_user = create_mock_user(
            user_id=self.test_user_id,
            email="updated@example.com",
            username="updated"
        )
        mock_user_service_instance.update = AsyncMock(return_value=updated_user)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            update_data = {
                "email": "updated@example.com",
                "username": "updated"
            }
            
            response = client.put(f"/admin/users/{self.test_user_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "updated@example.com"
            assert data["username"] == "updated"
        
        app.dependency_overrides.clear()

    def test_update_user_by_admin_not_found(self):
        """Test user update when user not found."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.update = AsyncMock(return_value=None)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            update_data = {"email": "updated@example.com"}
            
            response = client.put(f"/admin/users/{self.test_user_id}", json=update_data)
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_activate_user_success(self):
        """Test successful user activation."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.activate_user = AsyncMock(return_value=True)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.put(f"/admin/users/{self.test_user_id}/activate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "User activated successfully"
        
        app.dependency_overrides.clear()

    def test_activate_user_not_found(self):
        """Test user activation when user not found."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.activate_user = AsyncMock(return_value=False)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.put(f"/admin/users/{self.test_user_id}/activate")
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
        
        app.dependency_overrides.clear()

    def test_deactivate_user_success(self):
        """Test successful user deactivation."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.deactivate_user = AsyncMock(return_value=True)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.put(f"/admin/users/{self.test_user_id}/deactivate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "User deactivated successfully"
        
        app.dependency_overrides.clear()

    def test_delete_user_success(self):
        """Test successful user deletion."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.delete = AsyncMock(return_value=True)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.delete(f"/admin/users/{self.test_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "User deleted successfully"
        
        app.dependency_overrides.clear()


class TestAdminRouterAdvanced:
    """Advanced test cases for admin router."""

    def setup_method(self):
        """Set up test fixtures."""
        self.admin_user = create_mock_user(
            user_id=uuid4(),
            email="admin@example.com",
            username="admin",
            role=UserRole.ADMIN
        )
        self.test_user_id = uuid4()

    def test_invite_user_success(self):
        """Test successful user invitation."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.invite_user = AsyncMock(return_value=(True, "User invitation sent successfully"))
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            invite_data = {
                "email": "invite@example.com",
                "role": "user",
                "send_email": True
            }
            
            response = client.post("/admin/users/invite", json=invite_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "User invitation sent successfully"
        
        app.dependency_overrides.clear()

    def test_bulk_import_users_success(self):
        """Test successful bulk user import."""
        mock_db = Mock(spec=Session)
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        import_data = {
            "users_data": [
                {
                    "email": "user1@example.com", 
                    "username": "user1",
                    "first_name": "User",
                    "last_name": "One"
                },
                {
                    "email": "user2@example.com", 
                    "username": "user2",
                    "first_name": "User",
                    "last_name": "Two"
                }
            ],
            "send_invitations": True
        }
        
        response = client.post("/admin/users/bulk-import", json=import_data)
        
        assert response.status_code == 200
        data = response.json()
        # The endpoint is currently a placeholder that returns hardcoded values
        assert data["message"] == "Bulk import completed"
        assert data["imported_count"] == 0  # Placeholder returns 0
        assert data["failed_count"] == 0
        assert data["errors"] == []
        
        app.dependency_overrides.clear()

    def test_get_user_stats_success(self):
        """Test successful user statistics retrieval."""
        mock_db = Mock(spec=Session)
        
        mock_user_service_instance = Mock()
        mock_user_service_instance.get_user_statistics = AsyncMock(
            return_value={
                "total_users": 100,
                "active_users": 85,
                "inactive_users": 15,
                "verified_users": 90,
                "unverified_users": 10,
                "admin_users": 5,
                "regular_users": 95,
                "users_created_today": 3,
                "users_created_this_week": 12,
                "users_created_this_month": 25
            }
        )
        
        # Override dependencies
        def override_get_current_admin_user():
            return self.admin_user
        
        def override_get_db():
            return mock_db
        
        app.dependency_overrides[get_current_admin_user] = override_get_current_admin_user
        app.dependency_overrides[get_db] = override_get_db
        
        with patch('app.modules.auth.routers.admin.UserService') as mock_user_service:
            mock_user_service.return_value = mock_user_service_instance
            
            response = client.get("/admin/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_users"] == 100
            assert data["active_users"] == 85
            assert data["admin_users"] == 5
        
        app.dependency_overrides.clear() 