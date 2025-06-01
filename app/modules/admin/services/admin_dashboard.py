"""
Admin Dashboard Service - System-wide statistics and data aggregation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.modules.auth.models.user import User
from app.modules.expenses.models.household import Household
from app.modules.expenses.models.expense import Expense
from app.modules.expenses.models.user_household import UserHousehold

logger = logging.getLogger(__name__)


class AdminDashboardService:
    """Service for aggregating admin dashboard data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """
        Get system-wide overview statistics.
        
        Returns:
            Dict containing system metrics like user count, household count, etc.
        """
        try:
            # Get basic counts
            total_users = self.db.query(func.count(User.id)).scalar() or 0
            active_users = self.db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
            admin_users = self.db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0
            
            total_households = self.db.query(func.count(Household.id)).scalar() or 0
            active_households = self.db.query(func.count(Household.id)).filter(Household.is_active == True).scalar() or 0
            
            total_expenses = self.db.query(func.count(Expense.id)).scalar() or 0
            
            # Calculate total expense amount
            total_expense_amount = self.db.query(func.sum(Expense.amount)).scalar() or 0.0
            
            # Get recent activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            new_users_30d = self.db.query(func.count(User.id)).filter(
                User.created_at >= thirty_days_ago
            ).scalar() or 0
            
            new_households_30d = self.db.query(func.count(Household.id)).filter(
                Household.created_at >= thirty_days_ago
            ).scalar() or 0
            
            new_expenses_30d = self.db.query(func.count(Expense.id)).filter(
                Expense.created_at >= thirty_days_ago
            ).scalar() or 0
            
            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "admin": admin_users,
                    "new_30d": new_users_30d
                },
                "households": {
                    "total": total_households,
                    "active": active_households,
                    "new_30d": new_households_30d
                },
                "expenses": {
                    "total": total_expenses,
                    "total_amount": float(total_expense_amount),
                    "new_30d": new_expenses_30d
                },
                "system": {
                    "database_status": "healthy",  # Can be expanded with actual health checks
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {
                "users": {"total": 0, "active": 0, "admin": 0, "new_30d": 0},
                "households": {"total": 0, "active": 0, "new_30d": 0},
                "expenses": {"total": 0, "total_amount": 0.0, "new_30d": 0},
                "system": {
                    "database_status": "error",
                    "last_updated": datetime.utcnow().isoformat()
                }
            }
    
    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent system activity.
        
        Args:
            limit: Maximum number of activities to return
            
        Returns:
            List of recent activities
        """
        try:
            activities = []
            
            # Recent user registrations
            recent_users = (
                self.db.query(User)
                .filter(User.created_at >= datetime.utcnow() - timedelta(days=7))
                .order_by(desc(User.created_at))
                .limit(5)
                .all()
            )
            
            for user in recent_users:
                activities.append({
                    "type": "user_registration",
                    "title": "New User Registration",
                    "description": f"{user.first_name} {user.last_name} ({user.email}) joined",
                    "timestamp": user.created_at,
                    "user_id": str(user.id),
                    "user_name": f"{user.first_name} {user.last_name}",
                    "user_email": user.email
                })
            
            # Recent household creations
            recent_households = (
                self.db.query(Household)
                .filter(Household.created_at >= datetime.utcnow() - timedelta(days=7))
                .order_by(desc(Household.created_at))
                .limit(5)
                .all()
            )
            
            for household in recent_households:
                activities.append({
                    "type": "household_creation",
                    "title": "New Household Created",
                    "description": f"Household '{household.name}' was created",
                    "timestamp": household.created_at,
                    "household_id": str(household.id),
                    "household_name": household.name
                })
            
            # Recent expenses
            recent_expenses = (
                self.db.query(Expense)
                .filter(Expense.created_at >= datetime.utcnow() - timedelta(days=7))
                .order_by(desc(Expense.created_at))
                .limit(5)
                .all()
            )
            
            for expense in recent_expenses:
                activities.append({
                    "type": "expense_creation",
                    "title": "New Expense Added",
                    "description": f"${expense.amount:.2f} expense '{expense.title}' added",
                    "timestamp": expense.created_at,
                    "expense_id": str(expense.id),
                    "expense_title": expense.title,
                    "expense_amount": float(expense.amount)
                })
            
            # Sort all activities by timestamp and limit
            activities.sort(key=lambda x: x["timestamp"], reverse=True)
            return activities[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health indicators.
        
        Returns:
            Dict containing system health metrics
        """
        try:
            health_status = {
                "overall_status": "healthy",
                "checks": {
                    "database": {"status": "healthy", "message": "Database connection active"},
                    "auth": {"status": "healthy", "message": "Authentication system operational"},
                    "expenses": {"status": "healthy", "message": "Expense system operational"}
                },
                "metrics": {
                    "response_time": "< 100ms",  # Placeholder - can be calculated from logs
                    "error_rate": "< 1%",       # Placeholder - can be calculated from logs
                    "uptime": "99.9%"           # Placeholder - can be tracked separately
                },
                "last_check": datetime.utcnow().isoformat()
            }
            
            # Check if there are any critical issues
            # For now, just verify basic database connectivity
            user_count = self.db.query(func.count(User.id)).scalar()
            if user_count is None:
                health_status["checks"]["database"]["status"] = "error"
                health_status["checks"]["database"]["message"] = "Database query failed"
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "overall_status": "error",
                "checks": {
                    "database": {"status": "error", "message": f"Database error: {str(e)}"},
                    "auth": {"status": "unknown", "message": "Could not verify auth system"},
                    "expenses": {"status": "unknown", "message": "Could not verify expense system"}
                },
                "metrics": {
                    "response_time": "unknown",
                    "error_rate": "unknown",
                    "uptime": "unknown"
                },
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def get_quick_stats(self) -> Dict[str, Any]:
        """
        Get quick stats for dashboard cards.
        
        Returns:
            Dict containing quick statistics
        """
        try:
            # Get today's date range
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            # Today's new registrations
            today_new_users = self.db.query(func.count(User.id)).filter(
                User.created_at >= today_start,
                User.created_at < today_end
            ).scalar() or 0
            
            # Today's new expenses
            today_new_expenses = self.db.query(func.count(Expense.id)).filter(
                Expense.created_at >= today_start,
                Expense.created_at < today_end
            ).scalar() or 0
            
            # Today's expense amount
            today_expense_amount = self.db.query(func.sum(Expense.amount)).filter(
                Expense.created_at >= today_start,
                Expense.created_at < today_end
            ).scalar() or 0.0
            
            # Active user sessions (users who were active in last hour)
            last_hour = datetime.utcnow() - timedelta(hours=1)
            active_sessions = self.db.query(func.count(User.id)).filter(
                User.last_login >= last_hour
            ).scalar() or 0
            
            return {
                "today": {
                    "new_users": today_new_users,
                    "new_expenses": today_new_expenses,
                    "expense_amount": float(today_expense_amount)
                },
                "active_sessions": active_sessions,
                "system_load": "normal"  # Placeholder for actual system load monitoring
            }
            
        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return {
                "today": {
                    "new_users": 0,
                    "new_expenses": 0,
                    "expense_amount": 0.0
                },
                "active_sessions": 0,
                "system_load": "unknown"
            } 