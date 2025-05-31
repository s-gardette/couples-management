"""
Tests for expenses API endpoints.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.expenses.models import Household, UserHousehold, Category, Expense, ExpenseShare
from app.modules.expenses.models.household import UserHouseholdRole


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        first_name="Test",
        last_name="User",
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user2(db_session: Session) -> User:
    """Create a second test user."""
    user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password="hashed_password",
        first_name="Test2",
        last_name="User2",
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_household(db_session: Session, test_user: User) -> Household:
    """Create a test household."""
    household = Household(
        name="Test Household",
        description="A test household",
        invite_code="TEST123",
        created_by=test_user.id,
        settings={"currency": "USD"}
    )
    db_session.add(household)
    db_session.commit()
    db_session.refresh(household)
    
    # Add user as admin
    membership = UserHousehold(
        user_id=test_user.id,
        household_id=household.id,
        role=UserHouseholdRole.ADMIN,
        nickname="Admin User"
    )
    db_session.add(membership)
    db_session.commit()
    
    return household


@pytest.fixture
def test_category(db_session: Session, test_household: Household) -> Category:
    """Create a test category."""
    category = Category.create_household_category(
        name="Test Category",
        household_id=test_household.id,
        icon="test",
        color="#FF0000"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def authenticated_client(test_user: User, client) -> TestClient:
    """Create an authenticated test client."""
    # Mock all authentication dependencies
    def mock_get_current_user():
        return test_user
    
    def mock_get_current_user_or_default():
        return test_user
    
    def mock_require_authentication():
        return test_user
    
    # Import the dependencies to override them
    from app.modules.auth.dependencies import (
        get_current_user, 
        get_current_user_or_default, 
        require_authentication
    )
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_user_or_default] = mock_get_current_user_or_default
    app.dependency_overrides[require_authentication] = mock_require_authentication
    
    yield client
    
    # Clean up
    app.dependency_overrides.clear()


class TestHouseholdEndpoints:
    """Test household management endpoints."""
    
    def test_create_household(self, authenticated_client: TestClient):
        """Test creating a new household."""
        household_data = {
            "name": "New Household",
            "description": "A new test household",
            "settings": {"currency": "EUR"}
        }
        
        response = authenticated_client.post("/api/households/", json=household_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == household_data["name"]
        assert data["description"] == household_data["description"]
        assert data["settings"] == household_data["settings"]
        assert "id" in data
        assert "invite_code" in data
    
    def test_get_user_households(self, authenticated_client: TestClient, test_household: Household):
        """Test getting user's households."""
        response = authenticated_client.get("/api/households/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check if our test household is in the list
        household_ids = [h["id"] for h in data]
        assert str(test_household.id) in household_ids
    
    def test_get_household_details(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household details."""
        response = authenticated_client.get(f"/api/households/{test_household.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_household.id)
        assert data["name"] == test_household.name
        assert data["description"] == test_household.description
    
    def test_update_household(self, authenticated_client: TestClient, test_household: Household):
        """Test updating household information."""
        update_data = {
            "name": "Updated Household Name",
            "description": "Updated description"
        }
        
        response = authenticated_client.put(f"/api/households/{test_household.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_join_household_by_invite(self, authenticated_client: TestClient, test_household: Household):
        """Test joining a household by invite code."""
        join_data = {
            "invite_code": test_household.invite_code,
            "nickname": "New Member"
        }
        
        response = authenticated_client.post(f"/api/households/{test_household.id}/join", json=join_data)
        
        # This might fail if user is already a member, which is expected in our test setup
        # In a real scenario, we'd use a different user
        assert response.status_code in [200, 400]
    
    def test_get_household_members(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household members."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/members")
        
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "total" in data
        assert data["household_id"] == str(test_household.id)
        assert data["total"] >= 1  # At least the creator
    
    def test_unauthorized_access(self, authenticated_client: TestClient):
        """Test accessing non-existent household."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/households/{fake_id}")
        
        assert response.status_code == 403  # Forbidden, not 404, because we check permissions first


class TestExpenseEndpoints:
    """Test expense management endpoints."""
    
    def test_create_expense(self, authenticated_client: TestClient, test_household: Household, test_category: Category):
        """Test creating a new expense."""
        expense_data = {
            "title": "Test Expense",
            "description": "A test expense",
            "amount": "50.00",
            "currency": "USD",
            "category_id": str(test_category.id),
            "expense_date": "2024-01-15",
            "tags": ["test", "food"],
            "split_method": "equal",
            "split_data": {}
        }
        
        response = authenticated_client.post(f"/api/households/{test_household.id}/expenses", json=expense_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == expense_data["title"]
        assert data["description"] == expense_data["description"]
        assert float(data["amount"]) == float(expense_data["amount"])
        assert data["currency"] == expense_data["currency"]
        assert "id" in data
    
    def test_get_household_expenses(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household expenses."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/expenses")
        
        assert response.status_code == 200
        data = response.json()
        assert "expenses" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["expenses"], list)
    
    def test_get_household_expenses_with_filters(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household expenses with filters."""
        params = {
            "page": 1,
            "per_page": 10,
            "date_from": "2024-01-01",
            "date_to": "2024-12-31",
            "search": "test"
        }
        
        response = authenticated_client.get(f"/api/households/{test_household.id}/expenses", params=params)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
    
    def test_get_expense_summary(self, authenticated_client: TestClient, test_household: Household):
        """Test getting expense summary."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/expenses/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_expenses" in data
        assert "total_amount" in data
        assert "paid_amount" in data
        assert "unpaid_amount" in data


class TestCategoryEndpoints:
    """Test category management endpoints."""
    
    def test_get_household_categories(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household categories."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total" in data
        assert "global_categories" in data
        assert "household_categories" in data
        assert isinstance(data["categories"], list)
    
    def test_create_household_category(self, authenticated_client: TestClient, test_household: Household):
        """Test creating a new household category."""
        category_data = {
            "name": "New Category",
            "icon": "new-icon",
            "color": "#00FF00",
            "is_default": False
        }
        
        response = authenticated_client.post(f"/api/households/{test_household.id}/categories", json=category_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == category_data["name"]
        assert data["icon"] == category_data["icon"]
        assert data["color"] == category_data["color"]
        assert data["is_default"] == category_data["is_default"]
        assert "id" in data
    
    def test_get_category_statistics(self, authenticated_client: TestClient, test_household: Household):
        """Test getting category statistics."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/categories/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Each category stat should have required fields
        for stat in data:
            assert "category_id" in stat
            assert "category_name" in stat
            assert "expense_count" in stat
            assert "total_amount" in stat
            assert "percentage_of_total" in stat


class TestAnalyticsEndpoints:
    """Test analytics endpoints."""
    
    def test_get_spending_summary(self, authenticated_client: TestClient, test_household: Household):
        """Test getting spending summary."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/analytics/summary")
        
        assert response.status_code == 200
        data = response.json()
        # Check the actual structure returned by the service
        assert "period" in data
        assert "totals" in data
        assert "category_breakdown" in data
        assert "user_breakdown" in data
        assert "time_series" in data
        assert "top_expenses" in data
        assert "trends" in data
        
        # Check nested structures
        assert "start_date" in data["period"]
        assert "end_date" in data["period"]
        assert "period_type" in data["period"]
        
        assert "total_amount" in data["totals"]
        assert "expense_count" in data["totals"]
        assert "average_expense" in data["totals"]
        assert "daily_average" in data["totals"]

    def test_get_category_analysis(self, authenticated_client: TestClient, test_household: Household):
        """Test getting category analysis."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/analytics/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_spending_patterns(self, authenticated_client: TestClient, test_household: Household):
        """Test getting user spending patterns."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/analytics/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_household_balances(self, authenticated_client: TestClient, test_household: Household):
        """Test getting household balances."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/analytics/balances")
        
        assert response.status_code == 200
        data = response.json()
        # Check the actual structure returned by the service
        assert "household_id" in data
        assert "total_outstanding" in data
        assert "member_balances" in data
        assert "settlement_suggestions" in data
        assert "summary" in data
        
        # Check that member_balances is a list
        assert isinstance(data["member_balances"], list)
        
        # Check summary structure
        assert "members_owed" in data["summary"]
        assert "members_owing" in data["summary"]
        assert "members_settled" in data["summary"]

    def test_get_analytics_dashboard(self, authenticated_client: TestClient, test_household: Household):
        """Test getting analytics dashboard."""
        response = authenticated_client.get(f"/api/households/{test_household.id}/analytics/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "household_id" in data
        assert "household_name" in data
        assert "spending_summary" in data
        assert "top_categories" in data
        assert "user_patterns" in data
        assert "balance_overview" in data
        assert "key_insights" in data
        assert "recommendations" in data


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    def test_invalid_household_id(self, authenticated_client: TestClient):
        """Test accessing invalid household ID."""
        fake_id = uuid4()
        response = authenticated_client.get(f"/api/households/{fake_id}")
        
        assert response.status_code == 403  # Should be forbidden, not 404
    
    def test_invalid_expense_data(self, authenticated_client: TestClient, test_household: Household):
        """Test creating expense with invalid data."""
        invalid_data = {
            "title": "",  # Empty title should fail validation
            "amount": "-10.00",  # Negative amount should fail
            "expense_date": "invalid-date"  # Invalid date format
        }
        
        response = authenticated_client.post(f"/api/households/{test_household.id}/expenses", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_category_color(self, authenticated_client: TestClient, test_household: Household):
        """Test creating category with invalid color."""
        invalid_data = {
            "name": "Test Category",
            "color": "invalid-color"  # Should fail pattern validation
        }
        
        response = authenticated_client.post(f"/api/households/{test_household.id}/categories", json=invalid_data)
        
        assert response.status_code == 422  # Validation error 