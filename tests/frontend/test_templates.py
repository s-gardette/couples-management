"""
Frontend template tests for all UI endpoints.

Tests that all frontend routes return proper 200 responses and contain expected content.
"""

import pytest
from fastapi.testclient import TestClient
from app.modules.auth.models.user import User
from sqlalchemy.orm import Session


class TestPublicTemplates:
    """Test public templates that don't require authentication."""
    
    def test_login_page(self, frontend_client: TestClient):
        """Test login page returns 200."""
        response = frontend_client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower() or "sign in" in response.text.lower()
    
    def test_access_restricted_page(self, frontend_client: TestClient):
        """Test access restricted page returns 200."""
        response = frontend_client.get("/access-restricted")
        assert response.status_code == 200
        assert "restricted" in response.text.lower() or "access" in response.text.lower()


class TestAuthenticatedTemplates:
    """Test templates that require authentication."""
    
    def test_root_redirect(self, authenticated_frontend_client: TestClient):
        """Test root endpoint redirects properly."""
        response = authenticated_frontend_client.get("/", allow_redirects=False)
        # Should redirect to onboarding or dashboard
        assert response.status_code in [200, 302, 307]
    
    def test_expenses_dashboard(self, authenticated_frontend_client: TestClient):
        """Test expenses dashboard page."""
        response = authenticated_frontend_client.get("/expenses/dashboard")
        assert response.status_code in [200, 302]  # 302 if redirecting to household-specific
    
    def test_expenses_list(self, authenticated_frontend_client: TestClient):
        """Test expenses list page."""
        response = authenticated_frontend_client.get("/expenses/list")
        assert response.status_code in [200, 302]  # 302 if redirecting to household-specific
    
    def test_expenses_redirect(self, authenticated_frontend_client: TestClient):
        """Test expenses redirect endpoint."""
        response = authenticated_frontend_client.get("/expenses", allow_redirects=False)
        assert response.status_code in [200, 302, 307]
    
    def test_households_page(self, authenticated_frontend_client: TestClient):
        """Test households management page."""
        response = authenticated_frontend_client.get("/households")
        assert response.status_code == 200
        assert "household" in response.text.lower()
    
    def test_households_create_form(self, authenticated_frontend_client: TestClient):
        """Test household creation form page."""
        response = authenticated_frontend_client.get("/households/create")
        assert response.status_code == 200
        assert "create" in response.text.lower() or "form" in response.text.lower()
    
    def test_global_analytics(self, authenticated_frontend_client: TestClient):
        """Test global analytics page."""
        response = authenticated_frontend_client.get("/analytics")
        assert response.status_code == 200
        assert "analytics" in response.text.lower() or "chart" in response.text.lower()
    
    def test_expense_create_form_redirect(self, authenticated_frontend_client: TestClient):
        """Test expense creation form redirect."""
        response = authenticated_frontend_client.get("/expenses/create", allow_redirects=False)
        assert response.status_code in [200, 302, 307]
    
    def test_expense_create_modal(self, authenticated_frontend_client: TestClient):
        """Test expense creation modal content."""
        response = authenticated_frontend_client.get("/expenses/create_modal")
        assert response.status_code in [200, 302]  # 302 if redirecting
    
    def test_budgets_placeholder_page(self, authenticated_frontend_client: TestClient):
        """Test budgets list page (placeholder)."""
        response = authenticated_frontend_client.get("/budgets")
        assert response.status_code == 200
        assert "budget" in response.text.lower()
    
    def test_budgets_create_placeholder(self, authenticated_frontend_client: TestClient):
        """Test budget creation page (placeholder)."""
        response = authenticated_frontend_client.get("/budgets/create")
        assert response.status_code == 200
        assert "budget" in response.text.lower() or "create" in response.text.lower()
    
    def test_reports_placeholder_page(self, authenticated_frontend_client: TestClient):
        """Test reports page (placeholder)."""
        response = authenticated_frontend_client.get("/reports")
        assert response.status_code == 200
        assert "report" in response.text.lower()
    
    def test_settings_placeholder_page(self, authenticated_frontend_client: TestClient):
        """Test settings page (placeholder)."""
        response = authenticated_frontend_client.get("/settings")
        assert response.status_code == 200
        assert "setting" in response.text.lower()


