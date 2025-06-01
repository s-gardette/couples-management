"""
Admin UI module for the Household Management App.

This module provides a comprehensive web-based admin interface for:
- Managing users (view, create, edit, deactivate, delete)
- Monitoring households and their activities  
- Reviewing and managing expenses across all households
- Viewing system-wide analytics and reports
- Managing application settings and configurations
- Monitoring system health and security
"""

from .dependencies import get_current_admin_user, require_admin_auth

__all__ = [
    "get_current_admin_user",
    "require_admin_auth"
] 