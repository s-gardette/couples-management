"""
Tests for the main application.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

client = TestClient(app)
settings = get_settings()


def test_root_endpoint_redirects_to_login():
    """Test the root endpoint redirects to login when not authenticated."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_health_check_requires_auth():
    """Test the health check endpoint is publicly accessible (no auth required)."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data
    assert "version" in data


def test_access_restricted_page():
    """Test the access restricted page is publicly accessible."""
    response = client.get("/access-restricted")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Access Restricted" in response.text
    assert settings.admin_contact_email in response.text


def test_static_files():
    """Test that static files are served correctly."""
    response = client.get("/static/css/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_app_info():
    """Test that the app has correct configuration."""
    assert app.title == "Household Management App"
    assert app.version == "0.1.0"


def test_login_page_accessible():
    """Test the login page is publicly accessible."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sign in to your account" in response.text
