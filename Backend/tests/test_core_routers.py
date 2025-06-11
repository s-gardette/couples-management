"""
Tests for core routers.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.modules.auth.dependencies import require_authentication
from app.database import get_db


class TestHealthRouter:
    """Test cases for health check router."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        # Override the authentication dependency for health checks
        def mock_require_authentication():
            return True
        
        app.dependency_overrides[require_authentication] = mock_require_authentication
        client = TestClient(app)
        yield client
        # Clean up
        app.dependency_overrides.clear()

    def test_health_check_basic(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    def test_health_check_detailed_success(self, client):
        """Test detailed health check with successful database connection."""
        # Mock successful database connection
        mock_session = Mock()
        mock_result = Mock()
        mock_session.execute.return_value = mock_result
        mock_result.fetchone.return_value = (1,)
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/detailed")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert "app_name" in data
            assert "version" in data
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]

    def test_health_check_detailed_db_failure(self, client):
        """Test detailed health check with database connection failure."""
        # Mock database session that fails when execute is called
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database connection failed")
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/detailed")
            
            assert response.status_code == status.HTTP_200_OK  # Returns 200 but with degraded status
            data = response.json()
            assert data["status"] == "degraded"
            assert "components" in data
            assert "database" in data["components"]
            assert "Database connection failed" in str(data["components"]["database"]["error"])
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]

    def test_health_check_detailed_db_query_failure(self, client):
        """Test detailed health check with database query failure."""
        # Mock database session but query failure
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Query failed")
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/detailed")
            
            assert response.status_code == status.HTTP_200_OK  # Returns 200 but with degraded status
            data = response.json()
            assert data["status"] == "degraded"
            assert "components" in data
            assert "database" in data["components"]
            assert "Query failed" in str(data["components"]["database"]["error"])
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]

    def test_health_check_liveness(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_readiness_success(self, client):
        """Test readiness probe with successful database connection."""
        # Mock successful database connection
        mock_session = Mock()
        mock_result = Mock()
        mock_session.execute.return_value = mock_result
        mock_result.fetchone.return_value = (1,)
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/db")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]

    def test_health_check_readiness_failure(self, client):
        """Test readiness probe with database connection failure."""
        # Mock database session that fails when execute is called
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database connection failed")
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/db")
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()["detail"]  # Error details are in the detail field
            assert data["status"] == "unhealthy"
            assert data["database"] == "disconnected"
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]

    def test_health_check_with_app_info(self, client):
        """Test health check with application information."""
        response = client.get("/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_response_format(self, client):
        """Test that health check response has correct format."""
        response = client.get("/health/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Check required fields that actually exist
        required_fields = ["status", "app_name", "version", "environment"]
        for field in required_fields:
            assert field in data

    def test_health_check_detailed_response_format(self, client):
        """Test that detailed health check response has correct format."""
        # Mock successful database connection
        mock_session = Mock()
        mock_result = Mock()
        mock_session.execute.return_value = mock_result
        mock_result.fetchone.return_value = (1,)
        
        def mock_get_db():
            return mock_session
        
        app.dependency_overrides[get_db] = mock_get_db
        
        try:
            response = client.get("/health/detailed")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Check required fields that actually exist
            required_fields = ["status", "app_name", "version", "environment", "components"]
            for field in required_fields:
                assert field in data
            
            # Check components section
            assert isinstance(data["components"], dict)
            assert "database" in data["components"]
        finally:
            # Clean up the override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db] 