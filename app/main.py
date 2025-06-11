"""
Main FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.core.logging import setup_logging
from app.core.routers import health
from app.modules.auth.routers import auth_router, users_router, auth_frontend_router
from app.modules.auth.routers.admin import router as admin_router
from app.modules.admin.routers import admin_ui_router
from app.modules.auth.dependencies import require_authentication, get_current_user_optional, get_current_user_from_cookie_or_header
from app.modules.auth.utils.startup import initialize_auth_system
from app.modules.expenses.routers import (
    households_router,
    expenses_router,
    categories_router,
    analytics_router,
    payments_router,
    balances_router
)
from app.modules.live.routers import live_router
from app.modules.frontend import (
    main_router,
    expenses_router as frontend_expenses_router,
    households_router as frontend_households_router,
    payments_router as frontend_payments_router,
    onboarding_router
)
from app.modules.expenses.services import HouseholdService
from app.modules.expenses.models.user_household import UserHousehold
from app.modules.auth.models.user import User

# Setup logging first
log_files = setup_logging()
logger = logging.getLogger(__name__)

# Log the startup and log file locations
logger.info("=== Household Management App Starting ===")
logger.info(f"Log files created: {log_files}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Household Management App...")
    print("🚀 Starting Household Management App...")
    
    # Initialize auth system
    db = next(get_db())
    try:
        init_results = await initialize_auth_system(db)
        logger.info(f"✅ Auth system initialized: {init_results}")
        print(f"✅ Auth system initialized: {init_results}")
    except Exception as e:
        logger.error(f"❌ Auth system initialization failed: {e}", exc_info=True)
        print(f"❌ Auth system initialization failed: {e}")
    finally:
        db.close()
    
    logger.info("Application startup complete")
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Household Management App...")
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

# Setup Enhanced Jinja2 templates with automatic global context
from app.core.templates import templates

logger.info("FastAPI application configured")

# Include routers with mandatory authentication
if settings.require_authentication_for_all:
    # Include auth router without global authentication dependency
    # Individual endpoints will handle their own authentication requirements
    app.include_router(auth_router, prefix="/api")
    
    # Auth frontend router for join and other auth-related frontend functionality
    app.include_router(auth_frontend_router)
    
    # Health endpoint should always be public (no authentication required)
    app.include_router(health.router, prefix="/health", tags=["health"])
    
    # All other API routes require authentication
    app.include_router(users_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(admin_router, prefix="/api", dependencies=[Depends(require_authentication)])
    
    # Admin UI router - uses its own admin authentication
    app.include_router(admin_ui_router)
    
    # API Expenses module routers
    app.include_router(households_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(expenses_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(categories_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(analytics_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(payments_router, prefix="/api", dependencies=[Depends(require_authentication)])
    app.include_router(balances_router, prefix="/api", dependencies=[Depends(require_authentication)])
    
    # Live updates module router (handles its own authentication per endpoint)
    app.include_router(live_router)
    
    # Frontend module routers (these handle their own authentication)
    app.include_router(main_router)
    app.include_router(frontend_expenses_router)
    app.include_router(frontend_households_router)
    app.include_router(frontend_payments_router)
    app.include_router(onboarding_router)
else:
    # Normal routing (for development)
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    
    # Auth frontend router for join and other auth-related frontend functionality
    app.include_router(auth_frontend_router)
    
    # Admin UI router - uses its own admin authentication
    app.include_router(admin_ui_router)
    
    # API Expenses module routers (development mode)
    app.include_router(households_router, prefix="/api")
    app.include_router(expenses_router, prefix="/api")
    app.include_router(categories_router, prefix="/api")
    app.include_router(analytics_router, prefix="/api")
    app.include_router(payments_router, prefix="/api")
    app.include_router(balances_router, prefix="/api")
    
    # Live updates module router (development mode)
    app.include_router(live_router)
    
    # Frontend module routers
    app.include_router(main_router)
    app.include_router(frontend_expenses_router)
    app.include_router(frontend_households_router)
    app.include_router(frontend_payments_router)
    app.include_router(onboarding_router)


# ============================================================================
# SPECIAL FRONTEND/API HYBRID ROUTES (shared functionality)
# ============================================================================

# NOTE: Frontend join routes moved to auth module (app.modules.auth.routers.frontend)


# ============================================================================
# API ENDPOINTS FOR MOBILE/EXTERNAL ACCESS
# ============================================================================

@app.get("/api/join")
async def join_household_info_api(
    code: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for getting household join information using an invite code."""
    if not code:
        raise HTTPException(status_code=400, detail="Invite code is required")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        
        # Find household by invite code
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            raise HTTPException(status_code=404, detail="Invalid or expired invite code")
        
        # Check if user is already a member (if authenticated)
        is_member = False
        if current_user:
            existing_membership = db.query(UserHousehold).filter(
                UserHousehold.household_id == household.id,
                UserHousehold.user_id == current_user.id,
                UserHousehold.is_active == True
            ).first()
            is_member = existing_membership is not None
        
        return {
            "success": True,
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description,
                "invite_code": household.invite_code
            },
            "user_status": {
                "is_authenticated": current_user is not None,
                "is_member": is_member,
                "user_id": str(current_user.id) if current_user else None,
                "email": current_user.email if current_user else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in join API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request")
    finally:
        db.close()


@app.post("/api/join")
async def join_household_api(
    code: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for joining a household using an invite code."""
    if settings.require_authentication_for_all and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not code:
        raise HTTPException(status_code=400, detail="Invite code is required")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household, UserHouseholdRole
        
        # Find household by invite code
        household = db.query(Household).filter(Household.invite_code == code).first()
        
        if not household:
            raise HTTPException(status_code=404, detail="Invalid or expired invite code")
        
        # Check if user is already a member
        existing_membership = db.query(UserHousehold).filter(
            UserHousehold.household_id == household.id,
            UserHousehold.user_id == current_user.id,
            UserHousehold.is_active == True
        ).first()
        
        if existing_membership:
            return {
                "success": True,
                "message": f"You're already a member of {household.name}",
                "household": {
                    "id": str(household.id),
                    "name": household.name,
                    "description": household.description
                },
                "action": "already_member"
            }
        
        # Add user as a member (using the UserHousehold model)
        new_membership = UserHousehold(
            user_id=current_user.id,
            household_id=household.id,
            role=UserHouseholdRole.MEMBER,
            nickname=None,
            is_active=True
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        
        return {
            "success": True,
            "message": f"Successfully joined {household.name}!",
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description
            },
            "membership": {
                "id": str(new_membership.id),
                "role": new_membership.role.value,
                "joined_at": new_membership.created_at.isoformat() if new_membership.created_at else None
            },
            "action": "joined"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining household via API: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while joining the household")
    finally:
        db.close()


@app.get("/api/households/{household_id}/join-info")
async def household_join_info_api(
    request: Request,
    household_id: str,
    current_user = Depends(get_current_user_from_cookie_or_header)
):
    """API endpoint for getting household join information by household ID."""
    if settings.require_authentication_for_all and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        household_uuid = UUID(household_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid household ID format")
    
    try:
        db = next(get_db())
        from app.modules.expenses.models.household import Household
        
        # Get household
        household = db.query(Household).filter(Household.id == household_uuid).first()
        if not household:
            raise HTTPException(status_code=404, detail="Household not found")
        
        # Check if user has permission to access this household
        has_permission = False
        if current_user:
            membership = db.query(UserHousehold).filter(
                UserHousehold.household_id == household_uuid,
                UserHousehold.user_id == current_user.id,
                UserHousehold.is_active == True
            ).first()
            has_permission = membership is not None and membership.role in ["admin", "member"]
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Access denied to this household")
        
        return {
            "success": True,
            "household": {
                "id": str(household.id),
                "name": household.name,
                "description": household.description,
                "invite_code": household.invite_code,
                "join_link": f"{request.url.scheme}://{request.url.netloc}/join?code={household.invite_code}"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting household join info: {e}")
        raise HTTPException(status_code=500, detail="Error getting household information")
    finally:
        db.close()


# Favicon route
@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.svg", media_type="image/svg+xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    ) 