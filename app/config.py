"""
Application configuration module.
Handles environment variables and application settings.
"""

import os
from typing import List, Optional
from functools import lru_cache

from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Application Configuration
    app_name: str = "Household Management App"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "production"
    
    # Database Configuration
    database_url: str
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "couples_management"
    database_user: str = "couples_user"
    database_password: str
    
    # Security Configuration
    secret_key: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:8000"
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # Static Files Configuration
    static_url: str = "/static"
    static_dir: str = "static"
    templates_dir: str = "templates"
    
    # Upload Configuration
    upload_dir: str = "uploads"
    max_upload_size: int = 10485760  # 10MB
    allowed_upload_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "pdf"]
    
    # Email Configuration
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    smtp_ssl: bool = False
    email_reset_token_expire_hours: int = 48
    
    # Redis Configuration
    redis_url: Optional[str] = None
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Auth Module Configuration
    auth_password_min_length: int = 8
    auth_password_require_uppercase: bool = True
    auth_password_require_lowercase: bool = True
    auth_password_require_numbers: bool = True
    auth_password_require_special: bool = True
    auth_max_login_attempts: int = 5
    auth_lockout_duration_minutes: int = 15
    
    # Expenses Module Configuration
    expenses_default_currency: str = "USD"
    expenses_max_amount: float = 999999.99
    expenses_categories_limit: int = 50
    expenses_receipt_max_size: int = 5242880  # 5MB
    
    # Household Module Configuration
    household_max_members: int = 20
    household_invite_code_length: int = 8
    household_invite_code_expiry_days: int = 7
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from string or list."""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from string or list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v
    
    @field_validator("allowed_upload_extensions", mode="before")
    @classmethod
    def parse_upload_extensions(cls, v):
        """Parse upload extensions from string or list."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Create settings instance
settings = get_settings() 