"""
Comprehensive tests for the health router endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.routers.health import router
from app.database import get_db


class TestHealthRouter:
    """Test cases for health router endpoints."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        # Create a fresh test app for each test
        self.app = FastAPI()
        self.app.include_router(router, prefix="/health")
        self.client = TestClient(self.app)

    def test_basic_health_check(self):
        """Test basic health check endpoint."""
        with patch('app.core.routers.health.settings') as mock_settings:
            mock_settings.app_name = "Test App"
            mock_settings.app_version = "1.0.0"
            mock_settings.environment = "test"
            
            response = self.client.get("/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["app_name"] == "Test App"
            assert data["version"] == "1.0.0"
            assert data["environment"] == "test"

    def test_database_health_check_success(self):
        """Test successful database health check."""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        
        # Override the dependency
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            response = self.client.get("/health/db")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert data["message"] == "Database connection successful"
        finally:
            # Clean up the override
            self.app.dependency_overrides.clear()

    def test_database_health_check_failure(self):
        """Test database health check with connection failure."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = SQLAlchemyError("Connection failed")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            response = self.client.get("/health/db")
            
            assert response.status_code == 503
            data = response.json()
            assert "status" in data["detail"]
            assert data["detail"]["status"] == "unhealthy"
            assert data["detail"]["database"] == "disconnected"
            assert "Connection failed" in data["detail"]["error"]
        finally:
            self.app.dependency_overrides.clear()

    def test_database_health_check_generic_exception(self):
        """Test database health check with generic exception."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = Exception("Generic error")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            response = self.client.get("/health/db")
            
            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["status"] == "unhealthy"
            assert "Generic error" in data["detail"]["error"]
        finally:
            self.app.dependency_overrides.clear()

    def test_detailed_health_check_all_healthy(self):
        """Test detailed health check with all components healthy."""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.app_version = "1.0.0"
                mock_settings.environment = "test"
                
                response = self.client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["app_name"] == "Test App"
                assert data["version"] == "1.0.0"
                assert data["environment"] == "test"
                assert "components" in data
                assert data["components"]["database"]["status"] == "healthy"
                assert data["components"]["database"]["message"] == "Connected"
        finally:
            self.app.dependency_overrides.clear()

    def test_detailed_health_check_database_unhealthy(self):
        """Test detailed health check with database unhealthy."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = SQLAlchemyError("Database connection failed")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.app_version = "1.0.0"
                mock_settings.environment = "test"
                
                response = self.client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["components"]["database"]["status"] == "unhealthy"
                assert "Database connection failed" in data["components"]["database"]["error"]
        finally:
            self.app.dependency_overrides.clear()

    def test_detailed_health_check_database_generic_exception(self):
        """Test detailed health check with database generic exception."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = Exception("Generic database error")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.app_version = "1.0.0"
                mock_settings.environment = "test"
                
                response = self.client.get("/health/detailed")
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["components"]["database"]["status"] == "unhealthy"
                assert "Generic database error" in data["components"]["database"]["error"]
        finally:
            self.app.dependency_overrides.clear()


class TestHealthRouterIntegration:
    """Integration tests for health router."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        self.app = FastAPI()
        self.app.include_router(router, prefix="/health")
        self.client = TestClient(self.app)

    def test_health_endpoints_response_format(self):
        """Test that all health endpoints return proper response format."""
        # Test basic health check response format
        with patch('app.core.routers.health.settings') as mock_settings:
            mock_settings.app_name = "Test App"
            mock_settings.app_version = "1.0.0"
            mock_settings.environment = "test"
            
            response = self.client.get("/health/")
            data = response.json()
            
            required_fields = ["status", "app_name", "version", "environment"]
            for field in required_fields:
                assert field in data

    def test_database_health_check_sql_execution(self):
        """Test that database health check executes SQL properly."""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.text') as mock_text:
                mock_text.return_value = "SELECT 1"
                
                response = self.client.get("/health/db")
                
                # Verify SQL was executed
                mock_db.execute.assert_called_once()
                mock_result.fetchone.assert_called_once()
        finally:
            self.app.dependency_overrides.clear()

    def test_detailed_health_check_components_structure(self):
        """Test detailed health check components structure."""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_db.execute.return_value = mock_result
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.app_version = "1.0.0"
                mock_settings.environment = "test"
                
                response = self.client.get("/health/detailed")
                data = response.json()
                
                # Check overall structure
                assert "components" in data
                assert isinstance(data["components"], dict)
                
                # Check database component structure
                db_component = data["components"]["database"]
                assert "status" in db_component
                assert "message" in db_component
                assert db_component["status"] in ["healthy", "unhealthy"]
        finally:
            self.app.dependency_overrides.clear()


class TestHealthRouterErrorHandling:
    """Test error handling in health router."""

    def setup_method(self):
        """Set up test fixtures for each test."""
        self.app = FastAPI()
        self.app.include_router(router, prefix="/health")
        self.client = TestClient(self.app)

    def test_database_health_check_connection_timeout(self):
        """Test database health check with connection timeout."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = TimeoutError("Connection timeout")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            response = self.client.get("/health/db")
            
            assert response.status_code == 503
            data = response.json()
            assert "Connection timeout" in data["detail"]["error"]
        finally:
            self.app.dependency_overrides.clear()

    def test_detailed_health_check_partial_failure(self):
        """Test detailed health check handles partial component failures gracefully."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = ConnectionError("Network error")
        
        def override_get_db():
            return mock_db
        
        self.app.dependency_overrides[get_db] = override_get_db
        
        try:
            with patch('app.core.routers.health.settings') as mock_settings:
                mock_settings.app_name = "Test App"
                mock_settings.app_version = "1.0.0"
                mock_settings.environment = "test"
                
                response = self.client.get("/health/detailed")
                
                # Should still return 200 but with degraded status
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["components"]["database"]["status"] == "unhealthy"
        finally:
            self.app.dependency_overrides.clear() 