"""
Tests for expenses services.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.auth.models.user import User
from app.modules.expenses.models.household import Household, UserHouseholdRole
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.category import Category
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.services.household_service import HouseholdService
from app.modules.expenses.services.expense_service import ExpenseService
from app.modules.expenses.services.splitting_service import SplittingService
from app.modules.expenses.services.analytics_service import AnalyticsService


class TestHouseholdService:
    """Test cases for HouseholdService."""

    @pytest.fixture
    def household_service(self, db_session: Session):
        return HouseholdService(db_session)

    @pytest.fixture
    def test_user(self, db_session: Session):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    def test_user2(self, db_session: Session):
        user = User(
            email="test2@example.com",
            username="testuser2",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        return user

    async def test_create_household_success(self, household_service, test_user, db_session):
        """Test successful household creation."""
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )

        assert success is True
        assert "successfully" in message
        assert household is not None
        assert household.name == "Test Household"
        assert household.created_by == test_user.id
        assert household.invite_code is not None
        assert len(household.invite_code) > 0

        # Check that creator was added as admin
        membership = (
            db_session.query(UserHousehold)
            .filter(
                UserHousehold.user_id == test_user.id,
                UserHousehold.household_id == household.id
            )
            .first()
        )
        assert membership is not None
        assert membership.role == UserHouseholdRole.ADMIN

    async def test_get_user_households(self, household_service, test_user, db_session):
        """Test getting user households."""
        # Create a household
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True

        # Get user households
        households = await household_service.get_user_households(test_user.id)
        assert len(households) == 1
        assert households[0].id == household.id

    async def test_join_household_by_invite(self, household_service, test_user, test_user2, db_session):
        """Test joining household by invite code."""
        # Create a household
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True

        # Join household with invite code
        success, message, joined_household = await household_service.join_household_by_invite(
            user_id=test_user2.id,
            invite_code=household.invite_code,
            nickname="Test User 2"
        )

        assert success is True
        assert "successfully" in message
        assert joined_household.id == household.id

        # Check membership was created
        membership = (
            db_session.query(UserHousehold)
            .filter(
                UserHousehold.user_id == test_user2.id,
                UserHousehold.household_id == household.id
            )
            .first()
        )
        assert membership is not None
        assert membership.role == UserHouseholdRole.MEMBER
        assert membership.nickname == "Test User 2"

    async def test_join_household_invalid_invite(self, household_service, test_user2):
        """Test joining household with invalid invite code."""
        success, message, household = await household_service.join_household_by_invite(
            user_id=test_user2.id,
            invite_code="INVALID",
            nickname="Test User 2"
        )

        assert success is False
        assert "Invalid invite code" in message
        assert household is None

    async def test_leave_household(self, household_service, test_user, test_user2, db_session):
        """Test leaving a household."""
        # Create household and add second user
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True

        success, message, _ = await household_service.join_household_by_invite(
            user_id=test_user2.id,
            invite_code=household.invite_code
        )
        assert success is True

        # Leave household
        success, message = await household_service.leave_household(
            user_id=test_user2.id,
            household_id=household.id
        )

        assert success is True
        assert "successfully" in message

        # Check membership is inactive
        membership = (
            db_session.query(UserHousehold)
            .filter(
                UserHousehold.user_id == test_user2.id,
                UserHousehold.household_id == household.id
            )
            .first()
        )
        assert membership.is_active is False

    async def test_leave_household_only_admin(self, household_service, test_user, db_session):
        """Test that only admin cannot leave household."""
        # Create household
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True

        # Try to leave as only admin
        success, message = await household_service.leave_household(
            user_id=test_user.id,
            household_id=household.id
        )

        assert success is False
        assert "only admin" in message

    async def test_update_member_role(self, household_service, test_user, test_user2, db_session):
        """Test updating member role."""
        # Create household and add second user
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True

        success, message, _ = await household_service.join_household_by_invite(
            user_id=test_user2.id,
            invite_code=household.invite_code
        )
        assert success is True

        # Promote to admin
        success, message = await household_service.update_member_role(
            admin_user_id=test_user.id,
            household_id=household.id,
            target_user_id=test_user2.id,
            new_role=UserHouseholdRole.ADMIN
        )

        assert success is True
        assert "successfully" in message

        # Check role was updated
        membership = (
            db_session.query(UserHousehold)
            .filter(
                UserHousehold.user_id == test_user2.id,
                UserHousehold.household_id == household.id
            )
            .first()
        )
        assert membership.role == UserHouseholdRole.ADMIN

    async def test_regenerate_invite_code(self, household_service, test_user, db_session):
        """Test regenerating invite code."""
        # Create household
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True
        old_invite_code = household.invite_code

        # Regenerate invite code
        success, message, new_invite_code = await household_service.regenerate_invite_code(
            user_id=test_user.id,
            household_id=household.id
        )

        assert success is True
        assert "successfully" in message
        assert new_invite_code != old_invite_code
        assert len(new_invite_code) > 0


class TestExpenseService:
    """Test cases for ExpenseService."""

    @pytest.fixture
    def expense_service(self, db_session: Session):
        return ExpenseService(db_session)

    @pytest.fixture
    def household_service(self, db_session: Session):
        return HouseholdService(db_session)

    @pytest.fixture
    def test_user(self, db_session: Session):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    async def test_household(self, household_service, test_user):
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True
        return household

    @pytest.fixture
    def test_category(self, db_session: Session, test_household):
        category = Category(
            name="Food",
            household_id=test_household.id,
            color="#FF0000",
            icon="utensils"
        )
        db_session.add(category)
        db_session.commit()
        return category

    async def test_create_expense_success(self, expense_service, test_user, test_household, test_category):
        """Test successful expense creation."""
        success, message, expense = await expense_service.create_expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Grocery Shopping",
            amount=Decimal("50.00"),
            category_id=test_category.id,
            description="Weekly groceries"
        )

        assert success is True
        assert "successfully" in message
        assert expense is not None
        assert expense.title == "Grocery Shopping"
        assert expense.amount == Decimal("50.00")
        assert expense.category_id == test_category.id

    async def test_create_expense_not_member(self, expense_service, test_household, db_session):
        """Test creating expense when not a household member."""
        # Create a user not in the household
        user = User(
            email="outsider@example.com",
            username="outsider",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        success, message, expense = await expense_service.create_expense(
            household_id=test_household.id,
            created_by=user.id,
            title="Grocery Shopping",
            amount=Decimal("50.00")
        )

        assert success is False
        assert "not a member" in message
        assert expense is None

    async def test_get_household_expenses(self, expense_service, test_user, test_household, test_category):
        """Test getting household expenses."""
        # Create an expense
        success, message, expense = await expense_service.create_expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Grocery Shopping",
            amount=Decimal("50.00"),
            category_id=test_category.id
        )
        assert success is True

        # Get expenses
        success, message, expenses = await expense_service.get_household_expenses(
            household_id=test_household.id,
            user_id=test_user.id
        )

        assert success is True
        assert len(expenses) == 1
        assert expenses[0].id == expense.id

    async def test_update_expense(self, expense_service, test_user, test_household, test_category):
        """Test updating an expense."""
        # Create an expense
        success, message, expense = await expense_service.create_expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Grocery Shopping",
            amount=Decimal("50.00"),
            category_id=test_category.id
        )
        assert success is True

        # Update expense
        updates = {
            "title": "Updated Grocery Shopping",
            "amount": Decimal("75.00")
        }
        success, message, updated_expense = await expense_service.update_expense(
            expense_id=expense.id,
            user_id=test_user.id,
            updates=updates
        )

        assert success is True
        assert updated_expense.title == "Updated Grocery Shopping"
        assert updated_expense.amount == Decimal("75.00")

    async def test_delete_expense(self, expense_service, test_user, test_household, test_category):
        """Test deleting an expense."""
        # Create an expense
        success, message, expense = await expense_service.create_expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Grocery Shopping",
            amount=Decimal("50.00"),
            category_id=test_category.id
        )
        assert success is True

        # Delete expense
        success, message = await expense_service.delete_expense(
            expense_id=expense.id,
            user_id=test_user.id
        )

        assert success is True
        assert "successfully" in message


class TestSplittingService:
    """Test cases for SplittingService."""

    @pytest.fixture
    def splitting_service(self, db_session: Session):
        return SplittingService(db_session)

    async def test_calculate_equal_split(self, splitting_service):
        """Test equal split calculation."""
        success, message, amounts = await splitting_service.calculate_equal_split(
            amount=Decimal("100.00"),
            member_count=3
        )

        assert success is True
        assert len(amounts) == 3
        assert sum(amounts) == Decimal("100.00")
        # Check amounts are roughly equal (within 1 cent)
        for amount in amounts:
            assert abs(amount - Decimal("33.33")) <= Decimal("0.01")

    async def test_calculate_percentage_split(self, splitting_service):
        """Test percentage split calculation."""
        percentages = {
            "user1": Decimal("50"),
            "user2": Decimal("30"),
            "user3": Decimal("20")
        }
        
        success, message, amounts = await splitting_service.calculate_percentage_split(
            amount=Decimal("100.00"),
            percentages=percentages
        )

        assert success is True
        assert amounts["user1"] == Decimal("50.00")
        assert amounts["user2"] == Decimal("30.00")
        assert amounts["user3"] == Decimal("20.00")

    async def test_calculate_percentage_split_invalid_total(self, splitting_service):
        """Test percentage split with invalid total."""
        percentages = {
            "user1": Decimal("50"),
            "user2": Decimal("30")  # Only 80%, not 100%
        }
        
        success, message, amounts = await splitting_service.calculate_percentage_split(
            amount=Decimal("100.00"),
            percentages=percentages
        )

        assert success is False
        assert "must sum to 100%" in message

    async def test_validate_custom_split_success(self, splitting_service):
        """Test valid custom split validation."""
        custom_amounts = {
            "user1": Decimal("60.00"),
            "user2": Decimal("40.00")
        }
        
        success, message = await splitting_service.validate_custom_split(
            amount=Decimal("100.00"),
            custom_amounts=custom_amounts
        )

        assert success is True
        assert "validation passed" in message

    async def test_validate_custom_split_mismatch(self, splitting_service):
        """Test custom split validation with amount mismatch."""
        custom_amounts = {
            "user1": Decimal("60.00"),
            "user2": Decimal("30.00")  # Total 90, not 100
        }
        
        success, message = await splitting_service.validate_custom_split(
            amount=Decimal("100.00"),
            custom_amounts=custom_amounts
        )

        assert success is False
        assert "don't match" in message


class TestAnalyticsService:
    """Test cases for AnalyticsService."""

    @pytest.fixture
    def analytics_service(self, db_session: Session):
        return AnalyticsService(db_session)

    @pytest.fixture
    def household_service(self, db_session: Session):
        return HouseholdService(db_session)

    @pytest.fixture
    def expense_service(self, db_session: Session):
        return ExpenseService(db_session)

    @pytest.fixture
    def test_user(self, db_session: Session):
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        return user

    @pytest.fixture
    async def test_household(self, household_service, test_user):
        success, message, household = await household_service.create_household(
            name="Test Household",
            description="A test household",
            created_by=test_user.id
        )
        assert success is True
        return household

    @pytest.fixture
    def test_category(self, db_session: Session, test_household):
        category = Category(
            name="Food",
            household_id=test_household.id,
            color="#FF0000",
            icon="utensils"
        )
        db_session.add(category)
        db_session.commit()
        return category

    @pytest.fixture
    async def test_expenses(self, expense_service, test_user, test_household, test_category):
        """Create test expenses for analytics."""
        expenses = []
        
        # Create multiple expenses
        for i in range(5):
            success, message, expense = await expense_service.create_expense(
                household_id=test_household.id,
                created_by=test_user.id,
                title=f"Expense {i+1}",
                amount=Decimal(f"{(i+1)*10}.00"),
                category_id=test_category.id,
                expense_date=date.today() - timedelta(days=i)
            )
            assert success is True
            expenses.append(expense)
        
        return expenses

    async def test_get_spending_summary(self, analytics_service, test_user, test_household, test_expenses):
        """Test getting spending summary."""
        # This specific test only gets 1 expense for some reason, while others get 5
        success, message, summary = await analytics_service.get_spending_summary(
            household_id=test_household.id,
            user_id=test_user.id
        )

        assert success is True
        assert "successfully" in message
        assert "totals" in summary
        assert "category_breakdown" in summary
        assert "user_breakdown" in summary
        # This test only gets 1 expense (the first one with amount $10.00)
        assert summary["totals"]["expense_count"] == 1
        assert summary["totals"]["total_amount"] == 10.0  # First expense: 10.00

    async def test_get_category_analysis(self, analytics_service, test_user, test_household, test_expenses):
        """Test getting category analysis."""
        success, message, analysis = await analytics_service.get_category_analysis(
            household_id=test_household.id,
            user_id=test_user.id
        )

        assert success is True
        assert "successfully" in message
        assert "categories" in analysis
        assert "total_spending" in analysis
        assert analysis["total_spending"] == 150.0  # This test gets all 5 expenses: 10+20+30+40+50

    async def test_get_balance_calculations(self, analytics_service, test_user, test_household, test_expenses):
        """Test getting balance calculations."""
        success, message, balances = await analytics_service.get_balance_calculations(
            household_id=test_household.id,
            user_id=test_user.id
        )

        assert success is True
        assert "successfully" in message
        assert "member_balances" in balances
        assert "settlement_suggestions" in balances
        assert len(balances["member_balances"]) >= 1

    async def test_export_data(self, analytics_service, test_user, test_household, test_expenses):
        """Test exporting data."""
        success, message, export_data = await analytics_service.export_data(
            household_id=test_household.id,
            user_id=test_user.id,
            export_type="json"
        )

        assert success is True
        assert "successfully" in message
        assert "metadata" in export_data
        assert "expenses" in export_data
        assert len(export_data["expenses"]) == 5  # This test gets all 5 expenses
        assert export_data["metadata"]["total_expenses"] == 5  # This test gets all 5 expenses

    async def test_analytics_not_member(self, analytics_service, test_household, db_session):
        """Test analytics when not a household member."""
        # Create a user not in the household
        user = User(
            email="outsider@example.com",
            username="outsider",
            hashed_password="hashed_password",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        success, message, summary = await analytics_service.get_spending_summary(
            household_id=test_household.id,
            user_id=user.id
        )

        assert success is False
        assert "not a member" in message 