class TestOnboardingTemplates:
    """Test onboarding flow templates."""
    
    def test_onboarding_welcome(self, authenticated_frontend_client: TestClient):
        """Test onboarding welcome page."""
        response = authenticated_frontend_client.get("/onboarding")
        assert response.status_code == 200
        assert "onboarding" in response.text.lower() or "welcome" in response.text.lower()
    
    def test_onboarding_create_household(self, authenticated_frontend_client: TestClient):
        """Test onboarding create household page."""
        response = authenticated_frontend_client.get("/onboarding/create-household")
        assert response.status_code == 200
        assert "household" in response.text.lower() and "create" in response.text.lower()
    
    def test_onboarding_add_members(self, authenticated_frontend_client: TestClient):
        """Test onboarding add members page."""
        response = authenticated_frontend_client.get("/onboarding/add-members")
        assert response.status_code == 200
        assert "member" in response.text.lower() or "add" in response.text.lower()
    
    def test_onboarding_join_household(self, authenticated_frontend_client: TestClient):
        """Test onboarding join household page."""
        response = authenticated_frontend_client.get("/onboarding/join-household")
        assert response.status_code == 200
        assert "join" in response.text.lower() and "household" in response.text.lower()
    
    def test_onboarding_complete(self, authenticated_frontend_client: TestClient):
        """Test onboarding completion page."""
        response = authenticated_frontend_client.get("/onboarding/complete")
        assert response.status_code == 200
        assert "complete" in response.text.lower() or "finish" in response.text.lower()


class TestHouseholdSpecificTemplates:
    """Test household-specific templates."""
    
    def test_household_detail_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test household detail page with actual data."""
        household = test_household_with_expenses["household"]
        response = authenticated_frontend_client.get(f"/households/{household.id}")
        assert response.status_code == 200
        assert household.name in response.text
    
    def test_household_detail_invalid_id(self, authenticated_frontend_client: TestClient, mock_expense_id):
        """Test household detail page with invalid ID."""
        response = authenticated_frontend_client.get(f"/households/{mock_expense_id}")
        assert response.status_code in [404, 403]  # Not found or forbidden
    
    def test_household_expenses_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test household expenses page with actual data."""
        household = test_household_with_expenses["household"]
        response = authenticated_frontend_client.get(f"/households/{household.id}/expenses")
        assert response.status_code == 200
        assert "expense" in response.text.lower()
    
    def test_household_analytics_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test household analytics page with actual data."""
        household = test_household_with_expenses["household"]
        response = authenticated_frontend_client.get(f"/households/{household.id}/analytics")
        assert response.status_code == 200
        assert "analytics" in response.text.lower() or "chart" in response.text.lower()
    
    def test_household_expense_create_form_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test household-specific expense creation form."""
        household = test_household_with_expenses["household"]
        response = authenticated_frontend_client.get(f"/households/{household.id}/expenses/create")
        assert response.status_code == 200
        assert "create" in response.text.lower() and "expense" in response.text.lower()


class TestExpenseDetailTemplates:
    """Test expense detail templates."""
    
    def test_expense_detail_page_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test expense detail full page with actual data."""
        expense = test_household_with_expenses["expenses"][0]
        response = authenticated_frontend_client.get(f"/expenses/{expense.id}")
        assert response.status_code == 200
        assert expense.title in response.text
    
    def test_expense_detail_page_invalid_id(self, authenticated_frontend_client: TestClient, mock_expense_id):
        """Test expense detail page with invalid ID."""
        response = authenticated_frontend_client.get(f"/expenses/{mock_expense_id}")
        assert response.status_code in [404, 403]  # Not found or forbidden


class TestPartialTemplates:
    """Test HTMX partial templates."""
    
    def test_households_list_partial(self, authenticated_frontend_client: TestClient):
        """Test households list partial."""
        response = authenticated_frontend_client.get("/partials/households/list")
        assert response.status_code == 200
        # Should contain HTML but not full page structure
        assert "<div" in response.text or "<ul" in response.text
    
    def test_household_create_partial(self, authenticated_frontend_client: TestClient):
        """Test household create form partial."""
        response = authenticated_frontend_client.get("/partials/households/create")
        assert response.status_code == 200
        assert "<form" in response.text or "create" in response.text.lower()
    
    def test_household_join_partial(self, authenticated_frontend_client: TestClient):
        """Test household join form partial."""
        response = authenticated_frontend_client.get("/partials/households/join")
        assert response.status_code == 200
        assert "<form" in response.text or "join" in response.text.lower()
    
    def test_expenses_recent_partial(self, authenticated_frontend_client: TestClient):
        """Test expenses recent partial (unified endpoint)."""
        response = authenticated_frontend_client.get("/partials/expenses/recent")
        assert response.status_code == 200
        assert "<div" in response.text or "expense" in response.text.lower()
    
    def test_expenses_recent_partial_with_params(self, authenticated_frontend_client: TestClient):
        """Test expenses recent partial with query parameters."""
        response = authenticated_frontend_client.get("/partials/expenses/recent?view_type=list&limit=5")
        assert response.status_code == 200
        assert "<div" in response.text or "expense" in response.text.lower()
    
    def test_expense_create_partial(self, authenticated_frontend_client: TestClient):
        """Test expense create form partial."""
        response = authenticated_frontend_client.get("/partials/expenses/create")
        assert response.status_code in [200, 302]  # 302 if redirecting to household-specific
    
    def test_expense_details_partial_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test expense details modal partial with actual data."""
        expense = test_household_with_expenses["expenses"][0]
        response = authenticated_frontend_client.get(f"/partials/expenses/{expense.id}/details")
        assert response.status_code == 200
        assert expense.title in response.text
        # Should be a modal partial, not full page
        assert "<div" in response.text
    
    def test_expense_details_partial_invalid_id(self, authenticated_frontend_client: TestClient, mock_expense_id):
        """Test expense details partial with invalid ID."""
        response = authenticated_frontend_client.get(f"/partials/expenses/{mock_expense_id}/details")
        assert response.status_code in [404, 403]  # Not found or forbidden


