"""
Tests for expenses module models.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.modules.expenses.models import (
    Household, 
    UserHousehold, 
    UserHouseholdRole,
    Category, 
    Expense, 
    ExpenseShare,
    Payment,
    PaymentType,
    PaymentMethod,
    ExpenseSharePayment
)
from app.modules.auth.models import User
from app.modules.auth.models.user import UserRole


class TestHouseholdModel:
    """Test cases for Household model."""
    
    def test_household_creation(self, db_session):
        """Test basic household creation."""
        household = Household(
            name="Test Household",
            description="A test household",
            invite_code="TEST123",
            is_active=True
        )
        db_session.add(household)
        db_session.commit()
        
        assert household.id is not None
        assert household.name == "Test Household"
        assert household.description == "A test household"
        assert household.invite_code == "TEST123"
        assert household.is_active is True
        assert household.created_at is not None
        assert household.updated_at is not None
    
    def test_household_default_settings(self, db_session):
        """Test household default settings."""
        household = Household(
            name="Test Household",
            invite_code="TEST123"
        )
        db_session.add(household)
        db_session.commit()
        
        # Test default settings
        assert household.get_setting("default_currency") == "USD"
        assert household.get_setting("allow_member_invites") is True
        assert household.get_setting("default_split_method") == "equal"
    
    def test_household_settings_management(self, db_session):
        """Test household settings management."""
        household = Household(
            name="Test Household",
            invite_code="TEST123"
        )
        db_session.add(household)
        db_session.commit()
        
        # Update a setting
        household.update_setting("default_currency", "EUR")
        assert household.get_setting("default_currency") == "EUR"
        
        # Get non-existent setting with default
        assert household.get_setting("non_existent", "default_value") == "default_value"
    
    def test_household_member_management(self, db_session, test_user):
        """Test household member management methods."""
        household = Household(
            name="Test Household",
            invite_code="TEST123",
            created_by=test_user.id
        )
        db_session.add(household)
        db_session.commit()
        
        # Create a user household relationship
        user_household = UserHousehold(
            user_id=test_user.id,
            household_id=household.id,
            role=UserHouseholdRole.ADMIN,
            is_active=True
        )
        db_session.add(user_household)
        db_session.commit()
        
        # Test member management methods
        assert household.is_member(str(test_user.id)) is True
        assert household.is_admin(str(test_user.id)) is True
        assert household.member_count == 1
        assert household.admin_count == 1
        
        member = household.get_member(str(test_user.id))
        assert member is not None
        assert member.role == UserHouseholdRole.ADMIN
    
    def test_household_repr(self, db_session):
        """Test household string representation."""
        household = Household(
            name="Test Household",
            invite_code="TEST123"
        )
        db_session.add(household)
        db_session.commit()
        
        repr_str = repr(household)
        assert "Test Household" in repr_str
        assert "TEST123" in repr_str


class TestUserHouseholdModel:
    """Test cases for UserHousehold model."""
    
    def test_user_household_creation(self, db_session, test_user, test_household):
        """Test basic user household creation."""
        user_household = UserHousehold(
            user_id=test_user.id,
            household_id=test_household.id,
            role=UserHouseholdRole.MEMBER,
            nickname="Test User",
            is_active=True
        )
        db_session.add(user_household)
        db_session.commit()
        
        assert user_household.id is not None
        assert user_household.user_id == test_user.id
        assert user_household.household_id == test_household.id
        assert user_household.role == UserHouseholdRole.MEMBER
        assert user_household.nickname == "Test User"
        assert user_household.is_active is True
        assert user_household.joined_at is not None
    
    def test_user_household_display_name(self, db_session, test_user, test_household):
        """Test display name property."""
        # With nickname
        user_household = UserHousehold(
            user_id=test_user.id,
            household_id=test_household.id,
            nickname="Custom Name"
        )
        db_session.add(user_household)
        db_session.commit()
        
        assert user_household.display_name == "Custom Name"
        
        # Without nickname (should use user's display name)
        user_household.nickname = None
        assert user_household.display_name == test_user.display_name
    
    def test_user_household_role_management(self, db_session, test_user, test_household):
        """Test role management methods."""
        user_household = UserHousehold(
            user_id=test_user.id,
            household_id=test_household.id,
            role=UserHouseholdRole.MEMBER
        )
        db_session.add(user_household)
        db_session.commit()
        
        # Test role checks
        assert user_household.is_member() is True
        assert user_household.is_admin() is False
        
        # Promote to admin
        user_household.promote_to_admin()
        assert user_household.role == UserHouseholdRole.ADMIN
        assert user_household.is_admin() is True
        assert user_household.is_member() is False
        
        # Demote to member
        user_household.demote_to_member()
        assert user_household.role == UserHouseholdRole.MEMBER
    
    def test_user_household_lifecycle(self, db_session, test_user, test_household):
        """Test household lifecycle methods."""
        user_household = UserHousehold(
            user_id=test_user.id,
            household_id=test_household.id,
            is_active=True
        )
        db_session.add(user_household)
        db_session.commit()
        
        # Leave household
        user_household.leave_household()
        assert user_household.is_active is False
        
        # Rejoin household
        original_joined_at = user_household.joined_at
        user_household.rejoin_household()
        assert user_household.is_active is True
        assert user_household.joined_at > original_joined_at
    
    def test_user_household_create_membership(self, test_user, test_household):
        """Test create membership class method."""
        user_household = UserHousehold.create_membership(
            user_id=str(test_user.id),
            household_id=str(test_household.id),
            role=UserHouseholdRole.ADMIN,
            nickname="Admin User"
        )
        
        assert user_household.user_id == str(test_user.id)
        assert user_household.household_id == str(test_household.id)
        assert user_household.role == UserHouseholdRole.ADMIN
        assert user_household.nickname == "Admin User"
        assert user_household.is_active is True


class TestCategoryModel:
    """Test cases for Category model."""
    
    def test_category_creation(self, db_session):
        """Test basic category creation."""
        category = Category(
            name="Food & Dining",
            icon="utensils",
            color="#EF4444",
            is_default=True,
            is_active=True
        )
        db_session.add(category)
        db_session.commit()
        
        assert category.id is not None
        assert category.name == "Food & Dining"
        assert category.icon == "utensils"
        assert category.color == "#EF4444"
        assert category.is_default is True
        assert category.is_active is True
    
    def test_category_global_vs_household(self, db_session, test_household):
        """Test global vs household-specific categories."""
        # Global category
        global_category = Category(
            name="Global Category",
            household_id=None
        )
        db_session.add(global_category)
        
        # Household-specific category
        household_category = Category(
            name="Household Category",
            household_id=test_household.id
        )
        db_session.add(household_category)
        db_session.commit()
        
        assert global_category.is_global is True
        assert global_category.is_household_specific is False
        
        assert household_category.is_global is False
        assert household_category.is_household_specific is True
    
    def test_category_color_validation(self, db_session):
        """Test category color validation."""
        category = Category(name="Test Category")
        db_session.add(category)
        db_session.commit()
        
        # Valid color
        category.set_color("#FF0000")
        assert category.color == "#FF0000"
        
        # Invalid color format
        with pytest.raises(ValueError, match="Color must be in hex format"):
            category.set_color("red")
    
    def test_category_default_management(self, db_session):
        """Test default category management."""
        category = Category(name="Test Category", is_default=False)
        db_session.add(category)
        db_session.commit()
        
        # Make default
        category.make_default()
        assert category.is_default is True
        
        # Remove default
        category.remove_default()
        assert category.is_default is False
    
    def test_category_class_methods(self):
        """Test category class methods."""
        # Test global category creation
        global_cat = Category.create_global_category(
            name="Global Test",
            icon="test",
            color="#123456",
            is_default=True
        )
        assert global_cat.household_id is None
        assert global_cat.name == "Global Test"
        assert global_cat.is_default is True
        
        # Test household category creation
        test_uuid = "12345678-1234-1234-1234-123456789012"
        household_cat = Category.create_household_category(
            name="Household Test",
            household_id=test_uuid,
            icon="house"
        )
        assert str(household_cat.household_id) == test_uuid
        assert household_cat.name == "Household Test"
        
        # Test default categories
        default_categories = Category.get_default_categories()
        assert len(default_categories) == 10
        assert any(cat["name"] == "Food & Dining" for cat in default_categories)


class TestExpenseModel:
    """Test cases for Expense model."""
    
    def test_expense_creation(self, db_session, test_household, test_user, test_category):
        """Test basic expense creation."""
        expense = Expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Grocery Shopping",
            description="Weekly groceries",
            amount=Decimal("125.50"),
            currency="USD",
            category_id=test_category.id,
            expense_date=date.today(),
            tags=["groceries", "weekly"],
            is_active=True
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.id is not None
        assert expense.title == "Grocery Shopping"
        assert expense.amount == Decimal("125.50")
        assert expense.currency == "USD"
        assert expense.tags == ["groceries", "weekly"]
    
    def test_expense_amount_properties(self, db_session, test_household, test_user):
        """Test expense amount-related properties."""
        expense = Expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Test Expense",
            amount=Decimal("100.00"),
            currency="USD"
        )
        db_session.add(expense)
        db_session.commit()
        
        assert expense.amount_decimal == Decimal("100.00")
        assert expense.formatted_amount == "$100.00"
        
        # Test different currencies
        expense.currency = "EUR"
        assert expense.formatted_amount == "€100.00"
    
    def test_expense_tag_management(self, db_session, test_household, test_user):
        """Test expense tag management."""
        expense = Expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Test Expense",
            amount=Decimal("50.00")
        )
        db_session.add(expense)
        db_session.commit()
        
        # Add tags
        expense.add_tag("food")
        expense.add_tag("restaurant")
        assert "food" in expense.tags
        assert "restaurant" in expense.tags
        
        # Check tag existence
        assert expense.has_tag("food") is True
        assert expense.has_tag("nonexistent") is False
        
        # Remove tag
        expense.remove_tag("food")
        assert "food" not in expense.tags
        assert "restaurant" in expense.tags
    
    def test_expense_receipt_management(self, db_session, test_household, test_user):
        """Test expense receipt management."""
        expense = Expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Test Expense",
            amount=Decimal("50.00")
        )
        db_session.add(expense)
        db_session.commit()
        
        # Set receipt
        expense.set_receipt("https://example.com/receipt.jpg")
        assert expense.receipt_url == "https://example.com/receipt.jpg"
        
        # Remove receipt
        expense.remove_receipt()
        assert expense.receipt_url is None
    
    def test_expense_share_properties(self, db_session, test_household, test_user, test_user_household):
        """Test expense share-related properties."""
        expense = Expense(
            household_id=test_household.id,
            created_by=test_user.id,
            title="Test Expense",
            amount=Decimal("100.00")
        )
        db_session.add(expense)
        db_session.commit()
        
        # Create expense share
        share = ExpenseShare(
            expense_id=expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("50.00"),
            is_paid=False
        )
        db_session.add(share)
        db_session.commit()
        
        assert expense.total_shares_amount == Decimal("50.00")
        assert expense.remaining_amount == Decimal("50.00")
        assert expense.is_fully_shared is False
        assert expense.paid_shares_count == 0
        assert expense.unpaid_shares_count == 1
        assert expense.is_fully_paid is False
        
        # Mark share as paid
        share.is_paid = True
        assert expense.paid_shares_count == 1
        assert expense.unpaid_shares_count == 0
        assert expense.is_fully_paid is True


class TestExpenseShareModel:
    """Test cases for ExpenseShare model."""
    
    def test_expense_share_creation(self, db_session, test_expense, test_user_household):
        """Test basic expense share creation."""
        share = ExpenseShare(
            expense_id=test_expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("25.00"),
            share_percentage=Decimal("50.00"),
            is_paid=False,
            is_active=True
        )
        db_session.add(share)
        db_session.commit()
        
        assert share.id is not None
        assert share.expense_id == test_expense.id
        assert share.user_household_id == test_user_household.id
        assert share.share_amount == Decimal("25.00")
        assert share.share_percentage == Decimal("50.00")
        assert share.is_paid is False
    
    def test_expense_share_properties(self, db_session, test_expense, test_user_household):
        """Test expense share properties."""
        share = ExpenseShare(
            expense_id=test_expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("30.00"),
            share_percentage=Decimal("60.00")
        )
        db_session.add(share)
        db_session.commit()
        
        assert share.share_amount_decimal == Decimal("30.00")
        assert share.share_percentage_decimal == Decimal("60.00")
        assert share.formatted_amount == "$30.00"  # Assuming USD
        assert share.user_display_name == test_user_household.display_name
    
    def test_expense_share_payment_management(self, db_session, test_expense, test_user_household):
        """Test expense share payment management."""
        share = ExpenseShare(
            expense_id=test_expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("40.00"),
            is_paid=False
        )
        db_session.add(share)
        db_session.commit()
        
        # Mark as paid
        share.mark_as_paid(payment_method="Credit Card", payment_notes="Paid online")
        assert share.is_paid is True
        assert share.paid_at is not None
        assert share.payment_method == "Credit Card"
        assert share.payment_notes == "Paid online"
        
        # Mark as unpaid
        share.mark_as_unpaid()
        assert share.is_paid is False
        assert share.paid_at is None
        assert share.payment_method is None
        assert share.payment_notes is None
    
    def test_expense_share_amount_updates(self, db_session, test_expense, test_user_household):
        """Test expense share amount updates."""
        share = ExpenseShare(
            expense_id=test_expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("20.00"),
            share_percentage=Decimal("40.00")
        )
        db_session.add(share)
        db_session.commit()
        
        # Update amount
        share.update_amount(Decimal("35.00"))
        assert share.share_amount == Decimal("35.00")
        
        # Update percentage
        share.update_percentage(Decimal("70.00"))
        assert share.share_percentage == Decimal("70.00")
    
    def test_expense_share_class_methods(self, test_expense, test_user_household):
        """Test expense share class methods."""
        # Test create_share
        share = ExpenseShare.create_share(
            expense_id=str(test_expense.id),
            user_household_id=str(test_user_household.id),
            share_amount=Decimal("50.00"),
            share_percentage=Decimal("100.00")
        )
        assert share.expense_id == str(test_expense.id)
        assert share.share_amount == Decimal("50.00")
        assert share.is_paid is False
        assert share.is_active is True
        
        # Test create_equal_share
        equal_share = ExpenseShare.create_equal_share(
            expense_id=str(test_expense.id),
            user_household_id=str(test_user_household.id),
            total_amount=Decimal("100.00"),
            num_people=4
        )
        assert equal_share.share_amount == Decimal("25.00")
        assert equal_share.share_percentage == Decimal("25.00")
        
        # Test create_percentage_share
        percent_share = ExpenseShare.create_percentage_share(
            expense_id=str(test_expense.id),
            user_household_id=str(test_user_household.id),
            total_amount=Decimal("100.00"),
            percentage=Decimal("30.00")
        )
        assert percent_share.share_amount == Decimal("30.00")
        assert percent_share.share_percentage == Decimal("30.00")
    
    def test_expense_share_time_properties(self, db_session, test_expense, test_user_household):
        """Test expense share time-related properties."""
        # Create expense with specific date
        test_expense.expense_date = date.today() - timedelta(days=5)
        
        share = ExpenseShare(
            expense_id=test_expense.id,
            user_household_id=test_user_household.id,
            share_amount=Decimal("25.00"),
            is_paid=True,
            paid_at=datetime.utcnow() - timedelta(days=2)
        )
        db_session.add(share)
        db_session.commit()
        
        assert share.days_since_expense == 5
        assert share.days_since_paid == 2


class TestPaymentModel:
    """Test cases for Payment model."""
    
    def test_payment_creation(self, db_session, test_household, test_user, test_user_2):
        """Test basic payment creation."""
        from app.modules.expenses.models.payment import Payment, PaymentType, PaymentMethod
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            currency="USD",
            payment_type=PaymentType.REIMBURSEMENT,
            payment_method=PaymentMethod.CASH,
            description="Test payment",
            reference_number="REF123",
            is_active=True
        )
        db_session.add(payment)
        db_session.commit()
        
        assert payment.id is not None
        assert payment.household_id == test_household.id
        assert payment.payer_id == test_user.id
        assert payment.payee_id == test_user_2.id
        assert payment.amount == Decimal("50.00")
        assert payment.currency == "USD"
        assert payment.payment_type == PaymentType.REIMBURSEMENT
        assert payment.payment_method == PaymentMethod.CASH
        assert payment.description == "Test payment"
        assert payment.reference_number == "REF123"
        assert payment.is_active is True
        assert payment.payment_date is not None
        assert payment.created_at is not None
    
    def test_payment_amount_properties(self, db_session, test_household, test_user, test_user_2):
        """Test payment amount-related properties."""
        from app.modules.expenses.models.payment import Payment, PaymentType
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("100.50"),
            currency="USD",
            payment_type=PaymentType.REIMBURSEMENT
        )
        db_session.add(payment)
        db_session.commit()
        
        # Test amount decimal property
        assert payment.amount_decimal == Decimal("100.50")
        
        # Test formatted amount
        assert payment.formatted_amount == "$100.50"
        
        # Test with different currency
        payment.currency = "EUR"
        assert payment.formatted_amount == "€100.50"
    
    def test_payment_user_properties(self, db_session, test_household, test_user, test_user_2):
        """Test payment user-related properties."""
        from app.modules.expenses.models.payment import Payment, PaymentType
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            payment_type=PaymentType.REIMBURSEMENT
        )
        db_session.add(payment)
        db_session.commit()
        
        # Test payer name
        assert test_user.username in payment.payer_name
        
        # Test payee name
        assert test_user_2.username in payment.payee_name
    
    def test_payment_allocation_properties(self, db_session, test_household, test_user, test_user_2, test_expense_share):
        """Test payment allocation-related properties."""
        from app.modules.expenses.models.payment import Payment, PaymentType
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("100.00"),
            payment_type=PaymentType.REIMBURSEMENT
        )
        db_session.add(payment)
        db_session.commit()
        
        # Initially no allocations
        assert payment.total_allocated_amount == Decimal("0")
        assert payment.unallocated_amount == Decimal("100.00")
        assert payment.is_fully_allocated is False
        assert len(payment.covered_expense_shares) == 0
        
        # Add a mock allocation
        esp = ExpenseSharePayment(
            payment_id=payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("30.00"),
            is_active=True
        )
        db_session.add(esp)
        db_session.commit()
        db_session.refresh(payment)
        
        # Test with allocation
        assert payment.total_allocated_amount == Decimal("30.00")
        assert payment.unallocated_amount == Decimal("70.00")
        assert payment.is_fully_allocated is False
    
    def test_payment_class_methods(self, test_household, test_user, test_user_2):
        """Test payment class methods."""
        from app.modules.expenses.models.payment import Payment, PaymentMethod
        
        # Test create_reimbursement
        payment = Payment.create_reimbursement(
            household_id=str(test_household.id),
            payer_id=str(test_user.id),
            payee_id=str(test_user_2.id),
            amount=Decimal("75.00"),
            currency="USD",
            payment_method=PaymentMethod.BANK_TRANSFER,
            description="Test reimbursement",
            reference_number="BANK123"
        )
        
        assert payment.household_id == str(test_household.id)
        assert payment.payer_id == str(test_user.id)
        assert payment.payee_id == str(test_user_2.id)
        assert payment.amount == Decimal("75.00")
        assert payment.payment_method == PaymentMethod.BANK_TRANSFER
        assert payment.description == "Test reimbursement"
        assert payment.reference_number == "BANK123"
    
    def test_payment_methods_management(self, db_session, test_household, test_user, test_user_2):
        """Test payment method management."""
        from app.modules.expenses.models.payment import Payment, PaymentType, PaymentMethod
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            payment_type=PaymentType.REIMBURSEMENT
        )
        db_session.add(payment)
        db_session.commit()
        
        # Set payment method
        payment.set_payment_method(PaymentMethod.CREDIT_CARD, "CARD123")
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.reference_number == "CARD123"
        
        # Add description
        payment.add_description("Updated description")
        assert payment.description == "Updated description"
    
    def test_payment_repr(self, db_session, test_household, test_user, test_user_2):
        """Test payment string representation."""
        from app.modules.expenses.models.payment import Payment, PaymentType
        
        payment = Payment(
            household_id=test_household.id,
            payer_id=test_user.id,
            payee_id=test_user_2.id,
            amount=Decimal("50.00"),
            payment_type=PaymentType.REIMBURSEMENT
        )
        db_session.add(payment)
        db_session.commit()
        
        repr_str = repr(payment)
        assert "50.00" in repr_str
        assert "USD" in repr_str
        assert "reimbursement" in repr_str


class TestExpenseSharePaymentModel:
    """Test cases for ExpenseSharePayment model."""
    
    def test_expense_share_payment_creation(self, db_session, test_payment, test_expense_share):
        """Test basic expense share payment creation."""
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
        esp = ExpenseSharePayment(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("25.00"),
            is_active=True
        )
        db_session.add(esp)
        db_session.commit()
        
        assert esp.id is not None
        assert esp.payment_id == test_payment.id
        assert esp.expense_share_id == test_expense_share.id
        assert esp.amount == Decimal("25.00")
        assert esp.is_active is True
        assert esp.allocated_at is not None
        assert esp.created_at is not None
    
    def test_expense_share_payment_properties(self, db_session, test_payment, test_expense_share):
        """Test expense share payment properties."""
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
        # Create with partial payment
        esp = ExpenseSharePayment(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("15.00"),  # Less than full share amount
            is_active=True
        )
        db_session.add(esp)
        db_session.commit()
        
        # Test amount decimal property
        assert esp.amount_decimal == Decimal("15.00")
        
        # Test formatted amount
        assert "$15.00" in esp.formatted_amount
        
        # Test coverage properties
        assert esp.covers_full_share is False
        coverage_pct = esp.coverage_percentage
        assert coverage_pct is not None
        assert coverage_pct < Decimal("100")
        
        # Test with full payment
        esp.amount = test_expense_share.share_amount
        assert esp.covers_full_share is True
        assert esp.coverage_percentage == Decimal("100")
    
    def test_expense_share_payment_amount_updates(self, db_session, test_payment, test_expense_share):
        """Test amount update functionality."""
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
        esp = ExpenseSharePayment(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("10.00"),
            is_active=True
        )
        db_session.add(esp)
        db_session.commit()
        
        original_allocated_at = esp.allocated_at
        
        # Update amount
        esp.update_amount(Decimal("20.00"))
        assert esp.amount == Decimal("20.00")
        assert esp.allocated_at > original_allocated_at
    
    def test_expense_share_payment_class_methods(self, test_payment, test_expense_share):
        """Test class methods."""
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
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
        
        assert esp_full.amount == test_expense_share.share_amount_decimal
    
    def test_expense_share_payment_repr(self, db_session, test_payment, test_expense_share):
        """Test string representation."""
        from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
        
        esp = ExpenseSharePayment(
            payment_id=test_payment.id,
            expense_share_id=test_expense_share.id,
            amount=Decimal("25.00")
        )
        db_session.add(esp)
        db_session.commit()
        
        repr_str = repr(esp)
        assert str(test_payment.id) in repr_str
        assert str(test_expense_share.id) in repr_str
        assert "25.00" in repr_str


# Fixtures for testing
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
def test_household(db_session, test_user):
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
    return household


@pytest.fixture
def test_user_household(db_session, test_user, test_household):
    """Create a test user household relationship."""
    user_household = UserHousehold(
        user_id=test_user.id,
        household_id=test_household.id,
        role=UserHouseholdRole.ADMIN,
        nickname="Test Admin",
        is_active=True
    )
    db_session.add(user_household)
    db_session.commit()
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