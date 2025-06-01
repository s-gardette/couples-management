"""
Frontend test fixtures and utilities.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app.main import app
from app.database import get_db
from app.modules.auth.models.user import User
from app.modules.expenses.models.household import Household
from app.modules.expenses.models.user_household import UserHousehold, UserHouseholdRole
from app.modules.expenses.models.category import Category
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.expense_share import ExpenseShare
from decimal import Decimal
from datetime import date


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for frontend testing."""
    from app.core.utils.security import get_password_hash
    
    user = User(
        email="frontend@test.com",
        username="frontenduser",
        hashed_password=get_password_hash("TestPassword123!"),
        first_name="Frontend",
        last_name="User",
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def frontend_client():
    """Test client for frontend template testing."""
    return TestClient(app)


@pytest.fixture
def authenticated_frontend_client(db_session: Session, test_user: User):
    """Test client with authenticated user for frontend testing."""
    client = TestClient(app)
    
    # Override the get_db dependency to use our test db_session
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    # First try to login through the actual login endpoint
    login_data = {
        "username": test_user.email,  # Login uses email as username
        "password": "TestPassword123!"
    }
    
    # Post to login form to set cookies
    login_response = client.post("/auth/login", data=login_data, follow_redirects=False)
    
    # If login endpoint doesn't work or doesn't set cookies, manually set auth
    if login_response.status_code not in [200, 302, 307]:
        # Fallback: manually set authentication using tokens
        from app.core.utils.security import create_access_token, create_refresh_token
        
        access_token = create_access_token(subject=str(test_user.id))
        refresh_token = create_refresh_token(subject=str(test_user.id))
        
        # Set authentication cookies
        client.cookies.set("access_token", access_token)
        client.cookies.set("refresh_token", refresh_token)
    
    return client


@pytest.fixture
def test_household_with_expenses(db_session: Session, test_user: User):
    """Create a test household with sample expenses for frontend testing."""
    # Create household
    household = Household(
        name="Test Frontend Household",
        description="Test household for frontend testing",
        invite_code="FRONT123",
        created_by=test_user.id,
        is_active=True
    )
    db_session.add(household)
    db_session.flush()
    
    # Add user to household
    user_household = UserHousehold(
        user_id=test_user.id,
        household_id=household.id,
        role=UserHouseholdRole.ADMIN,
        is_active=True
    )
    db_session.add(user_household)
    db_session.flush()
    
    # Create category
    category = Category(
        name="Frontend Test Category",
        household_id=household.id,
        is_active=True
    )
    db_session.add(category)
    db_session.flush()
    
    # Create sample expenses
    expenses = []
    for i in range(3):
        expense = Expense(
            household_id=household.id,
            created_by=test_user.id,
            title=f"Frontend Test Expense {i+1}",
            description=f"Test expense {i+1} for frontend testing",
            amount=Decimal(f"{(i+1)*25}.00"),
            currency="USD",
            category_id=category.id,
            expense_date=date.today(),
            is_active=True
        )
        db_session.add(expense)
        db_session.flush()
        
        # Create expense share
        share = ExpenseShare(
            expense_id=expense.id,
            user_household_id=user_household.id,
            share_amount=expense.amount,
            share_percentage=Decimal("100.00"),
            is_paid=(i % 2 == 0),  # Alternate paid/unpaid
            is_active=True
        )
        db_session.add(share)
        expenses.append(expense)
    
    db_session.commit()
    
    return {
        "household": household,
        "user_household": user_household,
        "category": category,
        "expenses": expenses
    }


@pytest.fixture
def mock_expense_id():
    """Generate a mock expense ID for testing invalid scenarios."""
    return str(uuid4())


class TemplateTestUtils:
    """Utility class for template testing."""
    
    @staticmethod
    def assert_template_response(response, expected_status=200, should_contain=None, should_not_contain=None):
        """Assert template response properties."""
        assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
        
        if should_contain:
            if isinstance(should_contain, str):
                should_contain = [should_contain]
            for text in should_contain:
                assert text in response.text, f"Response should contain '{text}'"
        
        if should_not_contain:
            if isinstance(should_not_contain, str):
                should_not_contain = [should_not_contain]
            for text in should_not_contain:
                assert text not in response.text, f"Response should not contain '{text}'"
    
    @staticmethod
    def assert_html_structure(response, expected_elements=None):
        """Assert basic HTML structure."""
        assert "<!DOCTYPE html>" in response.text or "<div" in response.text, "Response should contain HTML"
        
        if expected_elements:
            for element in expected_elements:
                assert element in response.text, f"Response should contain HTML element '{element}'"


@pytest.fixture
def template_utils():
    """Template testing utilities."""
    return TemplateTestUtils 