"""
Test package for the Household Management App.

This package contains all tests for the application, including:
- Main application tests
- Module-specific tests (auth, expenses, etc.)
- Integration tests
"""

# Import all test modules to ensure they're discovered by pytest
from . import test_main
from . import test_jwt_system
from . import test_password_security

__all__ = [
    "test_main",
    "test_jwt_system", 
    "test_password_security"
] 