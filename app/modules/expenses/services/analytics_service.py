"""
Analytics service for generating expense reports and insights.
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID

from sqlalchemy import func, desc, asc, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.services.base_service import BaseService
from app.core.utils.helpers import format_currency
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.expense_share import ExpenseShare
from app.modules.expenses.models.household import Household
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.expenses.models.category import Category

logger = logging.getLogger(__name__)


class AnalyticsService(BaseService[Expense, dict, dict]):
    """Service for expense analytics and reporting."""

    def __init__(self, db: Session):
        super().__init__(Expense)
        self.db = db

    async def get_spending_summary(
        self,
        household_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period: str = "month"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get comprehensive spending summary for a household.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            start_date: Optional start date filter
            end_date: Optional end date filter
            period: Period for grouping (day, week, month, year)

        Returns:
            Tuple of (success, message, summary_dict)
        """
        try:
            # Verify household membership
            membership = await self._verify_membership(household_id, user_id)
            if not membership:
                return False, "You are not a member of this household", {}

            # Set default date range if not provided
            if not end_date:
                end_date = date.today()
            if not start_date:
                if period == "month":
                    start_date = end_date.replace(day=1)
                elif period == "year":
                    start_date = end_date.replace(month=1, day=1)
                else:
                    start_date = end_date - timedelta(days=30)

            # Get expenses in date range
            expenses = (
                self.db.query(Expense)
                .options(joinedload(Expense.category), joinedload(Expense.creator))
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date
                )
                .all()
            )

            # Calculate basic metrics
            total_amount = sum(expense.amount for expense in expenses)
            expense_count = len(expenses)
            average_expense = total_amount / expense_count if expense_count > 0 else Decimal("0")

            # Get category breakdown
            category_breakdown = await self._get_category_breakdown(expenses)

            # Get user breakdown
            user_breakdown = await self._get_user_breakdown(expenses, household_id)

            # Get time series data
            time_series = await self._get_time_series_data(expenses, period)

            # Get top expenses
            top_expenses = sorted(expenses, key=lambda x: x.amount, reverse=True)[:10]

            # Calculate trends
            trends = await self._calculate_trends(household_id, start_date, end_date, period)

            summary = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_type": period
                },
                "totals": {
                    "total_amount": float(total_amount),
                    "expense_count": expense_count,
                    "average_expense": float(average_expense),
                    "daily_average": float(total_amount / max(1, (end_date - start_date).days + 1))
                },
                "category_breakdown": category_breakdown,
                "user_breakdown": user_breakdown,
                "time_series": time_series,
                "top_expenses": [
                    {
                        "id": str(expense.id),
                        "title": expense.title,
                        "amount": float(expense.amount),
                        "date": expense.expense_date.isoformat(),
                        "category": expense.category.name if expense.category else "Uncategorized",
                        "creator": expense.creator.username if expense.creator else "Unknown"
                    }
                    for expense in top_expenses
                ],
                "trends": trends
            }

            return True, "Spending summary generated successfully", summary

        except Exception as e:
            logger.error(f"Error generating spending summary: {e}")
            return False, f"Failed to generate summary: {str(e)}", {}

    async def get_category_analysis(
        self,
        household_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get detailed category analysis for a household.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (success, message, analysis_dict)
        """
        try:
            # Verify household membership
            membership = await self._verify_membership(household_id, user_id)
            if not membership:
                return False, "You are not a member of this household", {}

            # Set default date range
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=90)  # Last 3 months

            # Get category spending data
            category_data = (
                self.db.query(
                    Category.id,
                    Category.name,
                    Category.color,
                    Category.icon,
                    func.sum(Expense.amount).label('total_amount'),
                    func.count(Expense.id).label('expense_count'),
                    func.avg(Expense.amount).label('average_amount')
                )
                .outerjoin(Expense, and_(
                    Expense.category_id == Category.id,
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date
                ))
                .filter(
                    or_(
                        Category.household_id == household_id,
                        Category.household_id.is_(None)
                    )
                )
                .group_by(Category.id, Category.name, Category.color, Category.icon)
                .having(func.sum(Expense.amount) > 0)
                .order_by(desc('total_amount'))
                .all()
            )

            # Calculate total for percentages
            total_spending = sum(row.total_amount or 0 for row in category_data)

            categories = []
            for row in category_data:
                amount = row.total_amount or 0
                count = row.expense_count or 0
                avg = row.average_amount or 0
                percentage = (amount / total_spending * 100) if total_spending > 0 else 0

                categories.append({
                    "id": str(row.id),
                    "name": row.name,
                    "color": row.color,
                    "icon": row.icon,
                    "total_amount": float(amount),
                    "expense_count": count,
                    "average_amount": float(avg),
                    "percentage": round(percentage, 2)
                })

            # Get uncategorized expenses
            uncategorized = (
                self.db.query(
                    func.sum(Expense.amount).label('total_amount'),
                    func.count(Expense.id).label('expense_count')
                )
                .filter(
                    Expense.household_id == household_id,
                    Expense.category_id.is_(None),
                    Expense.is_active == True,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date
                )
                .first()
            )

            if uncategorized.total_amount:
                uncategorized_amount = uncategorized.total_amount
                uncategorized_count = uncategorized.expense_count
                uncategorized_percentage = (uncategorized_amount / total_spending * 100) if total_spending > 0 else 0

                categories.append({
                    "id": None,
                    "name": "Uncategorized",
                    "color": "#6B7280",
                    "icon": "question-mark",
                    "total_amount": float(uncategorized_amount),
                    "expense_count": uncategorized_count,
                    "average_amount": float(uncategorized_amount / uncategorized_count) if uncategorized_count > 0 else 0,
                    "percentage": round(uncategorized_percentage, 2)
                })

            # Get category trends (month-over-month)
            category_trends = await self._get_category_trends(household_id, start_date, end_date)

            analysis = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_spending": float(total_spending),
                "categories": categories,
                "trends": category_trends,
                "insights": await self._generate_category_insights(categories)
            }

            return True, "Category analysis generated successfully", analysis

        except Exception as e:
            logger.error(f"Error generating category analysis: {e}")
            return False, f"Failed to generate analysis: {str(e)}", {}

    async def get_user_spending_patterns(
        self,
        household_id: UUID,
        user_id: UUID,
        target_user_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get spending patterns for a specific user or all users.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            target_user_id: Optional specific user to analyze
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Tuple of (success, message, patterns_dict)
        """
        try:
            # Verify household membership
            membership = await self._verify_membership(household_id, user_id)
            if not membership:
                return False, "You are not a member of this household", {}

            # Set default date range
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=90)

            if target_user_id:
                # Analyze specific user
                patterns = await self._analyze_single_user(household_id, target_user_id, start_date, end_date)
            else:
                # Analyze all users
                patterns = await self._analyze_all_users(household_id, start_date, end_date)

            return True, "User spending patterns generated successfully", patterns

        except Exception as e:
            logger.error(f"Error generating user spending patterns: {e}")
            return False, f"Failed to generate patterns: {str(e)}", {}

    async def get_balance_calculations(
        self,
        household_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Get detailed balance calculations for all household members.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)

        Returns:
            Tuple of (success, message, balances_dict)
        """
        try:
            # Verify household membership
            membership = await self._verify_membership(household_id, user_id)
            if not membership:
                return False, "You are not a member of this household", {}

            # Get all household members
            members = (
                self.db.query(UserHousehold)
                .options(joinedload(UserHousehold.user))
                .filter(
                    UserHousehold.household_id == household_id,
                    UserHousehold.is_active == True
                )
                .all()
            )

            balances = []
            total_owed = Decimal("0")
            total_owing = Decimal("0")

            for member in members:
                # Calculate what this member owes
                owes = (
                    self.db.query(func.sum(ExpenseShare.share_amount))
                    .join(Expense)
                    .filter(
                        ExpenseShare.user_household_id == member.id,
                        ExpenseShare.is_paid == False,
                        ExpenseShare.is_active == True,
                        Expense.household_id == household_id,
                        Expense.is_active == True
                    )
                    .scalar() or Decimal("0")
                )

                # Calculate what this member is owed
                owed = (
                    self.db.query(func.sum(ExpenseShare.share_amount))
                    .join(Expense)
                    .join(UserHousehold, ExpenseShare.user_household_id == UserHousehold.id)
                    .filter(
                        Expense.created_by == member.user_id,
                        ExpenseShare.is_paid == False,
                        ExpenseShare.is_active == True,
                        Expense.household_id == household_id,
                        Expense.is_active == True,
                        UserHousehold.user_id != member.user_id  # Exclude their own share
                    )
                    .scalar() or Decimal("0")
                )

                net_balance = owed - owes
                
                if net_balance > 0:
                    total_owed += net_balance
                else:
                    total_owing += abs(net_balance)

                balances.append({
                    "user_id": str(member.user_id),
                    "username": member.user.username if member.user else "Unknown",
                    "nickname": member.nickname,
                    "owes_amount": float(owes),
                    "owed_amount": float(owed),
                    "net_balance": float(net_balance),
                    "status": "owed" if net_balance > 0 else "owes" if net_balance < 0 else "settled"
                })

            # Calculate settlement suggestions
            settlements = await self._calculate_settlement_suggestions(balances)

            balance_summary = {
                "household_id": str(household_id),
                "total_outstanding": float(total_owed),
                "member_balances": balances,
                "settlement_suggestions": settlements,
                "summary": {
                    "members_owed": len([b for b in balances if b["net_balance"] > 0]),
                    "members_owing": len([b for b in balances if b["net_balance"] < 0]),
                    "members_settled": len([b for b in balances if b["net_balance"] == 0])
                }
            }

            return True, "Balance calculations completed successfully", balance_summary

        except Exception as e:
            logger.error(f"Error calculating balances: {e}")
            return False, f"Failed to calculate balances: {str(e)}", {}

    async def export_data(
        self,
        household_id: UUID,
        user_id: UUID,
        export_type: str = "csv",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_shares: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Export household expense data.

        Args:
            household_id: Household ID
            user_id: User ID (for permission check)
            export_type: Export format (csv, json)
            start_date: Optional start date filter
            end_date: Optional end date filter
            include_shares: Whether to include share details

        Returns:
            Tuple of (success, message, export_data_dict)
        """
        try:
            # Verify household membership
            membership = await self._verify_membership(household_id, user_id)
            if not membership:
                return False, "You are not a member of this household", {}

            # Set default date range
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=365)  # Last year

            # Get expenses with related data
            expenses = (
                self.db.query(Expense)
                .options(
                    joinedload(Expense.category),
                    joinedload(Expense.creator),
                    joinedload(Expense.shares).joinedload(ExpenseShare.user_household)
                )
                .filter(
                    Expense.household_id == household_id,
                    Expense.is_active == True,
                    Expense.expense_date >= start_date,
                    Expense.expense_date <= end_date
                )
                .order_by(desc(Expense.expense_date))
                .all()
            )

            # Format data for export
            export_data = {
                "metadata": {
                    "household_id": str(household_id),
                    "export_date": datetime.now().isoformat(),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "total_expenses": len(expenses),
                    "export_type": export_type
                },
                "expenses": []
            }

            for expense in expenses:
                expense_data = {
                    "id": str(expense.id),
                    "title": expense.title,
                    "description": expense.description,
                    "amount": float(expense.amount),
                    "currency": expense.currency,
                    "expense_date": expense.expense_date.isoformat(),
                    "created_at": expense.created_at.isoformat(),
                    "category": expense.category.name if expense.category else "Uncategorized",
                    "creator": expense.creator.username if expense.creator else "Unknown",
                    "tags": expense.tags or [],
                    "receipt_url": expense.receipt_url
                }

                if include_shares:
                    expense_data["shares"] = [
                        {
                            "user_id": str(share.user_household.user_id) if share.user_household else None,
                            "username": share.user_household.user.username if share.user_household and share.user_household.user else "Unknown",
                            "share_amount": float(share.share_amount),
                            "share_percentage": float(share.share_percentage) if share.share_percentage else None,
                            "is_paid": share.is_paid,
                            "paid_at": share.paid_at.isoformat() if share.paid_at else None,
                            "payment_method": share.payment_method
                        }
                        for share in expense.shares if share.is_active
                    ]

                export_data["expenses"].append(expense_data)

            return True, "Data exported successfully", export_data

        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False, f"Failed to export data: {str(e)}", {}

    async def _verify_membership(self, household_id: UUID, user_id: UUID) -> Optional[UserHousehold]:
        """Verify user is a member of the household."""
        return (
            self.db.query(UserHousehold)
            .filter(
                UserHousehold.user_id == user_id,
                UserHousehold.household_id == household_id,
                UserHousehold.is_active == True
            )
            .first()
        )

    async def _get_category_breakdown(self, expenses: List[Expense]) -> Dict[str, Any]:
        """Get category breakdown from expenses list."""
        category_totals = {}
        total_amount = sum(expense.amount for expense in expenses)

        for expense in expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            if category_name not in category_totals:
                category_totals[category_name] = {
                    "amount": Decimal("0"),
                    "count": 0,
                    "color": expense.category.color if expense.category else "#6B7280"
                }
            category_totals[category_name]["amount"] += expense.amount
            category_totals[category_name]["count"] += 1

        # Convert to list with percentages
        breakdown = []
        for name, data in category_totals.items():
            percentage = (data["amount"] / total_amount * 100) if total_amount > 0 else 0
            breakdown.append({
                "name": name,
                "amount": float(data["amount"]),
                "count": data["count"],
                "percentage": round(percentage, 2),
                "color": data["color"]
            })

        return sorted(breakdown, key=lambda x: x["amount"], reverse=True)

    async def _get_user_breakdown(self, expenses: List[Expense], household_id: UUID) -> List[Dict[str, Any]]:
        """Get user breakdown from expenses list."""
        user_totals = {}
        total_amount = sum(expense.amount for expense in expenses)

        for expense in expenses:
            creator_name = expense.creator.username if expense.creator else "Unknown"
            if creator_name not in user_totals:
                user_totals[creator_name] = {
                    "amount": Decimal("0"),
                    "count": 0,
                    "user_id": str(expense.created_by) if expense.created_by else None
                }
            user_totals[creator_name]["amount"] += expense.amount
            user_totals[creator_name]["count"] += 1

        # Convert to list with percentages
        breakdown = []
        for name, data in user_totals.items():
            percentage = (data["amount"] / total_amount * 100) if total_amount > 0 else 0
            breakdown.append({
                "username": name,
                "user_id": data["user_id"],
                "amount": float(data["amount"]),
                "count": data["count"],
                "percentage": round(percentage, 2)
            })

        return sorted(breakdown, key=lambda x: x["amount"], reverse=True)

    async def _get_time_series_data(self, expenses: List[Expense], period: str) -> List[Dict[str, Any]]:
        """Get time series data grouped by period."""
        time_groups = {}

        for expense in expenses:
            if period == "day":
                key = expense.expense_date.isoformat()
            elif period == "week":
                # Get Monday of the week
                monday = expense.expense_date - timedelta(days=expense.expense_date.weekday())
                key = monday.isoformat()
            elif period == "month":
                key = expense.expense_date.strftime("%Y-%m")
            elif period == "year":
                key = expense.expense_date.strftime("%Y")
            else:
                key = expense.expense_date.isoformat()

            if key not in time_groups:
                time_groups[key] = {"amount": Decimal("0"), "count": 0}
            time_groups[key]["amount"] += expense.amount
            time_groups[key]["count"] += 1

        # Convert to sorted list
        time_series = []
        for key in sorted(time_groups.keys()):
            data = time_groups[key]
            time_series.append({
                "period": key,
                "amount": float(data["amount"]),
                "count": data["count"]
            })

        return time_series

    async def _calculate_trends(self, household_id: UUID, start_date: date, end_date: date, period: str) -> Dict[str, Any]:
        """Calculate spending trends."""
        # Get previous period for comparison
        period_length = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)

        # Current period total
        current_total = (
            self.db.query(func.sum(Expense.amount))
            .filter(
                Expense.household_id == household_id,
                Expense.is_active == True,
                Expense.expense_date >= start_date,
                Expense.expense_date <= end_date
            )
            .scalar() or Decimal("0")
        )

        # Previous period total
        previous_total = (
            self.db.query(func.sum(Expense.amount))
            .filter(
                Expense.household_id == household_id,
                Expense.is_active == True,
                Expense.expense_date >= prev_start,
                Expense.expense_date <= prev_end
            )
            .scalar() or Decimal("0")
        )

        # Calculate change
        if previous_total > 0:
            change_percentage = ((current_total - previous_total) / previous_total * 100)
        else:
            change_percentage = 100 if current_total > 0 else 0

        return {
            "current_period": float(current_total),
            "previous_period": float(previous_total),
            "change_amount": float(current_total - previous_total),
            "change_percentage": round(float(change_percentage), 2),
            "trend": "up" if change_percentage > 0 else "down" if change_percentage < 0 else "stable"
        }

    async def _get_category_trends(self, household_id: UUID, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get category spending trends."""
        # This is a simplified version - could be expanded for more detailed trend analysis
        return []

    async def _generate_category_insights(self, categories: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from category data."""
        insights = []
        
        if categories:
            top_category = categories[0]
            insights.append(f"Your highest spending category is {top_category['name']} at {top_category['percentage']:.1f}% of total expenses")
            
            if len(categories) > 1:
                second_category = categories[1]
                insights.append(f"{top_category['name']} and {second_category['name']} account for {top_category['percentage'] + second_category['percentage']:.1f}% of your spending")

        return insights

    async def _analyze_single_user(self, household_id: UUID, user_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze spending patterns for a single user."""
        # Implementation for single user analysis
        return {}

    async def _analyze_all_users(self, household_id: UUID, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze spending patterns for all users."""
        # Implementation for all users analysis
        return {}

    async def _calculate_settlement_suggestions(self, balances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate optimal settlement suggestions."""
        # Simple settlement algorithm - could be enhanced
        settlements = []
        
        # Separate those who owe from those who are owed
        owing = [b for b in balances if b["net_balance"] < 0]
        owed = [b for b in balances if b["net_balance"] > 0]
        
        # Sort by amount
        owing.sort(key=lambda x: x["net_balance"])  # Most negative first
        owed.sort(key=lambda x: x["net_balance"], reverse=True)  # Most positive first
        
        i, j = 0, 0
        while i < len(owing) and j < len(owed):
            debtor = owing[i]
            creditor = owed[j]
            
            debt_amount = abs(debtor["net_balance"])
            credit_amount = creditor["net_balance"]
            
            settlement_amount = min(debt_amount, credit_amount)
            
            if settlement_amount > 0.01:  # Only suggest settlements > 1 cent
                settlements.append({
                    "from_user": debtor["username"],
                    "from_user_id": debtor["user_id"],
                    "to_user": creditor["username"],
                    "to_user_id": creditor["user_id"],
                    "amount": settlement_amount
                })
            
            # Update balances
            debtor["net_balance"] += settlement_amount
            creditor["net_balance"] -= settlement_amount
            
            # Move to next if settled
            if abs(debtor["net_balance"]) < 0.01:
                i += 1
            if creditor["net_balance"] < 0.01:
                j += 1
        
        return settlements 