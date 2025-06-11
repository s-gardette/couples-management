"""
Notification Service

Handles toast notifications, alerts, and other user feedback mechanisms.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationService:
    """Service for handling notifications and user feedback."""

    def __init__(self):
        self.pending_notifications = []

    def create_notification(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        duration: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        auto_dismiss: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new notification.
        
        Args:
            message: Notification message
            notification_type: Type of notification
            priority: Priority level
            duration: Duration in milliseconds (None for default)
            actions: Optional action buttons
            auto_dismiss: Whether to auto-dismiss the notification
            
        Returns:
            Notification dictionary
        """
        # Set default durations based on type and priority
        if duration is None:
            if notification_type == NotificationType.ERROR:
                duration = 8000  # 8 seconds for errors
            elif notification_type == NotificationType.WARNING:
                duration = 6000  # 6 seconds for warnings
            elif priority == NotificationPriority.HIGH:
                duration = 6000  # 6 seconds for high priority
            else:
                duration = 4000  # 4 seconds for normal notifications

        notification = {
            "id": f"notif_{datetime.utcnow().timestamp()}".replace(".", "_"),
            "message": message,
            "type": notification_type.value,
            "priority": priority.value,
            "duration": duration,
            "actions": actions or [],
            "auto_dismiss": auto_dismiss,
            "created_at": datetime.utcnow().isoformat(),
            "dismissed": False
        }

        self.pending_notifications.append(notification)
        return notification

    def create_success_notification(
        self,
        message: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a success notification."""
        return self.create_notification(
            message=message,
            notification_type=NotificationType.SUCCESS,
            duration=duration
        )

    def create_error_notification(
        self,
        message: str,
        duration: Optional[int] = None,
        include_retry: bool = False
    ) -> Dict[str, Any]:
        """Create an error notification."""
        actions = []
        if include_retry:
            actions.append({
                "text": "Retry",
                "action": "retry",
                "style": "primary"
            })

        return self.create_notification(
            message=message,
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.HIGH,
            duration=duration,
            actions=actions
        )

    def create_warning_notification(
        self,
        message: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a warning notification."""
        return self.create_notification(
            message=message,
            notification_type=NotificationType.WARNING,
            duration=duration
        )

    def create_info_notification(
        self,
        message: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create an info notification."""
        return self.create_notification(
            message=message,
            notification_type=NotificationType.INFO,
            duration=duration
        )

    def create_action_notification(
        self,
        message: str,
        actions: List[Dict[str, Any]],
        notification_type: NotificationType = NotificationType.INFO,
        auto_dismiss: bool = False
    ) -> Dict[str, Any]:
        """Create a notification with action buttons."""
        return self.create_notification(
            message=message,
            notification_type=notification_type,
            actions=actions,
            auto_dismiss=auto_dismiss,
            duration=10000  # Longer duration for actionable notifications
        )

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all pending notifications."""
        return [n for n in self.pending_notifications if not n["dismissed"]]

    def dismiss_notification(self, notification_id: str, user_id: Optional[str] = None) -> bool:
        """
        Dismiss a specific notification for a user.
        
        Args:
            notification_id: Notification ID
            user_id: User ID (optional, for user-specific notifications)
            
        Returns:
            True if notification was dismissed, False otherwise
        """
        for notification in self.pending_notifications:
            if notification["id"] == notification_id:
                notification["dismissed"] = True
                return True
        return False

    def clear_all_notifications(self, user_id: Optional[str] = None) -> int:
        """
        Clear all notifications for a user.
        
        Args:
            user_id: User ID (optional, for user-specific notifications)
            
        Returns:
            Count of cleared notifications
        """
        count = len([n for n in self.pending_notifications if not n["dismissed"]])
        for notification in self.pending_notifications:
            notification["dismissed"] = True
        return count

    def get_notification_context(self) -> Dict[str, Any]:
        """Get notification context for templates."""
        pending = self.get_pending_notifications()
        
        return {
            "notifications": pending,
            "notification_count": len(pending),
            "has_notifications": len(pending) > 0,
            "has_errors": any(n["type"] == "error" for n in pending),
            "has_warnings": any(n["type"] == "warning" for n in pending)
        }

    # Predefined notification templates
    def expense_created(self, expense_title: str) -> Dict[str, Any]:
        """Notification for expense creation."""
        return self.create_success_notification(
            f"Expense '{expense_title}' created successfully!"
        )

    def expense_updated(self, expense_title: str) -> Dict[str, Any]:
        """Notification for expense update."""
        return self.create_success_notification(
            f"Expense '{expense_title}' updated successfully!"
        )

    def expense_deleted(self, expense_title: str) -> Dict[str, Any]:
        """Notification for expense deletion."""
        return self.create_success_notification(
            f"Expense '{expense_title}' deleted successfully!"
        )

    def payment_made(self, amount: float, expense_title: str = None) -> Dict[str, Any]:
        """Notification for payment creation."""
        if expense_title:
            message = f"Payment of ${amount:.2f} made for '{expense_title}'"
        else:
            message = f"Payment of ${amount:.2f} created successfully!"
        
        return self.create_success_notification(message)

    def payment_deleted(self, amount: float) -> Dict[str, Any]:
        """Notification for payment deletion."""
        return self.create_success_notification(
            f"Payment of ${amount:.2f} deleted successfully!"
        )

    def balance_updated(self) -> Dict[str, Any]:
        """Notification for balance update."""
        return self.create_info_notification(
            "Household balances have been updated"
        )

    def auto_save_success(self) -> Dict[str, Any]:
        """Notification for auto-save success."""
        return self.create_success_notification(
            "Changes saved automatically",
            duration=2000  # Short duration for auto-save
        )

    def network_error(self) -> Dict[str, Any]:
        """Notification for network errors."""
        return self.create_error_notification(
            "Network error occurred. Please check your connection and try again.",
            include_retry=True
        )

    def validation_error(self, field_name: str) -> Dict[str, Any]:
        """Notification for validation errors."""
        return self.create_error_notification(
            f"Please check the {field_name} field and try again."
        )

    def permission_denied(self) -> Dict[str, Any]:
        """Notification for permission errors."""
        return self.create_error_notification(
            "You don't have permission to perform this action."
        )

    def data_conflict(self, action: str) -> Dict[str, Any]:
        """Notification for data conflicts."""
        return self.create_error_notification(
            f"Data conflict detected while {action}. Please refresh and try again.",
            include_retry=True
        )

    # Additional methods for API compatibility
    def create_toast(
        self,
        message: str,
        type: str = "info",
        duration: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Create a toast notification (API-compatible method).
        
        Args:
            message: Notification message
            type: Notification type (success, error, warning, info)
            duration: Duration in milliseconds
            user_id: User ID (for user-specific notifications)
            
        Returns:
            Notification ID
        """
        try:
            notification_type = NotificationType(type)
        except ValueError:
            notification_type = NotificationType.INFO
        
        notification = self.create_notification(
            message=message,
            notification_type=notification_type,
            duration=duration
        )
        
        return notification["id"]

    def get_user_notifications(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get notifications for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user notifications
        """
        # For now, return all pending notifications
        # In a real implementation, this would filter by user_id
        return self.get_pending_notifications() 