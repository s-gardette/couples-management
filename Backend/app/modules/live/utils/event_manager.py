"""
Event Manager

Handles event-driven updates and communication between different parts of the application.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be triggered."""
    # Expense events
    EXPENSE_CREATED = "expense_created"
    EXPENSE_UPDATED = "expense_updated"
    EXPENSE_DELETED = "expense_deleted"
    EXPENSE_PAID = "expense_paid"
    
    # Payment events
    PAYMENT_CREATED = "payment_created"
    PAYMENT_UPDATED = "payment_updated"
    PAYMENT_DELETED = "payment_deleted"
    
    # Balance events
    BALANCE_UPDATED = "balance_updated"
    BALANCE_RECALCULATED = "balance_recalculated"
    
    # User events
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    
    # System events
    DATA_REFRESH = "data_refresh"
    NOTIFICATION_CREATED = "notification_created"


class EventManager:
    """Manages events and event listeners for live updates."""

    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 100  # Keep last 100 events

    def subscribe(self, event_type: EventType, callback: Callable) -> bool:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for
            callback: Function to call when event is triggered
            
        Returns:
            Boolean indicating success
        """
        try:
            if event_type not in self.listeners:
                self.listeners[event_type] = []
            
            self.listeners[event_type].append(callback)
            logger.debug(f"Subscribed to event: {event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to event {event_type.value}: {e}")
            return False

    def unsubscribe(self, event_type: EventType, callback: Callable) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to stop listening for
            callback: Function to remove from listeners
            
        Returns:
            Boolean indicating success
        """
        try:
            if event_type in self.listeners:
                if callback in self.listeners[event_type]:
                    self.listeners[event_type].remove(callback)
                    logger.debug(f"Unsubscribed from event: {event_type.value}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing from event {event_type.value}: {e}")
            return False

    def emit(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        household_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> bool:
        """
        Emit an event to all listeners.
        
        Args:
            event_type: Type of event being emitted
            data: Optional data to pass to listeners
            household_id: Optional household ID for scoped events
            user_id: Optional user ID for user-specific events
            
        Returns:
            Boolean indicating if event was processed successfully
        """
        try:
            event_data = {
                "type": event_type.value,
                "data": data or {},
                "household_id": str(household_id) if household_id else None,
                "user_id": str(user_id) if user_id else None,
                "timestamp": datetime.utcnow().isoformat(),
                "event_id": f"{event_type.value}_{datetime.utcnow().timestamp()}"
            }

            # Add to history
            self.event_history.append(event_data)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

            # Call all listeners for this event type
            if event_type in self.listeners:
                for callback in self.listeners[event_type]:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logger.error(f"Error in event listener for {event_type.value}: {e}")

            logger.debug(f"Emitted event: {event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Error emitting event {event_type.value}: {e}")
            return False

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events from history."""
        return self.event_history[-limit:]

    def get_events_by_type(self, event_type: EventType, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events of a specific type."""
        filtered_events = [
            event for event in self.event_history
            if event["type"] == event_type.value
        ]
        return filtered_events[-limit:]

    def get_events_for_household(self, household_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent events for a specific household."""
        household_str = str(household_id)
        filtered_events = [
            event for event in self.event_history
            if event["household_id"] == household_str
        ]
        return filtered_events[-limit:]

    def clear_history(self) -> int:
        """Clear event history and return count of cleared events."""
        count = len(self.event_history)
        self.event_history.clear()
        return count

    # Convenience methods for common events
    def expense_created(self, expense_id: UUID, household_id: UUID, user_id: UUID, data: Dict[str, Any] = None):
        """Emit expense created event."""
        event_data = {
            "expense_id": str(expense_id),
            **(data or {})
        }
        return self.emit(EventType.EXPENSE_CREATED, event_data, household_id, user_id)

    def expense_updated(self, expense_id: UUID, household_id: UUID, user_id: UUID, changes: Dict[str, Any] = None):
        """Emit expense updated event."""
        event_data = {
            "expense_id": str(expense_id),
            "changes": changes or {}
        }
        return self.emit(EventType.EXPENSE_UPDATED, event_data, household_id, user_id)

    def expense_deleted(self, expense_id: UUID, household_id: UUID, user_id: UUID):
        """Emit expense deleted event."""
        event_data = {"expense_id": str(expense_id)}
        return self.emit(EventType.EXPENSE_DELETED, event_data, household_id, user_id)

    def payment_created(self, payment_id: UUID, household_id: UUID, user_id: UUID, amount: float, data: Dict[str, Any] = None):
        """Emit payment created event."""
        event_data = {
            "payment_id": str(payment_id),
            "amount": amount,
            **(data or {})
        }
        return self.emit(EventType.PAYMENT_CREATED, event_data, household_id, user_id)

    def payment_deleted(self, payment_id: UUID, household_id: UUID, user_id: UUID, amount: float):
        """Emit payment deleted event."""
        event_data = {
            "payment_id": str(payment_id),
            "amount": amount
        }
        return self.emit(EventType.PAYMENT_DELETED, event_data, household_id, user_id)

    def balance_updated(self, household_id: UUID, user_id: UUID, new_balances: Dict[str, Any]):
        """Emit balance updated event."""
        event_data = {"balances": new_balances}
        return self.emit(EventType.BALANCE_UPDATED, event_data, household_id, user_id)

    def data_refresh(self, household_id: UUID, refresh_type: str = "all"):
        """Emit data refresh event."""
        event_data = {"refresh_type": refresh_type}
        return self.emit(EventType.DATA_REFRESH, event_data, household_id)


# Global event manager instance
event_manager = EventManager() 