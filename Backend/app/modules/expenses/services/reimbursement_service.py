"""
Reimbursement service for handling the three reimbursement workflows.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.core.services.base_service import BaseService
from app.modules.expenses.models.payment import Payment, PaymentType, PaymentMethod
from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.household import Household
from app.modules.expenses.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class ReimbursementService:
    """Service for managing reimbursement workflows."""

    def __init__(self, db: Session):
        self.db = db
        self.payment_service = PaymentService(db)

    async def reimburse_expense_directly(
        self,
        expense_id: UUID,
        payer_id: UUID,
        current_user_id: UUID,
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Payment]]:
        """
        Workflow 1: Reimburse one expense directly and close it.
        
        Args:
            expense_id: ID of the expense to reimburse
            payer_id: ID of user making the payment
            current_user_id: ID of user executing the action
            payment_method: Payment method used
            description: Optional payment description
            reference_number: Optional reference number
            
        Returns:
            Tuple of (success, message, payment)
        """
        try:
            # Get expense with shares
            expense = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household),
                    joinedload(Expense.household),
                    joinedload(Expense.creator)
                )
                .filter(Expense.id == expense_id, Expense.is_active == True)
                .first()
            )

            if not expense:
                return False, "Expense not found", None

            # Validate permissions
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == expense.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", None

            # Check if expense is already fully paid
            if expense.is_fully_paid:
                return False, "Expense is already fully paid", None

            # Get unpaid shares
            unpaid_shares = expense.get_unpaid_shares()
            if not unpaid_shares:
                return False, "No unpaid shares found for this expense", None

            # Calculate total amount to pay
            total_amount = sum(share.share_amount_decimal for share in unpaid_shares)

            # Determine payee (expense creator)
            payee_id = expense.created_by
            if not payee_id:
                return False, "Cannot determine expense creator for payment", None

            # Create payment description if not provided
            if not description:
                description = f"Reimbursement for expense: {expense.title}"

            # Create payment
            success, message, payment = await self.payment_service.create_payment(
                household_id=expense.household_id,
                payer_id=payer_id,
                payee_id=payee_id,
                amount=total_amount,
                payment_type=PaymentType.EXPENSE_PAYMENT,
                current_user_id=current_user_id,
                currency=expense.currency,
                payment_method=payment_method,
                description=description,
                reference_number=reference_number
            )

            if not success:
                return False, message, None

            # Link payment to all unpaid shares
            for share in unpaid_shares:
                esp = ExpenseSharePayment.create_full_allocation(
                    payment_id=payment.id,
                    expense_share=share
                )
                self.db.add(esp)

                # Mark share as paid
                share.mark_as_paid(
                    payment_method=payment_method.value if payment_method else None,
                    payment_notes=f"Paid via reimbursement payment {payment.id}"
                )

            self.db.commit()

            logger.info(f"Successfully reimbursed expense {expense_id} with payment {payment.id}")
            return True, "Expense reimbursed successfully", payment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error reimbursing expense {expense_id}: {e}")
            return False, f"Failed to reimburse expense: {str(e)}", None

    async def pay_all_user_expenses(
        self,
        household_id: UUID,
        target_user_id: UUID,
        payer_id: UUID,
        current_user_id: UUID,
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Payment]]:
        """
        Workflow 2: Pay all open expenses for a user and close them.
        
        Args:
            household_id: Household ID
            target_user_id: ID of user whose expenses to pay
            payer_id: ID of user making the payment
            current_user_id: ID of user executing the action
            payment_method: Payment method used
            description: Optional payment description
            reference_number: Optional reference number
            
        Returns:
            Tuple of (success, message, payment)
        """
        try:
            # Validate permissions
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", None

            # Get target user's membership
            target_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == target_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not target_membership:
                return False, "Target user is not a member of this household", None

            # Get all unpaid expense shares for the target user in this household
            unpaid_shares = (
                self.db.query(ExpenseShare)
                .join(Expense)
                .options(
                    joinedload(ExpenseShare.expense),
                    joinedload(ExpenseShare.user_household)
                )
                .filter(
                    ExpenseShare.user_household_id == target_membership.id,
                    ExpenseShare.is_paid == False,
                    ExpenseShare.is_active == True,
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
                .all()
            )

            if not unpaid_shares:
                return False, "No unpaid expenses found for this user", None

            # Calculate total amount
            total_amount = sum(share.share_amount_decimal for share in unpaid_shares)

            # Create payment description if not provided
            if not description:
                user_name = target_membership.user.username if target_membership.user else "user"
                description = f"Bulk payment for all expenses owed by {user_name}"

            # Create payment
            success, message, payment = await self.payment_service.create_payment(
                household_id=household_id,
                payer_id=payer_id,
                payee_id=target_user_id,
                amount=total_amount,
                payment_type=PaymentType.EXPENSE_PAYMENT,
                current_user_id=current_user_id,
                currency="USD",  # TODO: Get household default currency
                payment_method=payment_method,
                description=description,
                reference_number=reference_number
            )

            if not success:
                return False, message, None

            # Link payment to all unpaid shares and mark them as paid
            for share in unpaid_shares:
                esp = ExpenseSharePayment.create_full_allocation(
                    payment_id=payment.id,
                    expense_share=share
                )
                self.db.add(esp)

                # Mark share as paid
                share.mark_as_paid(
                    payment_method=payment_method.value if payment_method else None,
                    payment_notes=f"Paid via bulk payment {payment.id}"
                )

            self.db.commit()

            logger.info(f"Successfully paid all expenses for user {target_user_id} with payment {payment.id}")
            return True, f"All expenses paid successfully. Total: {payment.formatted_amount}", payment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error paying all expenses for user {target_user_id}: {e}")
            return False, f"Failed to pay all expenses: {str(e)}", None

    async def make_general_payment(
        self,
        household_id: UUID,
        payer_id: UUID,
        payee_id: UUID,
        amount: Decimal,
        current_user_id: UUID,
        expense_allocations: Optional[List[Dict[str, Any]]] = None,
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Payment]]:
        """
        Workflow 3: Pay a certain amount that adjusts balance, optionally linking expenses.
        
        Args:
            household_id: Household ID
            payer_id: ID of user making the payment
            payee_id: ID of user receiving the payment
            amount: Total payment amount
            current_user_id: ID of user executing the action
            expense_allocations: Optional list of {"expense_share_id": UUID, "amount": Decimal}
            payment_method: Payment method used
            description: Optional payment description
            reference_number: Optional reference number
            
        Returns:
            Tuple of (success, message, payment)
        """
        try:
            # Validate permissions
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", None

            # Create payment description if not provided
            if not description:
                description = f"General payment from {payer_id} to {payee_id}"

            # Create payment
            success, message, payment = await self.payment_service.create_payment(
                household_id=household_id,
                payer_id=payer_id,
                payee_id=payee_id,
                amount=amount,
                payment_type=PaymentType.REIMBURSEMENT,
                current_user_id=current_user_id,
                currency="USD",  # TODO: Get household default currency
                payment_method=payment_method,
                description=description,
                reference_number=reference_number
            )

            if not success:
                return False, message, None

            # Handle expense allocations if provided
            if expense_allocations:
                total_allocated = Decimal('0')
                
                for allocation in expense_allocations:
                    expense_share_id = allocation.get("expense_share_id")
                    allocation_amount = Decimal(str(allocation.get("amount", 0)))
                    
                    if allocation_amount <= 0:
                        continue
                    
                    # Validate allocation amount doesn't exceed payment amount
                    if total_allocated + allocation_amount > amount:
                        self.db.rollback()
                        return False, "Total allocations exceed payment amount", None
                    
                    # Get expense share
                    expense_share = (
                        self.db.query(ExpenseShare)
                        .join(Expense)
                        .filter(
                            ExpenseShare.id == expense_share_id,
                            ExpenseShare.is_active == True,
                            Expense.household_id == household_id,
                            Expense.is_active == True
                        )
                        .first()
                    )
                    
                    if not expense_share:
                        self.db.rollback()
                        return False, f"Expense share {expense_share_id} not found", None
                    
                    # Create allocation
                    esp = ExpenseSharePayment.create_allocation(
                        payment_id=payment.id,
                        expense_share_id=expense_share_id,
                        amount=allocation_amount
                    )
                    self.db.add(esp)
                    
                    # If allocation covers the full share amount, mark as paid
                    if allocation_amount >= expense_share.share_amount_decimal:
                        expense_share.mark_as_paid(
                            payment_method=payment_method.value if payment_method else None,
                            payment_notes=f"Paid via general payment {payment.id}"
                        )
                    
                    total_allocated += allocation_amount

            self.db.commit()

            unallocated_amount = amount - (total_allocated if expense_allocations else Decimal('0'))
            allocation_message = ""
            if expense_allocations:
                allocation_message = f" (${total_allocated:.2f} allocated to expenses, ${unallocated_amount:.2f} unallocated)"

            logger.info(f"Successfully created general payment {payment.id}")
            return True, f"Payment created successfully{allocation_message}", payment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating general payment: {e}")
            return False, f"Failed to create payment: {str(e)}", None

    async def get_unpaid_expenses_for_user(
        self,
        household_id: UUID,
        user_id: UUID,
        current_user_id: UUID
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Get all unpaid expenses for a specific user in a household.
        
        Args:
            household_id: Household ID
            user_id: User ID to get unpaid expenses for
            current_user_id: ID of user making the request
            
        Returns:
            Tuple of (success, message, expenses_list)
        """
        try:
            # Validate permissions
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You are not a member of this household", []

            # Get target user's membership
            target_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not target_membership:
                return False, "Target user is not a member of this household", []

            # Get unpaid expense shares
            unpaid_shares = (
                self.db.query(ExpenseShare)
                .join(Expense)
                .options(
                    joinedload(ExpenseShare.expense).joinedload(Expense.category),
                    joinedload(ExpenseShare.user_household)
                )
                .filter(
                    ExpenseShare.user_household_id == target_membership.id,
                    ExpenseShare.is_paid == False,
                    ExpenseShare.is_active == True,
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
                .order_by(Expense.expense_date.desc())
                .all()
            )

            # Format response
            expenses_data = []
            for share in unpaid_shares:
                expense = share.expense
                expenses_data.append({
                    "expense_id": str(expense.id),
                    "expense_share_id": str(share.id),
                    "title": expense.title,
                    "description": expense.description,
                    "total_amount": float(expense.amount),
                    "share_amount": float(share.share_amount),
                    "currency": expense.currency,
                    "expense_date": expense.expense_date.isoformat(),
                    "category": expense.category.name if expense.category else "Uncategorized",
                    "formatted_share_amount": share.formatted_amount
                })

            total_owed = sum(share.share_amount_decimal for share in unpaid_shares)

            return True, "Unpaid expenses retrieved successfully", {
                "expenses": expenses_data,
                "total_owed": float(total_owed),
                "count": len(expenses_data)
            }

        except Exception as e:
            logger.error(f"Error getting unpaid expenses for user {user_id}: {e}")
            return False, f"Failed to retrieve unpaid expenses: {str(e)}", [] 