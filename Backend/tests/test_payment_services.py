"""
Tests for payment and reimbursement services.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.modules.expenses.services.payment_service import PaymentService
from app.modules.expenses.services.reimbursement_service import ReimbursementService
from app.modules.expenses.models import (
    Payment, PaymentType, PaymentMethod,
    ExpenseSharePayment, ExpenseShare, Expense,
    Household, UserHousehold, UserHouseholdRole,
    Category
)
from app.modules.auth.models import User
from app.modules.auth.models.user import UserRole


class TestPaymentService:
    """Test cases for PaymentService."""

    @pytest.fixture
    def payment_service(self, db_session):
        """Create a payment service instance."""
        return PaymentService(db_session)

    async def test_create_payment_success(self, payment_service, test_household, test_user, test_user_2):
        """Test successful payment creation."""
        success, message, payment = await payment_service.create_payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            payment_type=PaymentType.REIMBURSEMENT,
            current_user_id=test_user.id,
            currency="USD",
            payment_method=PaymentMethod.CASH,
            description="Test payment"
        )

        assert success is True
        assert "successfully" in message
        assert payment is not None
        assert payment.amount == Decimal("50.00")
        assert payment.payer_id == test_user.id
        assert payment.payee_id == test_user_2.id

    async def test_create_payment_invalid_amount(self, payment_service, test_household, test_user, test_user_2):
        """Test payment creation with invalid amount."""
        success, message, payment = await payment_service.create_payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("0.00"),
            payment_type=PaymentType.REIMBURSEMENT,
            current_user_id=test_user.id
        )

        assert success is False
        assert "greater than zero" in message
        assert payment is None

    async def test_create_payment_non_member(self, payment_service, test_household, test_user_2):
        """Test payment creation by non-household member."""
        non_member = User(
            email="nonmember@example.com",
            username="nonmember",
            hashed_password="hashed_password",
            role=UserRole.USER,
            is_active=True
        )
        payment_service.db.add(non_member)
        payment_service.db.commit()

        success, message, payment = await payment_service.create_payment(
            household_id=test_household.id,
            payer_id=non_member.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            payment_type=PaymentType.REIMBURSEMENT,
            current_user_id=non_member.id
        )

        assert success is False
        assert "not a member" in message
        assert payment is None

    async def test_get_payments_with_filters(self, payment_service, test_household, test_user, test_user_2):
        """Test getting payments with various filters."""
        # Create test payments
        for i in range(3):
            await payment_service.create_payment(
                household_id=test_household.id,
                payer_id=test_user.id,
                payee_id=test_user_2.id,
                amount=Decimal(f"{10 + i * 10}.00"),
                payment_type=PaymentType.REIMBURSEMENT,
                current_user_id=test_user.id,
                payment_method=PaymentMethod.CASH
            )

        success, message, result = await payment_service.get_payments(
            household_id=test_household.id,
            current_user_id=test_user.id,
            payer_id=test_user.id,
            payment_method=PaymentMethod.CASH
        )

        assert success is True
        assert result["total"] == 3
        assert len(result["payments"]) == 3

    async def test_update_payment(self, payment_service, test_payment, test_user):
        """Test payment update."""
        updates = {
            "description": "Updated description",
            "amount": Decimal("75.00")
        }

        success, message, updated_payment = await payment_service.update_payment(
            payment_id=test_payment.id,
            current_user_id=test_user.id,
            updates=updates
        )

        assert success is True
        assert updated_payment.description == "Updated description"
        assert updated_payment.amount == Decimal("75.00")

    async def test_delete_payment(self, payment_service, test_payment, test_user):
        """Test payment deletion."""
        success, message = await payment_service.delete_payment(
            payment_id=test_payment.id,
            current_user_id=test_user.id
        )

        assert success is True
        assert "successfully" in message

        # Verify payment is soft deleted
        payment = payment_service.db.query(Payment).filter(Payment.id == test_payment.id).first()
        assert payment.is_active is False

    async def test_link_expense_share(self, payment_service, test_payment, test_expense_share, test_user):
        """Test linking payment to expense share."""
        success, message, esp = await payment_service.link_expense_share(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("20.00"),
            current_user_id=test_user.id
        )

        assert success is True
        assert esp is not None
        assert esp.amount == Decimal("20.00")
        assert esp.payment_id == test_payment.id
        assert esp.expense_share_id == test_expense_share.id

    async def test_link_expense_share_exceeds_amount(self, payment_service, test_payment, test_expense_share, test_user):
        """Test linking amount that exceeds payment amount."""
        success, message, esp = await payment_service.link_expense_share(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("200.00"),  # More than payment amount
            current_user_id=test_user.id
        )

        assert success is False
        assert "exceeds" in message
        assert esp is None

    async def test_create_allocation(self, payment_service, test_payment, test_expense_share):
        """Test creating an allocation."""
        # Test create_allocation
        esp = ExpenseSharePayment.create_allocation(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("30.00")
        )
        
        assert esp.payment_id == test_payment.id
        assert esp.expense_share_id == test_expense_share.id
        assert esp.amount == Decimal("30.00")
        assert esp.is_active is True
        
        # Test create_full_allocation
        esp_full = ExpenseSharePayment.create_full_allocation(
            payment_id=test_payment.id,
            expense_share=test_expense_share
        )


class TestReimbursementService:
    """Test cases for ReimbursementService."""

    @pytest.fixture
    def reimbursement_service(self, db_session):
        """Create a reimbursement service instance."""
        return ReimbursementService(db_session)

    async def test_reimburse_expense_directly(self, reimbursement_service, test_expense, test_user, test_user_2, test_expense_share):
        """Test direct expense reimbursement workflow."""
        success, message, payment = await reimbursement_service.reimburse_expense_directly(
            expense_id=test_expense.id,
            payer_id=test_user_2.id,
            current_user_id=test_user.id,
            payment_method=PaymentMethod.BANK_TRANSFER,
            description="Direct reimbursement"
        )

        assert success is True
        assert payment is not None
        assert payment.payment_type == PaymentType.EXPENSE_PAYMENT
        assert payment.payer_id == test_user_2.id
        assert payment.payee_id == test_expense.created_by

        # Check that expense share is marked as paid
        reimbursement_service.db.refresh(test_expense_share)
        assert test_expense_share.is_paid is True

    async def test_reimburse_already_paid_expense(self, reimbursement_service, test_expense, test_user, test_user_2, test_expense_share):
        """Test reimbursing an already paid expense."""
        # Mark expense share as paid
        test_expense_share.mark_as_paid()
        reimbursement_service.db.commit()

        success, message, payment = await reimbursement_service.reimburse_expense_directly(
            expense_id=test_expense.id,
            payer_id=test_user_2.id,
            current_user_id=test_user.id
        )

        assert success is False
        assert "already" in message or "No unpaid" in message
        assert payment is None

    async def test_pay_all_user_expenses(self, reimbursement_service, test_household, test_user, test_user_2):
        """Test bulk expense payment workflow."""
        # Create multiple unpaid expenses for test_user
        user_household = (
            reimbursement_service.db.query(UserHousehold)
            .filter(
                UserHousehold.user_id == test_user.id,
                UserHousehold.household_id == test_household.id
            )
            .first()
        )

        # Create test expenses and shares
        for i in range(3):
            expense = Expense(
                household_id=test_household.id,
                created_by=test_user_2.id,
                title=f"Test Expense {i}",
                amount=Decimal(f"{20 + i * 10}.00"),
                currency="USD",
                expense_date=date.today(),
                is_active=True
            )
            reimbursement_service.db.add(expense)
            reimbursement_service.db.commit()

            expense_share = ExpenseShare(
                expense_id=expense.id,
                user_household_id=user_household.id,
                share_amount=Decimal(f"{10 + i * 5}.00"),
                is_paid=False,
                is_active=True
            )
            reimbursement_service.db.add(expense_share)

        reimbursement_service.db.commit()

        success, message, payment = await reimbursement_service.pay_all_user_expenses(
            household_id=test_household.id,
            target_user_id=test_user.id,
            payer_id=test_user_2.id,
            current_user_id=test_user.id
        )

        assert success is True
        assert payment is not None
        assert payment.payment_type == PaymentType.EXPENSE_PAYMENT
        assert "All expenses paid" in message

    async def test_make_general_payment(self, reimbursement_service, test_household, test_user, test_user_2):
        """Test general payment workflow."""
        success, message, payment = await reimbursement_service.make_general_payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("100.00"),
            current_user_id=test_user.id,
            payment_method=PaymentMethod.DIGITAL_WALLET,
            description="General payment"
        )

        assert success is True
        assert payment is not None
        assert payment.payment_type == PaymentType.REIMBURSEMENT
        assert payment.amount == Decimal("100.00")
        assert "Payment created successfully" in message

    async def test_make_general_payment_with_allocations(self, reimbursement_service, test_household, test_user, test_user_2, test_expense_share):
        """Test general payment with expense allocations."""
        allocations = [
            {
                "expense_share_id": test_expense_share.id,
                "amount": Decimal("20.00")
            }
        ]

        success, message, payment = await reimbursement_service.make_general_payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            current_user_id=test_user.id,
            expense_allocations=allocations
        )

        assert success is True
        assert payment is not None
        assert "$20.00 allocated" in message
        assert "$30.00 unallocated" in message

    async def test_get_unpaid_expenses_for_user(self, reimbursement_service, test_household, test_user, test_user_2):
        """Test getting unpaid expenses for a user."""
        success, message, result = await reimbursement_service.get_unpaid_expenses_for_user(
            household_id=test_household.id,
            user_id=test_user.id,
            current_user_id=test_user.id
        )

        assert success is True
        assert "expenses" in result
        assert "total_owed" in result
        assert "count" in result


# Fixtures
@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        role=UserRole.USER,
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_user_2(db_session):
    """Create a second test user."""
    user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password="hashed_password",
        role=UserRole.USER,
        is_active=True,
        email_verified=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_household(db_session, test_user, test_user_2):
    """Create a test household."""
    household = Household(
        name="Test Household",
        description="A test household",
        invite_code="TEST123",
        created_by=test_user.id,
        is_active=True
    )
    db_session.add(household)
    db_session.commit()

    # Add user to household
    user_household = UserHousehold(
        user_id=test_user.id,
        household_id=household.id,
        role=UserHouseholdRole.ADMIN,
        is_active=True
    )
    db_session.add(user_household)
    
    # Add second user to household
    user_household_2 = UserHousehold(
        user_id=test_user_2.id,
        household_id=household.id,
        role=UserHouseholdRole.MEMBER,
        is_active=True
    )
    db_session.add(user_household_2)
    db_session.commit()
    
    return household


@pytest.fixture
def test_user_household(db_session, test_user, test_household):
    """Create a test user household relationship."""
    user_household = (
        db_session.query(UserHousehold)
        .filter(
            UserHousehold.user_id == test_user.id,
            UserHousehold.household_id == test_household.id
        )
        .first()
    )
    return user_household


@pytest.fixture
def test_category(db_session, test_household):
    """Create a test category."""
    category = Category(
        name="Test Category",
        household_id=test_household.id,
        icon="test",
        color="#FF0000",
        is_default=False,
        is_active=True
    )
    db_session.add(category)
    db_session.commit()
    return category


@pytest.fixture
def test_expense(db_session, test_household, test_user, test_category):
    """Create a test expense."""
    expense = Expense(
        household_id=test_household.id,
        created_by=test_user.id,
        title="Test Expense",
        description="A test expense",
        amount=Decimal("50.00"),
        currency="USD",
        category_id=test_category.id,
        expense_date=date.today(),
        is_active=True
    )
    db_session.add(expense)
    db_session.commit()
    return expense


@pytest.fixture
def test_expense_share(db_session, test_expense, test_user_household):
    """Create a test expense share."""
    expense_share = ExpenseShare(
        expense_id=test_expense.id,
        user_household_id=test_user_household.id,
        share_amount=Decimal("25.00"),
        share_percentage=Decimal("50.00"),
        is_paid=False,
        is_active=True
    )
    db_session.add(expense_share)
    db_session.commit()
    return expense_share


@pytest.fixture
def test_payment(db_session, test_household, test_user, test_user_2):
    """Create a test payment."""
    payment = Payment(
        household_id=test_household.id,
        payer_id=test_user.id,
        payee_id=test_user_2.id,
        amount=Decimal("100.00"),
        currency="USD",
        payment_type=PaymentType.REIMBURSEMENT,
        payment_method=PaymentMethod.CASH,
        description="Test payment",
        is_active=True
    )
    db_session.add(payment)
    db_session.commit()
    return payment 