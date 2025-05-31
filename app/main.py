"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.database import get_db
from app.core.routers import health
from app.modules.auth.routers import auth_router, users_router
from app.modules.auth.routers.admin import router as admin_router
from app.modules.auth.dependencies import require_authentication, get_current_user_optional, get_current_user_from_cookie_or_header
from app.modules.auth.utils.startup import initialize_auth_system
from app.modules.auth.schemas.admin import AdminAccessRestrictedResponse
from app.modules.expenses.routers import (
    households_router,
    expenses_router,
    categories_router,
    analytics_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting Household Management App...")
    
    # Initialize auth system
    db = next(get_db())
    try:
        init_results = await initialize_auth_system(db)
        print(f"✅ Auth system initialized: {init_results}")
    except Exception as e:
        print(f"❌ Auth system initialization failed: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Household Management App...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers with mandatory authentication
if settings.require_authentication_for_all:
    # Include auth router without global authentication dependency
    # Individual endpoints will handle their own authentication requirements
    app.include_router(auth_router, prefix="/api")
    
    # All other routes require authentication
    app.include_router(health.router, prefix="/health", tags=["health"], dependencies=[Depends(require_authentication)])
    app.include_router(users_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(admin_router, prefix="/api", dependencies=[Depends(require_authentication)])
    
    # Expenses module routers
    app.include_router(households_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(expenses_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(categories_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(analytics_router, prefix="/api", dependencies=[Depends(require_authentication)])
else:
    # Normal routing (for development)
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    
    # Expenses module routers (development mode)
    app.include_router(households_router, prefix="/api")
    app.include_router(expenses_router, prefix="/api")
    app.include_router(categories_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")


# Access restricted page (only public endpoint)
@app.get("/access-restricted", response_class=HTMLResponse)
async def access_restricted(request: Request):
    """Access restricted page - only public endpoint available."""
    return templates.TemplateResponse(
        request, 
        "auth/access_restricted.html",
        {
            "admin_contact_email": settings.admin_contact_email,
            "admin_contact_message": settings.admin_contact_message,
            "app_name": settings.app_name
        }
    )


# Login page (public endpoint)
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page - public endpoint."""
    return templates.TemplateResponse(
        request, 
        "auth/login.html",
        {
            "config": settings,
            "admin_contact_email": settings.admin_contact_email
        }
    )


# Root endpoint - requires authentication
@app.get("/")
async def root(
    request: Request,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """Root endpoint - redirects to login if not authenticated, shows home if authenticated."""
    if settings.require_authentication_for_all:
        if not current_user:
            # Redirect to login page
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        # User is authenticated, show home page
        return templates.TemplateResponse(
            request, 
            "home.html",
            {"current_user": current_user}
        )
    else:
        # Development mode - no auth required
        return templates.TemplateResponse(
            request, 
            "home.html",
            {"current_user": current_user}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
