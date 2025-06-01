"""
Expenses module models.
"""

# Import User model first to make it available for relationships
from app.modules.auth.models.user import User

from .household import Household, UserHouseholdRole
from .user_household import UserHousehold
from .category import Category
from .expense import Expense
from .expense_share import ExpenseShare
from .payment import Payment, PaymentType, PaymentMethod
from .expense_share_payment import ExpenseSharePayment

__all__ = [
    "User",  # Make User available for relationships
    "Household",
    "UserHousehold", 
    "UserHouseholdRole",
    "Category",
    "Expense",
    "ExpenseShare",
    "Payment",
    "PaymentType", 
    "PaymentMethod",
    "ExpenseSharePayment",
]
