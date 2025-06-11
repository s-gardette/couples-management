"""
Logging configuration for the application.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

from app.config import settings


def setup_logging():
    """Set up logging configuration for the application."""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = logs_dir / f"app_{timestamp}.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error log file handler
    error_log_filename = logs_dir / f"error_{timestamp}.log"
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Access log file handler for uvicorn
    access_log_filename = logs_dir / f"access_{timestamp}.log"
    access_handler = logging.handlers.RotatingFileHandler(
        filename=access_log_filename,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    access_formatter = logging.Formatter(
        fmt="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    access_handler.setFormatter(access_formatter)
    
    # Configure uvicorn access logger
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(access_handler)
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_access_logger.propagate = False
    
    # Configure uvicorn logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    
    # Configure app logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Log startup message
    logging.info(f"Logging configured. Log files: {log_filename}, {error_log_filename}, {access_log_filename}")
    logging.info(f"Log level: {settings.log_level}")
    
    return {
        "app_log": str(log_filename),
        "error_log": str(error_log_filename),
        "access_log": str(access_log_filename)
    }


def get_uvicorn_log_config():
    """Get uvicorn-specific logging configuration."""
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "format": "%(asctime)s - %(client_addr)s - \"%(request_line)s\" %(status_code)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"logs/uvicorn_{timestamp}.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "access": {
                "formatter": "access",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"logs/access_{timestamp}.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default", "console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["default", "console"],
        },
    } 