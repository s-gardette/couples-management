"""
Live Service

Handles real-time updates for expenses, payments, balances, and other live data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func

from app.core.services.base_service import BaseService
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.payment import Payment
from app.modules.expenses.models.household import Household
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.category import Category
from app.modules.auth.models.user import User
from app.modules.expenses.services.expense_service import ExpenseService
from app.modules.expenses.services.analytics_service import AnalyticsService
from app.database import get_db
from app.modules.live.utils.live_helpers import LiveHelpers

logger = logging.getLogger(__name__)


class LiveService:
    """
    Service for handling live updates and real-time data operations.
    
    This service provides real-time data for expenses, balances, and statistics
    with support for filtering, pagination, and live updates.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the LiveService.
        
        Args:
            db: Database session for real data operations.
        """
        self.db = db
        self.live_helpers = LiveHelpers()

    async def get_live_stats(
        self,
        household_id: Optional[str] = None,
        current_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get live summary statistics for the household."""
        try:
            # Build base query
            query = self.db.query(Expense).filter(Expense.is_active == True)
            
            # Filter by household if provided
            if household_id:
                # Convert string to UUID if needed
                try:
                    household_uuid = UUID(household_id) if isinstance(household_id, str) else household_id
                    query = query.filter(Expense.household_id == household_uuid)
                except ValueError:
                    logger.error(f"Invalid household_id format in stats: {household_id}")
                    return {
                        'total_expenses': 0,
                        'total_amount': 0,
                        'this_month_amount': 0,
                        'this_month_count': 0,
                        'success': False,
                        'message': f'Invalid household ID format: {household_id}'
                    }
            
            # Get total expense count and amount
            total_expenses = query.count()
            total_amount = query.with_entities(func.sum(Expense.amount)).scalar() or 0
            
            # Get counts by payment status
            # Count expenses with shares that are paid/unpaid
            paid_count = query.join(ExpenseShare).filter(
                ExpenseShare.is_active == True,
                ExpenseShare.is_paid == True
            ).distinct().count()
            
            unpaid_count = query.join(ExpenseShare).filter(
                ExpenseShare.is_active == True,
                ExpenseShare.is_paid == False
            ).distinct().count()
            
            return {
                'total_expenses': total_expenses,
                'total_amount': float(total_amount),
                'paid_count': paid_count,
                'pending_count': unpaid_count,  # Use unpaid_count for pending
                'unpaid_count': unpaid_count,
                'recent_activity': total_expenses,  # Could be refined to count recent activity
                'success': True,
                'message': 'Statistics calculated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error getting live stats: {e}")
            return {
                'total_expenses': 0,
                'total_amount': 0.0,
                'paid_count': 0,
                'pending_count': 0,
                'unpaid_count': 0,
                'recent_activity': 0,
                'success': False,
                'message': f'Error calculating statistics: {str(e)}'
            }

    async def get_live_expenses(
        self,
        user_id: UUID,
        household_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "date_desc",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get live expense data with real-time updates.
        
        Args:
            user_id: User ID
            household_id: Optional household ID to filter by
            filters: Optional filters dictionary
            sort_by: Sort field and order
            page: Page number for pagination
            per_page: Items per page
            
        Returns:
            Dictionary with formatted expense data
        """
        try:
            # Build base query with joins
            query = self.db.query(Expense).options(
                joinedload(Expense.creator),
                joinedload(Expense.category),
                joinedload(Expense.shares)
            ).filter(Expense.is_active == True)
            
            # Filter by household if provided
            if household_id:
                # Convert string to UUID if needed
                try:
                    household_uuid = UUID(household_id) if isinstance(household_id, str) else household_id
                    query = query.filter(Expense.household_id == household_uuid)
                except ValueError:
                    logger.error(f"Invalid household_id format: {household_id}")
                    return {
                        'expenses': [],
                        'total': 0,
                        'page': page,
                        'per_page': per_page,
                        'success': False,
                        'message': f'Invalid household ID format: {household_id}'
                    }
            
            # Apply filters
            if filters:
                if filters.get('search'):
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            Expense.title.ilike(search_term),
                            Expense.description.ilike(search_term)
                        )
                    )
                
                if filters.get('category'):
                    # Join with category to filter by category name
                    query = query.join(Category).filter(
                        Category.name.ilike(f"%{filters['category']}%")
                    )
                
                if filters.get('min_amount'):
                    query = query.filter(Expense.amount >= filters['min_amount'])
                
                if filters.get('max_amount'):
                    query = query.filter(Expense.amount <= filters['max_amount'])
                
                if filters.get('created_by') == 'me':
                    query = query.filter(Expense.created_by == user_id)
                
                # Date range filters
                if filters.get('date_range'):
                    today = datetime.now().date()
                    if filters['date_range'] == 'today':
                        query = query.filter(Expense.expense_date == today)
                    elif filters['date_range'] == 'week':
                        week_start = today - timedelta(days=today.weekday())
                        query = query.filter(Expense.expense_date >= week_start)
                    elif filters['date_range'] == 'month':
                        month_start = today.replace(day=1)
                        query = query.filter(Expense.expense_date >= month_start)
            
            # Apply sorting
            if sort_by == "date_desc":
                query = query.order_by(desc(Expense.expense_date), desc(Expense.created_at))
            elif sort_by == "date_asc":
                query = query.order_by(Expense.expense_date, Expense.created_at)
            elif sort_by == "amount_desc":
                query = query.order_by(desc(Expense.amount))
            elif sort_by == "amount_asc":
                query = query.order_by(Expense.amount)
            elif sort_by == "title_asc":
                query = query.order_by(Expense.title)
            elif sort_by == "title_desc":
                query = query.order_by(desc(Expense.title))
            
            # Get total count for pagination
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            expenses = query.offset(offset).limit(per_page).all()
            
            # Format expenses for template
            formatted_expenses = []
            for expense in expenses:
                # Determine payment status
                payment_status = 'unpaid'
                if expense.shares:
                    paid_shares = sum(1 for share in expense.shares if share.is_active and share.is_paid)
                    total_shares = sum(1 for share in expense.shares if share.is_active)
                    
                    if paid_shares == total_shares and total_shares > 0:
                        payment_status = 'paid'
                    elif paid_shares > 0:
                        payment_status = 'partial'
                
                formatted_expense = {
                    'id': str(expense.id),
                    'title': expense.title,
                    'amount': float(expense.amount),
                    'formatted_amount': expense.formatted_amount,
                    'description': expense.description or '',
                    'date': expense.expense_date.isoformat(),
                    'date_display': expense.expense_date.strftime('%b %d, %Y'),
                    'category': expense.category.name if expense.category else 'Other',
                    'payment_status': payment_status,
                    'created_by': {
                        'name': expense.creator.display_name if expense.creator else 'Unknown',
                        'id': str(expense.creator.id) if expense.creator else None
                    }
                }
                formatted_expenses.append(formatted_expense)
            
            return {
                'expenses': formatted_expenses,
                'total': total,
                'page': page,
                'per_page': per_page,
                'success': True,
                'message': 'Expenses retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"Error getting live expenses: {e}")
            return {
                'expenses': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'success': False,
                'message': f'Error retrieving expenses: {str(e)}'
            }

    async def get_live_balances(
        self,
        household_id: Optional[str] = None,
        current_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get live balance calculations with real-time updates."""
        try:
            # Build base query
            query = self.db.query(Expense).filter(Expense.is_active == True)
            
            # Filter by household if provided
            if household_id:
                # Convert string to UUID if needed
                try:
                    household_uuid = UUID(household_id) if isinstance(household_id, str) else household_id
                    query = query.filter(Expense.household_id == household_uuid)
                except ValueError:
                    logger.error(f"Invalid household_id format in balances: {household_id}")
                    return {
                        'total_expenses': 0.0,
                        'total_paid': 0.0,
                        'total_pending': 0.0,
                        'user_balance': 0.0,
                        'success': False,
                        'message': f'Invalid household ID format: {household_id}'
                    }
            
            # Calculate totals
            total_expenses = query.with_entities(func.sum(Expense.amount)).scalar() or 0
            
            # Get paid and pending amounts through shares
            paid_shares = self.db.query(ExpenseShare).join(Expense).filter(
                Expense.is_active == True,
                ExpenseShare.is_active == True,
                ExpenseShare.is_paid == True
            )
            if household_id:
                paid_shares = paid_shares.filter(Expense.household_id == household_uuid)
            
            total_paid = paid_shares.with_entities(func.sum(ExpenseShare.share_amount)).scalar() or 0
            
            pending_shares = self.db.query(ExpenseShare).join(Expense).filter(
                Expense.is_active == True,
                ExpenseShare.is_active == True,
                ExpenseShare.is_paid == False
            )
            if household_id:
                pending_shares = pending_shares.filter(Expense.household_id == household_uuid)
            
            total_pending = pending_shares.with_entities(func.sum(ExpenseShare.share_amount)).scalar() or 0
            
            # Calculate user balance (what they owe vs what they've paid)
            user_balance = 0.0
            if current_user_id:
                user_shares = self.db.query(ExpenseShare).join(Expense).filter(
                    Expense.is_active == True,
                    ExpenseShare.is_active == True,
                    ExpenseShare.user_id == current_user_id
                )
                if household_id:
                    user_shares = user_shares.filter(Expense.household_id == household_uuid)
                
                user_total_shares = user_shares.with_entities(func.sum(ExpenseShare.share_amount)).scalar() or 0
                user_paid_shares = user_shares.filter(ExpenseShare.is_paid == True).with_entities(func.sum(ExpenseShare.share_amount)).scalar() or 0
                user_balance = float(user_paid_shares) - float(user_total_shares)
            
            return {
                'total_expenses': float(total_expenses),
                'total_paid': float(total_paid),
                'total_pending': float(total_pending),
                'user_balance': user_balance,
                'success': True,
                'message': 'Balance calculations completed'
            }
            
        except Exception as e:
            logger.error(f"Error getting live balances: {e}")
            return {
                'total_expenses': 0.0,
                'total_paid': 0.0,
                'total_pending': 0.0,
                'user_balance': 0.0,
                'success': False,
                'message': f'Error calculating balances: {str(e)}'
            }

    async def get_live_expense_details(
        self,
        expense_id: UUID,
        current_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get live expense details with real-time data."""
        try:
            if self.db is None:
                # Return mock expense details
                return {
                    'expense': {
                        'id': str(expense_id),
                        'title': 'Sample Expense',
                        'amount': 50.00,
                        'description': 'Sample expense description',
                        'date': '2024-01-15',
                        'category': 'Other',
                        'payment_status': 'pending'
                    },
                    'success': True,
                    'message': 'Mock expense details retrieved'
                }
            
            # TODO: Implement actual expense details retrieval
            return {
                'expense': None,
                'success': False,
                'message': 'Expense not found'
            }
            
        except Exception as e:
            logger.error(f"Error getting live expense details: {e}")
            return {
                'success': False,
                'message': f'Error retrieving expense details: {str(e)}'
            }

    async def trigger_update(
        self,
        component: str = "expenses",
        data: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Trigger a live update event."""
        try:
            # For now, just return success
            return {
                'triggered': True,
                'component': component,
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'message': f'Live update triggered for {component}'
            }
            
        except Exception as e:
            logger.error(f"Error triggering live update: {e}")
            return {
                'success': False,
                'message': f'Error triggering update: {str(e)}'
            } 