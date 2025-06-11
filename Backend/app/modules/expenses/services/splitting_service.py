"""
Splitting service for managing expense splits and calculations.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.services.base_service import BaseService
from app.core.utils.helpers import split_amount_equally
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.user_household import UserHousehold

logger = logging.getLogger(__name__)


class SplittingService(BaseService[ExpenseShare, dict, dict]):
    """Service for expense splitting operations."""

    def __init__(self, db: Session):
        super().__init__(ExpenseShare)
        self.db = db

    async def calculate_equal_split(
        self,
        amount: Decimal,
        member_count: int
    ) -> Tuple[bool, str, List[Decimal]]:
        """
        Calculate equal split amounts for an expense.

        Args:
            amount: Total expense amount
            member_count: Number of members to split between

        Returns:
            Tuple of (success, message, split_amounts_list)
        """
        try:
            if member_count <= 0:
                return False, "Member count must be greater than 0", []

            if amount <= 0:
                return False, "Amount must be greater than 0", []

            split_amounts = split_amount_equally(amount, member_count)
            return True, "Equal split calculated successfully", split_amounts

        except Exception as e:
            logger.error(f"Error calculating equal split: {e}")
            return False, f"Failed to calculate split: {str(e)}", []

    async def calculate_percentage_split(
        self,
        amount: Decimal,
        percentages: Dict[str, Decimal]
    ) -> Tuple[bool, str, Dict[str, Decimal]]:
        """
        Calculate split amounts based on percentages.

        Args:
            amount: Total expense amount
            percentages: Dictionary of user_id -> percentage

        Returns:
            Tuple of (success, message, split_amounts_dict)
        """
        try:
            if amount <= 0:
                return False, "Amount must be greater than 0", {}

            # Validate percentages sum to 100
            total_percentage = sum(percentages.values())
            if abs(total_percentage - Decimal("100")) > Decimal("0.01"):
                return False, f"Percentages must sum to 100%, got {total_percentage}%", {}

            # Calculate amounts
            split_amounts = {}
            remaining_amount = amount
            
            # Calculate all but the last amount
            percentage_items = list(percentages.items())
            for i, (user_id, percentage) in enumerate(percentage_items[:-1]):
                split_amount = (amount * percentage / 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                split_amounts[user_id] = split_amount
                remaining_amount -= split_amount

            # Assign remaining amount to last user to handle rounding
            if percentage_items:
                last_user_id = percentage_items[-1][0]
                split_amounts[last_user_id] = remaining_amount

            return True, "Percentage split calculated successfully", split_amounts

        except Exception as e:
            logger.error(f"Error calculating percentage split: {e}")
            return False, f"Failed to calculate split: {str(e)}", {}

    async def validate_custom_split(
        self,
        amount: Decimal,
        custom_amounts: Dict[str, Decimal]
    ) -> Tuple[bool, str]:
        """
        Validate that custom split amounts sum to the total amount.

        Args:
            amount: Total expense amount
            custom_amounts: Dictionary of user_id -> amount

        Returns:
            Tuple of (success, message)
        """
        try:
            if amount <= 0:
                return False, "Amount must be greater than 0"

            if not custom_amounts:
                return False, "Custom amounts cannot be empty"

            # Check for negative amounts
            for user_id, split_amount in custom_amounts.items():
                if split_amount < 0:
                    return False, f"Split amount for user {user_id} cannot be negative"

            # Check if amounts sum to total
            total_split = sum(custom_amounts.values())
            if abs(total_split - amount) > Decimal("0.01"):
                return False, f"Split amounts ({total_split}) don't match expense amount ({amount})"

            return True, "Custom split validation passed"

        except Exception as e:
            logger.error(f"Error validating custom split: {e}")
            return False, f"Validation failed: {str(e)}"

    async def update_expense_splits(
        self,
        expense_id: UUID,
        user_id: UUID,
        split_method: str,
        split_data: Dict[str, Any]
    ) -> Tuple[bool, str, List[ExpenseShare]]:
        """
        Update the splits for an existing expense.

        Args:
            expense_id: Expense ID
            user_id: User ID (must be creator or admin)
            split_method: Split method (equal, percentage, custom)
            split_data: Split data based on method

        Returns:
            Tuple of (success, message, updated_shares_list)
        """
        try:
            # Get expense
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", []

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
                    return False, "You don't have permission to update splits", []

            # Get household members
            members = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .all()
            )

            if not members:
                return False, "No active members found in household", []

            # Calculate new splits based on method
            if split_method == "equal":
                success, message, split_amounts = await self.calculate_equal_split(
                    expense.amount, len(members)
                )
                if not success:
                    return False, message, []

                # Create split data for equal distribution
                new_splits = {}
                for i, member in enumerate(members):
                    new_splits[str(member.user_id)] = {
                        "amount": split_amounts[i],
                        "percentage": Decimal("100") / len(members)
                    }

            elif split_method == "percentage":
                percentages = split_data.get("percentages", {})
                success, message, split_amounts = await self.calculate_percentage_split(
                    expense.amount, percentages
                )
                if not success:
                    return False, message, []

                new_splits = {}
                for user_id, amount in split_amounts.items():
                    new_splits[user_id] = {
                        "amount": amount,
                        "percentage": percentages.get(user_id, Decimal("0"))
                    }

            elif split_method == "custom":
                custom_amounts = split_data.get("amounts", {})
                success, message = await self.validate_custom_split(
                    expense.amount, custom_amounts
                )
                if not success:
                    return False, message, []

                new_splits = {}
                for user_id, amount in custom_amounts.items():
                    percentage = (amount / expense.amount * 100) if expense.amount > 0 else Decimal("0")
                    new_splits[user_id] = {
                        "amount": amount,
                        "percentage": percentage
                    }

            else:
                return False, "Invalid split method", []

            # Update existing shares or create new ones
            updated_shares = await self._update_shares(expense, members, new_splits)

            self.db.commit()
            logger.info(f"Updated splits for expense {expense_id}")

            return True, "Expense splits updated successfully", updated_shares

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating expense splits: {e}")
            return False, f"Failed to update splits: {str(e)}", []

    async def mark_share_paid(
        self,
        expense_id: UUID,
        user_id: UUID,
        payer_user_id: UUID,
        payment_method: Optional[str] = None,
        payment_notes: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ExpenseShare]]:
        """
        Mark a user's share of an expense as paid.

        Args:
            expense_id: Expense ID
            user_id: User ID whose share is being marked as paid
            payer_user_id: User ID of the person marking it as paid
            payment_method: Optional payment method
            payment_notes: Optional payment notes

        Returns:
            Tuple of (success, message, expense_share_object)
        """
        try:
            # Get expense
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Verify payer has permission (member of household)
            payer_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == payer_user_id,
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not payer_membership:
                return False, "You are not a member of this household", None

            # Get user's membership to find the share
            user_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not user_membership:
                return False, "User is not a member of this household", None

            # Find the expense share
            share = (
                self.db.query(ExpenseShare)
                .filter(
                    ExpenseShare.expense_id == expense_id,
                    ExpenseShare.user_household_id == user_membership.id,
                    ExpenseShare.is_active == True
                )
                .first()
            )

            if not share:
                return False, "Expense share not found", None

            if share.is_paid:
                return False, "Share is already marked as paid", None

            # Mark as paid
            share.mark_as_paid(payment_method, payment_notes)
            self.db.commit()

            logger.info(f"Marked share as paid for user {user_id} in expense {expense_id}")
            return True, "Share marked as paid successfully", share

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking share as paid: {e}")
            return False, f"Failed to mark share as paid: {str(e)}", None

    async def mark_share_unpaid(
        self,
        expense_id: UUID,
        user_id: UUID,
        requester_user_id: UUID
    ) -> Tuple[bool, str, Optional[ExpenseShare]]:
        """
        Mark a user's share of an expense as unpaid.

        Args:
            expense_id: Expense ID
            user_id: User ID whose share is being marked as unpaid
            requester_user_id: User ID of the person making the request

        Returns:
            Tuple of (success, message, expense_share_object)
        """
        try:
            # Get expense
            expense = (
                self.db.query(Expense)
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Verify requester has permission (admin or the user themselves)
            if requester_user_id != user_id:
                admin_membership = (
                    self.db.query(UserHousehold)
                    .filter(
                        UserHousehold.user_id == requester_user_id,
                        UserHousehold.household_id == expense.household_id,
                        UserHousehold.role == "admin",
                        UserHousehold.is_active == True
                    )
                    .first()
                )
                if not admin_membership:
                    return False, "You don't have permission to mark this share as unpaid", None

            # Get user's membership to find the share
            user_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not user_membership:
                return False, "User is not a member of this household", None

            # Find the expense share
            share = (
                self.db.query(ExpenseShare)
                .filter(
                    ExpenseShare.expense_id == expense_id,
                    ExpenseShare.user_household_id == user_membership.id,
                    ExpenseShare.is_active == True
                )
                .first()
            )

            if not share:
                return False, "Expense share not found", None

            if not share.is_paid:
                return False, "Share is already marked as unpaid", None

            # Mark as unpaid
            share.mark_as_unpaid()
            self.db.commit()

            logger.info(f"Marked share as unpaid for user {user_id} in expense {expense_id}")
            return True, "Share marked as unpaid successfully", share

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking share as unpaid: {e}")
            return False, f"Failed to mark share as unpaid: {str(e)}", None

    async def get_user_balance(
        self,
        household_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Calculate a user's balance in a household (what they owe vs what they're owed).

        Args:
            household_id: Household ID
            user_id: User ID

        Returns:
            Tuple of (success, message, balance_dict)
        """
        try:
            # Verify user is member of household
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
                return False, "User is not a member of this household", {}

            # Get all expense shares for this user in the household
            shares = (
                self.db.query(ExpenseShare)
                .join(Expense)
                .filter(
                    ExpenseShare.user_household_id == membership.id,
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    ExpenseShare.is_active == True
                )
                .all()
            )

            # Calculate what user owes (unpaid shares)
            owes_amount = sum(
                share.share_amount for share in shares if not share.is_paid
            )

            # Get expenses created by this user
            created_expenses = (
                self.db.query(Expense)
                .filter(
                    Expense.created_by == user_id,
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
                .all()
            )

            # Calculate what user is owed (unpaid shares by others on their expenses)
            owed_amount = Decimal("0")
            for expense in created_expenses:
                unpaid_shares = (
                    self.db.query(ExpenseShare)
                    .join(UserHousehold)
                    .filter(
                        ExpenseShare.expense_id == expense.id,
                        ExpenseShare.is_paid == False,
                        ExpenseShare.is_active == True,
                        UserHousehold.user_id != user_id  # Exclude user's own share
                    )
                    .all()
                )
                owed_amount += sum(share.share_amount for share in unpaid_shares)

            # Calculate net balance
            net_balance = owed_amount - owes_amount

            balance_info = {
                "user_id": str(user_id),
                "household_id": str(household_id),
                "owes_amount": float(owes_amount),
                "owed_amount": float(owed_amount),
                "net_balance": float(net_balance),
                "status": "owes" if net_balance < 0 else "owed" if net_balance > 0 else "settled"
            }

            return True, "Balance calculated successfully", balance_info

        except Exception as e:
            logger.error(f"Error calculating user balance: {e}")
            return False, f"Failed to calculate balance: {str(e)}", {}

    async def get_household_balances(
        self,
        household_id: UUID,
        requester_user_id: UUID
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Get balance information for all members of a household.

        Args:
            household_id: Household ID
            requester_user_id: User ID making the request

        Returns:
            Tuple of (success, message, balances_list)
        """
        try:
            # Verify requester is member of household
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == requester_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", []

            # Get all household members
            members = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .all()
            )

            balances = []
            for member in members:
                success, message, balance_info = await self.get_user_balance(
                    household_id, member.user_id
                )
                if success:
                    # Add member info
                    balance_info["username"] = member.user.username if member.user else "Unknown"
                    balance_info["nickname"] = member.nickname
                    balances.append(balance_info)

            return True, "Household balances calculated successfully", balances

        except Exception as e:
            logger.error(f"Error calculating household balances: {e}")
            return False, f"Failed to calculate balances: {str(e)}", []

    async def _update_shares(
        self,
        expense: Expense,
        members: List[UserHousehold],
        new_splits: Dict[str, Dict[str, Decimal]]
    ) -> List[ExpenseShare]:
        """Update or create expense shares based on new split data."""
        try:
            # Get existing shares
            existing_shares = (
                self.db.query(ExpenseShare)
                .filter(
                    ExpenseShare.expense_id == expense.id,
                    ExpenseShare.is_active == True
                )
                .all()
            )

            # Create a map of existing shares by user_household_id
            existing_shares_map = {
                share.user_household_id: share for share in existing_shares
            }

            updated_shares = []

            # Update or create shares for each member
            for member in members:
                user_id_str = str(member.user_id)
                
                if user_id_str in new_splits:
                    split_data = new_splits[user_id_str]
                    
                    if member.id in existing_shares_map:
                        # Update existing share
                        share = existing_shares_map[member.id]
                        share.share_amount = split_data["amount"]
                        share.share_percentage = split_data["percentage"]
                    else:
                        # Create new share
                        share = ExpenseShare(
                            expense_id=expense.id,
                            user_household_id=member.id,
                            share_amount=split_data["amount"],
                            share_percentage=split_data["percentage"],
                            is_paid=False
                        )
                        self.db.add(share)
                    
                    updated_shares.append(share)
                else:
                    # Remove share if user not in new splits
                    if member.id in existing_shares_map:
                        existing_shares_map[member.id].is_active = False

            return updated_shares

        except Exception as e:
            logger.error(f"Error updating shares: {e}")
            raise 