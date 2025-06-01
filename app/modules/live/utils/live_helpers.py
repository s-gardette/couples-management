"""
Live Helpers

Utility functions and helpers for live updates and frontend integration.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class LiveHelpers:
    """Helper functions for live updates and frontend integration."""

    @staticmethod
    def format_live_response(
        data: Any,
        success: bool = True,
        message: str = "",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format a response for live updates with standard structure.
        
        Args:
            data: The main data payload
            success: Whether the operation was successful
            message: Optional message
            meta: Optional metadata
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "success": success,
            "data": data,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "meta": meta or {}
        }
        
        return response

    @staticmethod
    def create_htmx_headers(
        trigger_events: Optional[List[str]] = None,
        refresh_targets: Optional[List[str]] = None,
        push_url: Optional[str] = None,
        redirect_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create HTMX response headers for live updates.
        
        Args:
            trigger_events: Events to trigger on the client
            refresh_targets: Targets to refresh
            push_url: URL to push to history
            redirect_url: URL to redirect to
            
        Returns:
            Dictionary of headers
        """
        headers = {}
        
        if trigger_events:
            headers["HX-Trigger"] = json.dumps(trigger_events)
        
        if refresh_targets:
            headers["HX-Refresh"] = "true"
        
        if push_url:
            headers["HX-Push-Url"] = push_url
            
        if redirect_url:
            headers["HX-Redirect"] = redirect_url
            
        return headers

    @staticmethod
    def create_live_update_payload(
        update_type: str,
        target_selector: str,
        content: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        swap_type: str = "innerHTML"
    ) -> Dict[str, Any]:
        """
        Create a live update payload for frontend consumption.
        
        Args:
            update_type: Type of update (refresh, replace, append, etc.)
            target_selector: CSS selector for the target element
            content: Optional HTML content
            data: Optional data payload
            swap_type: HTMX swap type
            
        Returns:
            Live update payload
        """
        payload = {
            "type": update_type,
            "target": target_selector,
            "swap": swap_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if content:
            payload["content"] = content
            
        if data:
            payload["data"] = data
            
        return payload

    @staticmethod
    def extract_filters_from_request(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and clean filter parameters from request data.
        
        Args:
            form_data: Raw form data from request
            
        Returns:
            Cleaned filter dictionary
        """
        filters = {}
        
        # Standard filter fields
        filter_fields = [
            'search', 'category', 'date_range', 'payment_status',
            'created_by', 'sort_by', 'min_amount', 'max_amount',
            'view_mode', 'payment_type', 'payer_payee'
        ]
        
        for field in filter_fields:
            value = form_data.get(field, '').strip()
            if value:
                # Handle numeric fields
                if field in ['min_amount', 'max_amount']:
                    try:
                        filters[field] = float(value)
                    except (ValueError, TypeError):
                        continue
                else:
                    filters[field] = value
        
        return filters

    @staticmethod
    def create_toast_notification(
        message: str,
        notification_type: str = "info",
        duration: Optional[int] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create a toast notification for frontend display.
        
        Args:
            message: Notification message
            notification_type: Type (success, error, warning, info)
            duration: Duration in milliseconds
            actions: Optional action buttons
            
        Returns:
            Toast notification dictionary
        """
        # Set default durations
        if duration is None:
            durations = {
                "error": 8000,
                "warning": 6000,
                "success": 4000,
                "info": 4000
            }
            duration = durations.get(notification_type, 4000)
        
        notification = {
            "id": f"toast_{datetime.utcnow().timestamp()}".replace(".", "_"),
            "message": message,
            "type": notification_type,
            "duration": duration,
            "actions": actions or [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        return notification

    @staticmethod
    def create_live_stats_update(
        household_id: UUID,
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a live statistics update payload.
        
        Args:
            household_id: Household ID
            stats: Statistics data
            
        Returns:
            Live stats update payload
        """
        return {
            "type": "stats_update",
            "household_id": str(household_id),
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def create_balance_update(
        household_id: UUID,
        balances: Dict[str, Any],
        trigger_refresh: bool = True
    ) -> Dict[str, Any]:
        """
        Create a balance update payload.
        
        Args:
            household_id: Household ID
            balances: Balance data
            trigger_refresh: Whether to trigger UI refresh
            
        Returns:
            Balance update payload
        """
        return {
            "type": "balance_update",
            "household_id": str(household_id),
            "balances": balances,
            "trigger_refresh": trigger_refresh,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def format_currency(amount: Union[int, float], currency: str = "USD") -> str:
        """
        Format currency amount for display.
        
        Args:
            amount: Amount to format
            currency: Currency code
            
        Returns:
            Formatted currency string
        """
        try:
            if currency == "USD":
                return f"${amount:.2f}"
            else:
                return f"{amount:.2f} {currency}"
        except (ValueError, TypeError):
            return "N/A"

    @staticmethod
    def calculate_pagination_info(
        total_items: int,
        current_page: int,
        per_page: int
    ) -> Dict[str, Any]:
        """
        Calculate pagination information.
        
        Args:
            total_items: Total number of items
            current_page: Current page number
            per_page: Items per page
            
        Returns:
            Pagination info dictionary
        """
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        
        return {
            "total_items": total_items,
            "current_page": current_page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_previous": current_page > 1,
            "has_next": current_page < total_pages,
            "previous_page": current_page - 1 if current_page > 1 else None,
            "next_page": current_page + 1 if current_page < total_pages else None,
            "start_item": (current_page - 1) * per_page + 1 if total_items > 0 else 0,
            "end_item": min(current_page * per_page, total_items)
        }

    @staticmethod
    def create_auto_save_payload(
        form_id: str,
        saved_data: Dict[str, Any],
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Create an auto-save update payload.
        
        Args:
            form_id: Form identifier
            saved_data: Data that was saved
            success: Whether save was successful
            
        Returns:
            Auto-save payload
        """
        return {
            "type": "auto_save",
            "form_id": form_id,
            "saved_data": saved_data,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def sanitize_html_content(content: str) -> str:
        """
        Basic HTML sanitization for live updates.
        
        Args:
            content: HTML content to sanitize
            
        Returns:
            Sanitized content
        """
        # Basic sanitization - in production, use a proper HTML sanitizer
        import html
        return html.escape(content)

    @staticmethod
    def create_error_response(
        error_message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error_message: Human-readable error message
            error_code: Optional error code
            details: Optional error details
            
        Returns:
            Error response dictionary
        """
        return {
            "success": False,
            "error": {
                "message": error_message,
                "code": error_code,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        } 