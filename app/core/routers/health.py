"""
Health check endpoints for monitoring application status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/db")
async def database_health_check(db: Session = Depends(get_db)):
    """Database connectivity health check."""
    try:
        # Execute a simple query to test database connectivity
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        return {
            "status": "healthy",
            "database": "connected",
            "message": "Database connection successful"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with all system components."""
    health_status = {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {}
    }

    # Check database
    try:
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Add more component checks here as needed
    # (Redis, external APIs, etc.)

    return health_status
