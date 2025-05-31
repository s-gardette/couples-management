"""
Expenses routers module.
"""

from .households import router as households_router
from .expenses import router as expenses_router
from .categories import router as categories_router
from .analytics import router as analytics_router

__all__ = [
    "households_router",
    "expenses_router",
    "categories_router",
    "analytics_router",
]
