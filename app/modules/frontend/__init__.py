"""
Frontend module for handling user-facing web pages and UI routes.
"""

from .routers import (
    main_router,
    expenses_router,
    households_router,
    payments_router,
    onboarding_router
)

__all__ = [
    "main_router",
    "expenses_router",
    "households_router", 
    "payments_router",
    "onboarding_router"
] 