class TestTemplateContentQuality:
    """Test template content quality and structure."""
    
    def test_households_page_structure(self, authenticated_frontend_client: TestClient, template_utils):
        """Test households page has proper HTML structure."""
        response = authenticated_frontend_client.get("/households")
        template_utils.assert_html_structure(
            response,
            expected_elements=["<div", "<button", "<a"]
        )
    
    def test_expense_detail_page_structure(self, authenticated_frontend_client: TestClient, test_household_with_expenses, template_utils):
        """Test expense detail page has proper HTML structure."""
        expense = test_household_with_expenses["expenses"][0]
        response = authenticated_frontend_client.get(f"/expenses/{expense.id}")
        template_utils.assert_html_structure(
            response,
            expected_elements=["<div", "<h1", "<p"]
        )
        template_utils.assert_template_response(
            response,
            should_contain=[expense.title, "Expense Details"]
        )
    
    def test_household_detail_structure(self, authenticated_frontend_client: TestClient, test_household_with_expenses, template_utils):
        """Test household detail page has proper structure."""
        household = test_household_with_expenses["household"]
        response = authenticated_frontend_client.get(f"/households/{household.id}")
        template_utils.assert_html_structure(
            response,
            expected_elements=["<div", "<h1", "<section"]
        )
        template_utils.assert_template_response(
            response,
            should_contain=[household.name]
        )


class TestErrorHandling:
    """Test error handling in templates."""
    
    def test_nonexistent_household_detail(self, authenticated_frontend_client: TestClient):
        """Test accessing non-existent household details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_frontend_client.get(f"/households/{fake_id}")
        assert response.status_code in [404, 403]
    
    def test_invalid_household_id_format(self, authenticated_frontend_client: TestClient):
        """Test accessing household with invalid ID format."""
        response = authenticated_frontend_client.get("/households/invalid-id")
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_nonexistent_expense_detail(self, authenticated_frontend_client: TestClient):
        """Test accessing non-existent expense details."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = authenticated_frontend_client.get(f"/expenses/{fake_id}")
        assert response.status_code in [404, 403]
    
    def test_invalid_expense_id_format(self, authenticated_frontend_client: TestClient):
        """Test accessing expense with invalid ID format."""
        response = authenticated_frontend_client.get("/expenses/invalid-id")
        assert response.status_code in [400, 422]  # Bad request or validation error


@pytest.mark.integration
class TestFullUserJourney:
    """Integration tests for complete user journeys."""
    
    def test_onboarding_to_expense_creation_flow(self, authenticated_frontend_client: TestClient):
        """Test complete flow from onboarding to expense creation."""
        # Start with onboarding
        response = authenticated_frontend_client.get("/onboarding")
        assert response.status_code == 200
        
        # Check household creation
        response = authenticated_frontend_client.get("/onboarding/create-household")
        assert response.status_code == 200
        
        # Check households list
        response = authenticated_frontend_client.get("/households")
        assert response.status_code == 200
    
    def test_expense_management_flow_with_data(self, authenticated_frontend_client: TestClient, test_household_with_expenses):
        """Test expense management flow with actual data."""
        household = test_household_with_expenses["household"]
        expense = test_household_with_expenses["expenses"][0]
        
        # Household expenses page
        response = authenticated_frontend_client.get(f"/households/{household.id}/expenses")
        assert response.status_code == 200
        
        # Expense details page
        response = authenticated_frontend_client.get(f"/expenses/{expense.id}")
        assert response.status_code == 200
        
        # Expense details partial (modal)
        response = authenticated_frontend_client.get(f"/partials/expenses/{expense.id}/details")
        assert response.status_code == 200 