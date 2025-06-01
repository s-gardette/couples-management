"""
Live Service

Handles real-time updates for expenses, payments, balances, and other live data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from app.core.services.base_service import BaseService
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.payment import Payment
from app.modules.expenses.models.household import Household
from app.modules.expenses.services.expense_service import ExpenseService
from app.modules.expenses.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class LiveService(BaseService):
    """Service for handling real-time updates and live data."""

    def __init__(self, db: Session):
        self.db = db
        self.expense_service = ExpenseService(db)
        self.analytics_service = AnalyticsService(db)

    async def get_live_expenses(
        self,
        household_id: UUID,
        current_user_id: UUID,
        filters: Optional[Dict[str, Any]] = None,
        view_mode: str = "cards",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get live expense data with real-time updates.
        
        Args:
            household_id: Household ID
            current_user_id: Current user ID
            filters: Filter parameters
            view_mode: View mode (cards/table)
            page: Page number
            per_page: Items per page
            
        Returns:
            Dictionary with expenses, metadata, and live update info
        """
        try:
            # Get expenses using existing service
            success, message, result = await self.expense_service.get_expenses(
                household_id=household_id,
                current_user_id=current_user_id,
                filters=filters,
                page=page,
                per_page=per_page
            )
            
            if not success:
                return {
                    "success": False,
                    "message": message,
                    "expenses": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 0,
                    "view_mode": view_mode,
                    "last_updated": datetime.utcnow().isoformat()
                }

            # Add live update metadata
            result.update({
                "success": True,
                "view_mode": view_mode,
                "last_updated": datetime.utcnow().isoformat(),
                "live_enabled": True
            })

            return result

        except Exception as e:
            logger.error(f"Error getting live expenses: {e}")
            return {
                "success": False,
                "message": f"Failed to get live expenses: {str(e)}",
                "expenses": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "view_mode": view_mode,
                "last_updated": datetime.utcnow().isoformat()
            }

    async def get_live_balances(
        self,
        household_id: UUID,
        current_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get live balance data with real-time calculations.
        
        Args:
            household_id: Household ID
            current_user_id: Current user ID
            
        Returns:
            Dictionary with balance data and live update info
        """
        try:
            # Get balance data using analytics service
            success, message, balance_data = await self.analytics_service.get_household_balance_summary(
                household_id=household_id,
                current_user_id=current_user_id
            )
            
            if not success:
                return {
                    "success": False,
                    "message": message,
                    "balances": {},
                    "last_updated": datetime.utcnow().isoformat()
                }

            return {
                "success": True,
                "balances": balance_data,
                "last_updated": datetime.utcnow().isoformat(),
                "live_enabled": True
            }

        except Exception as e:
            logger.error(f"Error getting live balances: {e}")
            return {
                "success": False,
                "message": f"Failed to get live balances: {str(e)}",
                "balances": {},
                "last_updated": datetime.utcnow().isoformat()
            }

    async def get_live_summary_stats(
        self,
        household_id: UUID,
        current_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get live summary statistics for the household.
        
        Args:
            household_id: Household ID
            current_user_id: Current user ID
            
        Returns:
            Dictionary with summary stats and live update info
        """
        try:
            # Get expense counts by status
            total_expenses = (
                self.db.query(Expense)
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True
                )
                .count()
            )
            
            paid_expenses = (
                self.db.query(Expense)
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    Expense.payment_status == 'paid'
                )
                .count()
            )
            
            unpaid_expenses = (
                self.db.query(Expense)
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    Expense.payment_status == 'unpaid'
                )
                .count()
            )
            
            # Get recent payments count
            recent_payments = (
                self.db.query(Payment)
                .filter(
                    Payment.household_id == household_id,
                    Payment.is_active == True,
                    Payment.payment_date >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                )
                .count()
            )

            return {
                "success": True,
                "stats": {
                    "total_expenses": total_expenses,
                    "paid_expenses": paid_expenses,
                    "unpaid_expenses": unpaid_expenses,
                    "recent_payments": recent_payments,
                    "completion_rate": round((paid_expenses / total_expenses * 100) if total_expenses > 0 else 0, 1)
                },
                "last_updated": datetime.utcnow().isoformat(),
                "live_enabled": True
            }

        except Exception as e:
            logger.error(f"Error getting live summary stats: {e}")
            return {
                "success": False,
                "message": f"Failed to get live summary stats: {str(e)}",
                "stats": {},
                "last_updated": datetime.utcnow().isoformat()
            }

    def trigger_live_update(
        self,
        update_type: str,
        household_id: UUID,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Trigger a live update event.
        
        Args:
            update_type: Type of update (expense_created, expense_updated, payment_made, etc.)
            household_id: Household ID
            data: Optional data to include with the update
            
        Returns:
            Boolean indicating success
        """
        try:
            # For now, just log the event
            # In the future, this could trigger WebSocket events or other real-time mechanisms
            logger.info(f"Live update triggered: {update_type} for household {household_id}")
            
            if data:
                logger.debug(f"Update data: {data}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error triggering live update: {e}")
            return False

    async def get_live_expense_details(
        self,
        expense_id: UUID,
        current_user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get live expense details with real-time data.
        
        Args:
            expense_id: Expense ID
            current_user_id: Current user ID
            
        Returns:
            Dictionary with expense details and live update info
        """
        try:
            # Get expense details using existing service
            success, message, expense = await self.expense_service.get_expense_by_id(
                expense_id=expense_id,
                current_user_id=current_user_id
            )
            
            if not success:
                return {
                    "success": False,
                    "message": message,
                    "expense": None,
                    "last_updated": datetime.utcnow().isoformat()
                }

            return {
                "success": True,
                "expense": expense,
                "last_updated": datetime.utcnow().isoformat(),
                "live_enabled": True
            }

        except Exception as e:
            logger.error(f"Error getting live expense details: {e}")
            return {
                "success": False,
                "message": f"Failed to get live expense details: {str(e)}",
                "expense": None,
                "last_updated": datetime.utcnow().isoformat()
            } 