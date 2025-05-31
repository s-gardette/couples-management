"""
Expense service for managing expenses and their operations.
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, desc, asc, func, String
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.services.base_service import BaseService
from app.core.utils.helpers import split_amount_equally, format_currency
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.household import Household
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.category import Category

logger = logging.getLogger(__name__)


class ExpenseService(BaseService[Expense, dict, dict]):
    """Service for expense management operations."""

    def __init__(self, db: Session):
        super().__init__(Expense)
        self.db = db

    async def create_expense(
        self,
        household_id: UUID,
        created_by: UUID,
        title: str,
        amount: Decimal,
        category_id: Optional[UUID] = None,
        description: Optional[str] = None,
        expense_date: Optional[date] = None,
        currency: str = "USD",
        tags: Optional[List[str]] = None,
        receipt_url: Optional[str] = None,
        split_method: str = "equal",
        custom_splits: Optional[Dict[str, Decimal]] = None
    ) -> Tuple[bool, str, Optional[Expense]]:
        """
        Create a new expense with automatic splitting.

        Args:
            household_id: Household ID
            created_by: User ID creating the expense
            title: Expense title
            amount: Expense amount
            category_id: Optional category ID
            description: Optional description
            expense_date: Date of expense (defaults to today)
            currency: Currency code
            tags: Optional list of tags
            receipt_url: Optional receipt URL
            split_method: How to split the expense (equal, custom)
            custom_splits: Custom split amounts if split_method is 'custom'

        Returns:
            Tuple of (success, message, expense_object)
        """
        try:
            # Validate household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == created_by,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", None

            # Validate category if provided
            if category_id:
                category = (
                    self.db.query(Category)
                    .filter(
                        Category.id == category_id,
                        or_(
                            Category.household_id == household_id,
                            Category.household_id.is_(None)  # Global category
                        )
                    )
                    .first()
                )
                if not category:
                    return False, "Invalid category", None

            # Create expense
            expense = Expense(
                household_id=household_id,
                created_by=created_by,
                title=title.strip(),
                description=description.strip() if description else None,
                amount=amount,
                currency=currency,
                category_id=category_id,
                expense_date=expense_date or date.today(),
                receipt_url=receipt_url,
                tags=tags or [],
                is_active=True
            )

            self.db.add(expense)
            self.db.flush()  # Get the expense ID

            # Create expense shares
            success, message = await self._create_expense_shares(
                expense, split_method, custom_splits
            )

            if not success:
                self.db.rollback()
                return False, message, None

            self.db.commit()
            logger.info(f"Created expense {expense.id} in household {household_id}")

            # Reload expense with all relationships for proper response serialization
            expense = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.category),
                    joinedload(Expense.creator),
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user),
                    joinedload(Expense.household)
                )
                .filter(Expense.id == expense.id)
                .first()
            )

            return True, "Expense created successfully", expense

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating expense: {e}")
            return False, "Failed to create expense due to data conflict", None
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating expense: {e}")
            return False, f"Failed to create expense: {str(e)}", None

    async def get_household_expenses(
        self,
        household_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "expense_date",
        sort_order: str = "desc"
    ) -> Tuple[bool, str, List[Expense]]:
        """
        Get expenses for a household with filtering and pagination.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            skip: Number of records to skip
            limit: Maximum number of records
            filters: Optional filters
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Tuple of (success, message, expenses_list)
        """
        try:
            # Verify household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", []

            # Build query
            query = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.category),
                    joinedload(Expense.creator),
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user)
                )
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
            )

            # Apply filters
            if filters:
                query = self._apply_expense_filters(query, filters)

            # Apply sorting
            if hasattr(Expense, sort_by):
                sort_column = getattr(Expense, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))

            # Apply pagination
            expenses = query.offset(skip).limit(limit).all()

            return True, "Expenses retrieved successfully", expenses

        except Exception as e:
            logger.error(f"Error getting household expenses: {e}")
            return False, f"Failed to get expenses: {str(e)}", []

    async def get_expense_details(
        self,
        expense_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, str, Optional[Expense]]:
        """
        Get detailed expense information.

        Args:
            expense_id: Expense ID
            user_id: User ID (for permission check)

        Returns:
            Tuple of (success, message, expense_object)
        """
        try:
            expense = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.category),
                    joinedload(Expense.creator),
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user),
                    joinedload(Expense.household)
                )
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Verify household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to view this expense", None

            return True, "Expense retrieved successfully", expense

        except Exception as e:
            logger.error(f"Error getting expense details: {e}")
            return False, f"Failed to get expense: {str(e)}", None

    async def get_user_recent_expenses(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> Tuple[bool, str, List[Expense]]:
        """
        Get recent expenses across all user's households.

        Args:
            user_id: User ID
            limit: Maximum number of expenses to return

        Returns:
            Tuple of (success, message, expenses_list)
        """
        try:
            # Get all households the user is a member of
            user_households = (
                self.db.query(UserHousehold.household_id)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.is_active == True
                )
                .subquery()
            )

            # Get recent expenses from all user's households
            expenses = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.category),
                    joinedload(Expense.creator),
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user),
                    joinedload(Expense.household)
                )
                .filter(
                    Expense.household_id.in_(user_households),
                    Expense.is_active == True
                )
                .order_by(Expense.created_at.desc())
                .limit(limit)
                .all()
            )

            return True, "Recent expenses retrieved successfully", expenses

        except Exception as e:
            logger.error(f"Error getting user recent expenses: {e}")
            return False, f"Failed to get recent expenses: {str(e)}", []

    async def update_expense(
        self,
        expense_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any],
        recalculate_splits: bool = False
    ) -> Tuple[bool, str, Optional[Expense]]:
        """
        Update an expense.

        Args:
            expense_id: Expense ID
            user_id: User ID (must be creator or admin)
            updates: Dictionary of fields to update
            recalculate_splits: Whether to recalculate splits if amount changed

        Returns:
            Tuple of (success, message, expense_object)
        """
        try:
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Check permissions (creator or admin)
            if expense.created_by != user_id:
                admin_membership = (
                    self.db.query(UserHousehold)
                    .filter(
                        UserHousehold.user_id == user_id,
                        UserHousehold.household_id == expense.household_id,
                        UserHousehold.role == "admin",
                        UserHousehold.is_active == True
                    )
                    .first()
                )
                if not admin_membership:
                    return False, "You don't have permission to edit this expense", None

            # Validate category if being updated
            if "category_id" in updates and updates["category_id"]:
                category = (
                    self.db.query(Category)
                    .filter(
                        Category.id == updates["category_id"],
                        or_(
                            Category.household_id == expense.household_id,
                            Category.household_id.is_(None)
                        )
                    )
                    .first()
                )
                if not category:
                    return False, "Invalid category", None

            # Store old amount for split recalculation
            old_amount = expense.amount
            amount_changed = "amount" in updates and updates["amount"] != old_amount

            # Update expense fields
            for field, value in updates.items():
                if hasattr(expense, field) and field not in ["id", "created_at", "household_id"]:
                    setattr(expense, field, value)

            # Recalculate splits if amount changed and requested
            if amount_changed and recalculate_splits:
                await self._recalculate_expense_shares(expense)

            self.db.commit()
            logger.info(f"Updated expense {expense_id}")

            return True, "Expense updated successfully", expense

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating expense: {e}")
            return False, f"Failed to update expense: {str(e)}", None

    async def delete_expense(
        self,
        expense_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, str]:
        """
        Delete (soft delete) an expense.

        Args:
            expense_id: Expense ID
            user_id: User ID (must be creator or admin)

        Returns:
            Tuple of (success, message)
        """
        try:
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found"

            # Check permissions (creator or admin)
            if expense.created_by != user_id:
                admin_membership = (
                    self.db.query(UserHousehold)
                    .filter(
                        UserHousehold.user_id == user_id,
                        UserHousehold.household_id == expense.household_id,
                        UserHousehold.role == "admin",
                        UserHousehold.is_active == True
                    )
                    .first()
                )
                if not admin_membership:
                    return False, "You don't have permission to delete this expense"

            # Soft delete expense and shares
            expense.is_active = False
            for share in expense.shares:
                share.is_active = False

            self.db.commit()
            logger.info(f"Deleted expense {expense_id}")

            return True, "Expense deleted successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting expense: {e}")
            return False, f"Failed to delete expense: {str(e)}"

    async def upload_receipt(
        self,
        expense_id: UUID,
        user_id: UUID,
        receipt_url: str
    ) -> Tuple[bool, str, Optional[Expense]]:
        """
        Upload a receipt for an expense.

        Args:
            expense_id: Expense ID
            user_id: User ID (must be creator or admin)
            receipt_url: URL of the uploaded receipt

        Returns:
            Tuple of (success, message, expense_object)
        """
        try:
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Check permissions (creator or admin)
            if expense.created_by != user_id:
                admin_membership = (
                    self.db.query(UserHousehold)
                    .filter(
                        UserHousehold.user_id == user_id,
                        UserHousehold.household_id == expense.household_id,
                        UserHousehold.role == "admin",
                        UserHousehold.is_active == True
                    )
                    .first()
                )
                if not admin_membership:
                    return False, "You don't have permission to upload receipt", None

            expense.receipt_url = receipt_url
            self.db.commit()

            logger.info(f"Uploaded receipt for expense {expense_id}")
            return True, "Receipt uploaded successfully", expense

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error uploading receipt: {e}")
            return False, f"Failed to upload receipt: {str(e)}", None

    async def search_expenses(
        self,
        household_id: UUID,
        user_id: UUID,
        search_term: str,
        limit: int = 20
    ) -> Tuple[bool, str, List[Expense]]:
        """
        Search expenses by title, description, or tags.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            search_term: Search term
            limit: Maximum number of results

        Returns:
            Tuple of (success, message, expenses_list)
        """
        try:
            # Verify household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", []

            search_pattern = f"%{search_term.lower()}%"

            expenses = (
                self.db.query(Expense)
                .options(joinedload(Expense.category), joinedload(Expense.creator))
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    or_(
                        func.lower(Expense.title).like(search_pattern),
                        func.lower(Expense.description).like(search_pattern),
                        func.lower(func.cast(Expense.tags, String)).like(search_pattern)
                    )
                )
                .order_by(desc(Expense.expense_date))
                .limit(limit)
                .all()
            )

            return True, "Search completed successfully", expenses

        except Exception as e:
            logger.error(f"Error searching expenses: {e}")
            return False, f"Search failed: {str(e)}", []

    async def get_expense_summary(
        self,
        household_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get expense summary for a household.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (success, message, summary_dict)
        """
        try:
            # Verify household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", {}

            # Build base query
            query = (
                self.db.query(Expense)
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
            )

            # Apply date filters
            if start_date:
                query = query.filter(Expense.expense_date >= start_date)
            if end_date:
                query = query.filter(Expense.expense_date <= end_date)

            expenses = query.all()

            # Calculate summary
            total_amount = sum(expense.amount for expense in expenses)
            expense_count = len(expenses)
            
            # Calculate paid/unpaid amounts
            paid_amount = 0
            unpaid_amount = 0
            for expense in expenses:
                expense_shares = (
                    self.db.query(ExpenseShare)
                    .filter(
                        ExpenseShare.expense_id == expense.id,
                        ExpenseShare.is_active == True
                    )
                    .all()
                )
                
                if all(share.is_paid for share in expense_shares):
                    paid_amount += expense.amount
                else:
                    unpaid_amount += expense.amount
            
            # Group by category
            category_totals = {}
            for expense in expenses:
                category_name = expense.category.name if expense.category else "Uncategorized"
                category_totals[category_name] = {
                    "total": float(category_totals.get(category_name, {}).get("total", 0) + expense.amount),
                    "count": category_totals.get(category_name, {}).get("count", 0) + 1
                }

            # Group by month
            monthly_totals = {}
            for expense in expenses:
                month_key = expense.expense_date.strftime("%Y-%m")
                monthly_totals[month_key] = monthly_totals.get(month_key, 0) + expense.amount

            # Group by user
            user_totals = {}
            for expense in expenses:
                expense_shares = (
                    self.db.query(ExpenseShare)
                    .options(joinedload(ExpenseShare.user_household).joinedload(UserHousehold.user))
                    .filter(
                        ExpenseShare.expense_id == expense.id,
                        ExpenseShare.is_active == True
                    )
                    .all()
                )
                
                for share in expense_shares:
                    if share.user_household and share.user_household.user:
                        username = share.user_household.user.username
                        if username not in user_totals:
                            user_totals[username] = {"total": 0, "count": 0, "paid": 0, "unpaid": 0}
                        
                        user_totals[username]["total"] += float(share.share_amount)
                        user_totals[username]["count"] += 1
                        
                        if share.is_paid:
                            user_totals[username]["paid"] += float(share.share_amount)
                        else:
                            user_totals[username]["unpaid"] += float(share.share_amount)

            summary = {
                "total_expenses": expense_count,
                "total_amount": float(total_amount),
                "paid_amount": float(paid_amount),
                "unpaid_amount": float(unpaid_amount),
                "average_expense": float(total_amount / expense_count) if expense_count > 0 else 0,
                "categories_breakdown": category_totals,
                "monthly_breakdown": {k: float(v) for k, v in monthly_totals.items()},
                "user_breakdown": user_totals
            }

            return True, "Summary generated successfully", summary

        except Exception as e:
            logger.error(f"Error generating expense summary: {e}")
            return False, f"Failed to generate summary: {str(e)}", {}

    def _apply_expense_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to expense query."""
        if "category_id" in filters and filters["category_id"]:
            query = query.filter(Expense.category_id == filters["category_id"])

        if "created_by" in filters and filters["created_by"]:
            query = query.filter(Expense.created_by == filters["created_by"])

        if "start_date" in filters and filters["start_date"]:
            query = query.filter(Expense.expense_date >= filters["start_date"])

        if "end_date" in filters and filters["end_date"]:
            query = query.filter(Expense.expense_date <= filters["end_date"])

        if "min_amount" in filters and filters["min_amount"]:
            query = query.filter(Expense.amount >= filters["min_amount"])

        if "max_amount" in filters and filters["max_amount"]:
            query = query.filter(Expense.amount <= filters["max_amount"])

        if "tags" in filters and filters["tags"]:
            # Filter by tags (assuming tags is stored as JSON array)
            for tag in filters["tags"]:
                query = query.filter(func.json_contains(Expense.tags, f'"{tag}"'))

        return query

    async def _create_expense_shares(
        self,
        expense: Expense,
        split_method: str,
        custom_splits: Optional[Dict[str, Decimal]] = None
    ) -> Tuple[bool, str]:
        """Create expense shares based on split method."""
        try:
            # Get active household members
            members = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .all()
            )

            if not members:
                return False, "No active members found in household"

            if split_method == "equal":
                # Equal split among all members
                share_amounts = split_amount_equally(expense.amount, len(members))
                
                for i, member in enumerate(members):
                    share = ExpenseShare(
                        expense_id=expense.id,
                        user_household_id=member.id,
                        share_amount=share_amounts[i],
                        share_percentage=Decimal("100") / len(members),
                        is_paid=False
                    )
                    self.db.add(share)

            elif split_method == "custom" and custom_splits:
                # Custom split amounts
                total_custom = sum(custom_splits.values())
                if total_custom != expense.amount:
                    return False, f"Custom splits total ({total_custom}) doesn't match expense amount ({expense.amount})"

                for member in members:
                    member_key = str(member.user_id)
                    if member_key in custom_splits:
                        share_amount = custom_splits[member_key]
                        share_percentage = (share_amount / expense.amount) * 100

                        share = ExpenseShare(
                            expense_id=expense.id,
                            user_household_id=member.id,
                            share_amount=share_amount,
                            share_percentage=share_percentage,
                            is_paid=False
                        )
                        self.db.add(share)

            else:
                return False, "Invalid split method or missing custom splits"

            return True, "Expense shares created successfully"

        except Exception as e:
            logger.error(f"Error creating expense shares: {e}")
            return False, f"Failed to create expense shares: {str(e)}"

    async def _recalculate_expense_shares(self, expense: Expense) -> None:
        """Recalculate expense shares when amount changes."""
        try:
            # Get existing shares
            shares = (
                self.db.query(ExpenseShare)
                .filter(
                    ExpenseShare.expense_id == expense.id,
                    ExpenseShare.is_active == True
                )
                .all()
            )

            if not shares:
                return

            # Recalculate based on existing percentages
            for share in shares:
                if share.share_percentage:
                    new_amount = (expense.amount * share.share_percentage) / 100
                    share.share_amount = new_amount

        except Exception as e:
            logger.error(f"Error recalculating expense shares: {e}")
            raise 