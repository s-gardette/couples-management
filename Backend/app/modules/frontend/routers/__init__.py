"""
Frontend routers module.
"""

from .main import router as main_router
from .expenses import router as expenses_router
from .households import router as households_router
from .payments import router as payments_router
from .onboarding import router as onboarding_router

__all__ = [
    "main_router",
    "expenses_router", 
    "households_router",
    "payments_router",
    "onboarding_router"
] 