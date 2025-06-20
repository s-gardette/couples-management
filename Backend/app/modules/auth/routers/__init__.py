"""
Auth module routers.
"""

from .auth import router as auth_router
from .users import router as users_router
from .frontend import router as auth_frontend_router

__all__ = [
    "auth_router",
    "users_router",
    "auth_frontend_router"
]
