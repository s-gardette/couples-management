"""
Frontend test configuration and constants.
"""

import os
from typing import Dict, List


class FrontendTestConfig:
    """Configuration for frontend tests."""
    
    # Base URLs for testing
    BASE_URL = "http://localhost:8000"
    
    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS: List[str] = [
        "/login",
        "/access-restricted",
    ]
    
    # Authenticated endpoints that require login
    AUTHENTICATED_ENDPOINTS: List[str] = [
        "/",
        "/expenses",
        "/expenses/dashboard", 
        "/expenses/list",
        "/households",
        "/households/create",
        "/analytics",
        "/expenses/create",
        "/expenses/create_modal",
        "/budgets",
        "/budgets/create",
        "/reports", 
        "/settings",
    ]
    
    # Onboarding flow endpoints
    ONBOARDING_ENDPOINTS: List[str] = [
        "/onboarding",
        "/onboarding/create-household",
        "/onboarding/add-members",
        "/onboarding/join-household", 
        "/onboarding/complete",
    ]
    
    # Household-specific endpoints (require household_id parameter)
    HOUSEHOLD_ENDPOINTS: List[str] = [
        "/households/{household_id}",
        "/households/{household_id}/expenses",
        "/households/{household_id}/analytics",
        "/households/{household_id}/expenses/create",
    ]
    
    # Expense-specific endpoints (require expense_id parameter)
    EXPENSE_ENDPOINTS: List[str] = [
        "/expenses/{expense_id}",
    ]
    
    # HTMX partial endpoints
    PARTIAL_ENDPOINTS: List[str] = [
        "/partials/households/list",
        "/partials/households/create", 
        "/partials/households/join",
        "/partials/expenses/recent",
        "/partials/expenses/create",
        "/partials/expenses/{expense_id}/details",
    ]
    
    # Expected status codes for different scenarios
    EXPECTED_STATUS_CODES: Dict[str, List[int]] = {
        "success": [200],
        "redirect": [302, 307],
        "redirect_or_success": [200, 302, 307],
        "auth_required": [401, 403],
        "not_found": [404],
        "validation_error": [400, 422],
        "error": [404, 403, 400, 422],
    }
    
    # Content expectations for different page types
    CONTENT_EXPECTATIONS: Dict[str, List[str]] = {
        "login": ["login", "sign in", "email", "password"],
        "household": ["household", "member", "expense"],
        "expense": ["expense", "amount", "category", "date"],
        "analytics": ["analytics", "chart", "report", "summary"],
        "onboarding": ["onboarding", "welcome", "getting started"],
        "create": ["create", "form", "save", "submit"],
        "list": ["list", "table", "item"],
        "detail": ["detail", "information", "view"],
    }
    
    # HTML structure expectations
    HTML_STRUCTURE_EXPECTATIONS: Dict[str, List[str]] = {
        "full_page": ["<!DOCTYPE html>", "<html", "<head", "<body"],
        "partial": ["<div", "<section", "<form"],
        "modal": ["<div", "modal", "close"],
        "form": ["<form", "<input", "<button"],
        "list": ["<ul", "<li", "<div"],
        "table": ["<table", "<thead", "<tbody", "<tr", "<td"],
    }
    
    # Test data expectations
    TEST_DATA_REQUIREMENTS: Dict[str, str] = {
        "household_name": "Frontend Test Household",
        "expense_title_prefix": "Frontend Test Expense",
        "category_name": "Frontend Test Category",
        "min_expenses": 3,  # Minimum number of test expenses to create
    }
    
    @classmethod
    def get_full_url(cls, endpoint: str) -> str:
        """Get full URL for an endpoint."""
        return f"{cls.BASE_URL}{endpoint}"
    
    @classmethod
    def get_all_testable_endpoints(cls) -> List[str]:
        """Get all endpoints that should be tested."""
        return (
            cls.PUBLIC_ENDPOINTS + 
            cls.AUTHENTICATED_ENDPOINTS + 
            cls.ONBOARDING_ENDPOINTS +
            cls.PARTIAL_ENDPOINTS
        )
    
    @classmethod
    def get_parameterized_endpoints(cls) -> Dict[str, List[str]]:
        """Get endpoints that require parameters."""
        return {
            "household": cls.HOUSEHOLD_ENDPOINTS,
            "expense": cls.EXPENSE_ENDPOINTS,
        }
    
    @classmethod
    def is_partial_endpoint(cls, endpoint: str) -> bool:
        """Check if endpoint is a partial (HTMX) endpoint."""
        return endpoint.startswith("/partials/")
    
    @classmethod
    def get_expected_content(cls, page_type: str) -> List[str]:
        """Get expected content for a page type."""
        return cls.CONTENT_EXPECTATIONS.get(page_type, [])
    
    @classmethod
    def get_expected_status_codes(cls, scenario: str) -> List[int]:
        """Get expected status codes for a scenario."""
        return cls.EXPECTED_STATUS_CODES.get(scenario, [200])


# Environment-specific settings
TEST_SETTINGS = {
    "AUTHENTICATION_REQUIRED": os.getenv("TEST_AUTH_REQUIRED", "true").lower() == "true",
    "TEST_DB_CLEANUP": os.getenv("TEST_DB_CLEANUP", "true").lower() == "true", 
    "VERBOSE_TESTING": os.getenv("VERBOSE_TESTING", "false").lower() == "true",
    "PARALLEL_TESTING": os.getenv("PARALLEL_TESTING", "false").lower() == "true",
} 