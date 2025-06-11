#!/usr/bin/env python3
"""
Development server startup script with logging configuration.
"""

import os
import sys
from pathlib import Path
import uvicorn
from datetime import datetime

# Add the app directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.logging import get_uvicorn_log_config


def run_server():
    """Run the development server with proper logging configuration."""
    
    # Ensure logs directory exists
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Get current date for log files
    timestamp = datetime.now().strftime("%Y%m%d")
    
    print("🚀 Starting Household Management App Development Server")
    print(f"📁 Log files will be saved to:")
    print(f"   - Application logs: logs/app_{timestamp}.log")
    print(f"   - Error logs: logs/error_{timestamp}.log")  
    print(f"   - Access logs: logs/access_{timestamp}.log")
    print(f"   - Uvicorn logs: logs/uvicorn_{timestamp}.log")
    print()
    print("🌐 Server will be available at: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Get uvicorn logging configuration
    log_config = get_uvicorn_log_config()
    
    # Run uvicorn with logging configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=log_config,
        access_log=True,
        reload_dirs=["app", "templates", "static"],
        reload_excludes=["logs", "uploads", ".git", "__pycache__", "*.pyc"]
    )


if __name__ == "__main__":
    run_server() 