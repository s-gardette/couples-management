"""
Payment service for managing payments and reimbursements.
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.exc import IntegrityError

from app.core.services.base_service import BaseService
from app.modules.expenses.models.payment import Payment, PaymentType, PaymentMethod
from app.modules.expenses.models.expense_share_payment import ExpenseSharePayment
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.household import Household

logger = logging.getLogger(__name__)


class PaymentService(BaseService[Payment, dict, dict]):
    """Service for payment management operations."""

    def __init__(self, db: Session):
        super().__init__(Payment)
        self.db = db

    async def create_payment(
        self,
        household_id: UUID,
        payer_id: UUID,
        payee_id: UUID,
        amount: Decimal,
        payment_type: PaymentType,
        current_user_id: UUID,
        currency: str = "USD",
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None,
        payment_date: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[Payment]]:
        """
        Create a new payment with validation.

        Args:
            household_id: Household ID
            payer_id: User ID who made the payment
            payee_id: User ID who received the payment
            amount: Payment amount
            payment_type: Type of payment
            current_user_id: ID of user creating the payment
            currency: Currency code
            payment_method: Optional payment method
            description: Optional description
            reference_number: Optional reference number
            payment_date: Optional payment date (defaults to now)

        Returns:
            Tuple of (success, message, payment)
        """
        try:
            # Validate household membership for current user
            current_user_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not current_user_membership:
                return False, "You are not a member of this household", None

            # Validate payer is household member
            payer_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == payer_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not payer_membership:
                return False, "Payer is not a member of this household", None

            # Validate payee is household member
            payee_membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == payee_id,
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not payee_membership:
                return False, "Payee is not a member of this household", None

            # Validate amount
            if amount <= 0:
                return False, "Payment amount must be greater than zero", None

            # Create payment
            payment = Payment(
                household_id=household_id,
                payer_id=payer_id,
                payee_id=payee_id,
                amount=amount,
                currency=currency,
                payment_type=payment_type,
                payment_method=payment_method,
                payment_date=payment_date or datetime.utcnow(),
                description=description,
                reference_number=reference_number,
                is_active=True
            )

            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)

            logger.info(f"Created payment {payment.id} for household {household_id}")
            return True, "Payment created successfully", payment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating payment: {e}")
            return False, f"Failed to create payment: {str(e)}", None

    async def get_payments(
        self,
        household_id: UUID,
        current_user_id: UUID,
        page: int = 1,
        per_page: int = 20,
        payer_id: Optional[UUID] = None,
        payee_id: Optional[UUID] = None,
        payment_type: Optional[PaymentType] = None,
        payment_method: Optional[PaymentMethod] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
        sort_by: str = "payment_date",
        sort_order: str = "desc"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get payments with filtering and pagination.

        Returns:
            Tuple of (success, message, result_dict)
        """
        try:
            # Validate household membership
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
                return False, "You are not a member of this household", {}

            # Build base query
            query = (
                self.db.query(Payment)
                .options(
                    joinedload(Payment.payer),
                    joinedload(Payment.payee),
                    joinedload(Payment.household)
                )
                .filter(
                    Payment.household_id == household_id,
                    Payment.is_active == True
                )
            )

            # Apply filters
            if payer_id:
                query = query.filter(Payment.payer_id == payer_id)

            if payee_id:
                query = query.filter(Payment.payee_id == payee_id)

            if payment_type:
                query = query.filter(Payment.payment_type == payment_type)

            if payment_method:
                query = query.filter(Payment.payment_method == payment_method)

            if start_date:
                query = query.filter(Payment.payment_date >= start_date)

            if end_date:
                query = query.filter(Payment.payment_date <= end_date)

            if min_amount:
                query = query.filter(Payment.amount >= min_amount)

            if max_amount:
                query = query.filter(Payment.amount <= max_amount)

            if search:
                query = query.filter(
                    or_(
                        Payment.description.ilike(f"%{search}%"),
                        Payment.reference_number.ilike(f"%{search}%")
                    )
                )

            # Apply sorting
            sort_column = getattr(Payment, sort_by, Payment.payment_date)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Get total count
            total = query.count()

            # Apply pagination
            offset = (page - 1) * per_page
            payments = query.offset(offset).limit(per_page).all()

            return True, "Payments retrieved successfully", {
                "payments": payments,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page
            }

        except Exception as e:
            logger.error(f"Error getting payments: {e}")
            return False, f"Failed to retrieve payments: {str(e)}", {}

    async def get_payment_by_id(
        self,
        payment_id: UUID,
        current_user_id: UUID
    ) -> Tuple[bool, str, Optional[Payment]]:
        """Get a payment by ID with permission check."""
        try:
            payment = (
                self.db.query(Payment)
                .options(
                    joinedload(Payment.payer),
                    joinedload(Payment.payee),
                    joinedload(Payment.household),
                    joinedload(Payment.expense_share_payments).joinedload(ExpenseSharePayment.expense_share)
                )
                .filter(Payment.id == payment_id, Payment.is_active == True)
                .first()
            )

            if not payment:
                return False, "Payment not found", None

            # Check household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == payment.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to view this payment", None

            return True, "Payment retrieved successfully", payment

        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {e}")
            return False, f"Failed to retrieve payment: {str(e)}", None

    async def get_payment_details(
        self,
        payment_id: UUID,
        current_user_id: UUID
    ) -> Tuple[bool, str, Optional[Payment]]:
        """Get payment details with full related data. Alias for get_payment_by_id."""
        return await self.get_payment_by_id(payment_id, current_user_id)

    async def update_payment(
        self,
        payment_id: UUID,
        current_user_id: UUID,
        updates: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Payment]]:
        """Update a payment with validation."""
        try:
            payment = (
                self.db.query(Payment)
                .filter(Payment.id == payment_id, Payment.is_active == True)
                .first()
            )

            if not payment:
                return False, "Payment not found", None

            # Check permission (user must be household member)
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == payment.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to update this payment", None

            # Validate and apply updates
            for field, value in updates.items():
                if hasattr(payment, field):
                    if field == "amount" and value <= 0:
                        return False, "Payment amount must be greater than zero", None
                    setattr(payment, field, value)

            payment.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(payment)

            logger.info(f"Updated payment {payment_id}")
            return True, "Payment updated successfully", payment

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating payment {payment_id}: {e}")
            return False, f"Failed to update payment: {str(e)}", None

    async def delete_payment(
        self,
        payment_id: UUID,
        current_user_id: UUID
    ) -> Tuple[bool, str]:
        """Soft delete a payment and revert linked expense shares to unpaid status."""
        try:
            payment = (
                self.db.query(Payment)
                .options(
                    joinedload(Payment.expense_share_payments).joinedload(ExpenseSharePayment.expense_share)
                )
                .filter(Payment.id == payment_id, Payment.is_active == True)
                .first()
            )

            if not payment:
                return False, "Payment not found"

            # Check permission
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == payment.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to delete this payment"

            # CRITICAL: Revert all linked expense shares to unpaid status
            affected_shares = []
            for esp in payment.expense_share_payments:
                if esp.is_active and esp.expense_share and esp.expense_share.is_active:
                    expense_share = esp.expense_share
                    
                    # Check if this expense share has other active payments
                    other_payments = (
                        self.db.query(ExpenseSharePayment)
                        .filter(
                            ExpenseSharePayment.expense_share_id == expense_share.id,
                            ExpenseSharePayment.payment_id != payment_id,
                            ExpenseSharePayment.is_active == True
                        )
                        .count()
                    )
                    
                    # If no other payments, mark as unpaid
                    if other_payments == 0:
                        expense_share.mark_as_unpaid()
                        affected_shares.append(expense_share.id)
                        logger.info(f"Reverted expense share {expense_share.id} to unpaid status due to payment deletion")

            # Soft delete payment and related expense share payments
            payment.is_active = False
            payment.updated_at = datetime.utcnow()

            for esp in payment.expense_share_payments:
                esp.is_active = False
                esp.updated_at = datetime.utcnow()

            self.db.commit()

            affected_count = len(affected_shares)
            logger.info(f"Deleted payment {payment_id} and reverted {affected_count} expense shares to unpaid status")
            
            success_message = f"Payment deleted successfully"
            if affected_count > 0:
                success_message += f" and {affected_count} expense share(s) reverted to unpaid status"
                
            return True, success_message

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting payment {payment_id}: {e}")
            return False, f"Failed to delete payment: {str(e)}"

    async def link_expense_share(
        self,
        payment_id: UUID,
        expense_share_id: UUID,
        amount: Decimal,
        current_user_id: UUID
    ) -> Tuple[bool, str, Optional[ExpenseSharePayment]]:
        """Link a payment to an expense share."""
        try:
            # Get payment
            payment = (
                self.db.query(Payment)
                .filter(Payment.id == payment_id, Payment.is_active == True)
                .first()
            )

            if not payment:
                return False, "Payment not found", None

            # Get expense share
            expense_share = (
                self.db.query(ExpenseShare)
                .filter(ExpenseShare.id == expense_share_id, ExpenseShare.is_active == True)
                .first()
            )

            if not expense_share:
                return False, "Expense share not found", None

            # Validate household membership
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == payment.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to link this payment", None

            # Validate amount
            if amount <= 0:
                return False, "Link amount must be greater than zero", None

            if amount > payment.unallocated_amount:
                return False, "Link amount exceeds unallocated payment amount", None

            if amount > expense_share.share_amount_decimal:
                return False, "Link amount exceeds expense share amount", None

            # Create link
            esp = ExpenseSharePayment.create_allocation(
                payment_id=payment_id,
                expense_share_id=expense_share_id,
                amount=amount
            )

            self.db.add(esp)
            self.db.commit()
            self.db.refresh(esp)

            logger.info(f"Linked payment {payment_id} to expense share {expense_share_id}")
            return True, "Payment linked to expense share successfully", esp

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error linking payment to expense share: {e}")
            return False, f"Failed to link payment: {str(e)}", None

    async def unlink_expense_share(
        self,
        payment_id: UUID,
        expense_share_id: UUID,
        current_user_id: UUID
    ) -> Tuple[bool, str]:
        """Unlink a payment from an expense share."""
        try:
            # Get payment
            payment = (
                self.db.query(Payment)
                .filter(Payment.id == payment_id, Payment.is_active == True)
                .first()
            )

            if not payment:
                return False, "Payment not found"

            # Validate permission
            membership = (
                self.db.query(UserHousehold)
                .filter(
                    UserHousehold.user_id == current_user_id,
                    UserHousehold.household_id == payment.household_id,
                    UserHousehold.is_active == True
                )
                .first()
            )

            if not membership:
                return False, "You don't have permission to unlink this payment"

            # Find and remove link
            esp = (
                self.db.query(ExpenseSharePayment)
                .filter(
                    ExpenseSharePayment.payment_id == payment_id,
                    ExpenseSharePayment.expense_share_id == expense_share_id,
                    ExpenseSharePayment.is_active == True
                )
                .first()
            )

            if not esp:
                return False, "Payment link not found"

            esp.is_active = False
            esp.updated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Unlinked payment {payment_id} from expense share {expense_share_id}")
            return True, "Payment unlinked successfully"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error unlinking payment: {e}")
            return False, f"Failed to unlink payment: {str(e)}"

    def get_payments_by_filters(
        self,
        user_id: UUID,
        household_id: Optional[UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "payment_date",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20
    ) -> List[Payment]:
        """
        Get payments by filters - simplified version for history display.
        
        Args:
            user_id: Current user ID
            household_id: Optional household ID filter
            filters: Optional filters dict
            sort_by: Sort field
            sort_order: Sort direction
            skip: Records to skip for pagination
            limit: Max records to return
            
        Returns:
            List of Payment objects
        """
        try:
            # Build base query - payments where user is payer or payee
            query = (
                self.db.query(Payment)
                .options(
                    joinedload(Payment.payer),
                    joinedload(Payment.payee),
                    joinedload(Payment.household)
                )
                .filter(
                    Payment.is_active == True,
                    or_(
                        Payment.payer_id == user_id,
                        Payment.payee_id == user_id
                    )
                )
            )

            # Apply household filter if provided
            if household_id:
                query = query.filter(Payment.household_id == household_id)

            # Apply additional filters if provided
            if filters:
                if 'search' in filters and filters['search']:
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            Payment.description.ilike(search_term),
                            Payment.reference_number.ilike(search_term)
                        )
                    )

                if 'payment_type' in filters and filters['payment_type']:
                    query = query.filter(Payment.payment_type == filters['payment_type'])

                if 'min_amount' in filters and filters['min_amount'] is not None:
                    query = query.filter(Payment.amount >= filters['min_amount'])

                if 'max_amount' in filters and filters['max_amount'] is not None:
                    query = query.filter(Payment.amount <= filters['max_amount'])

                if 'status' in filters and filters['status']:
                    # For now, all active payments are "completed"
                    # This can be extended later if payment status is added
                    pass

            # Apply sorting
            if sort_order.lower() == "desc":
                if sort_by == "amount":
                    query = query.order_by(desc(Payment.amount))
                else:  # default to payment_date
                    query = query.order_by(desc(Payment.payment_date))
            else:
                if sort_by == "amount":
                    query = query.order_by(asc(Payment.amount))
                else:  # default to payment_date
                    query = query.order_by(asc(Payment.payment_date))

            # Apply pagination
            query = query.offset(skip).limit(limit)

            return query.all()

        except Exception as e:
            logger.error(f"Error getting payments by filters: {e}")
            return [] 