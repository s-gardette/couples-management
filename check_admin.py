#!/usr/bin/env python3
"""
Script to check if admin user exists and verify credentials.
"""

import asyncio
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import AuthService
from app.config import settings

def check_admin_user():
    """Check if admin user exists and verify credentials."""
    db = next(get_db())
    
    try:
        # Check by email
        admin_by_email = db.query(User).filter(User.email == settings.default_admin_email).first()
        print(f"Admin by email ({settings.default_admin_email}): {admin_by_email}")
        
        # Check by username
        admin_by_username = db.query(User).filter(User.username == settings.default_admin_username).first()
        print(f"Admin by username ({settings.default_admin_username}): {admin_by_username}")
        
        # List all users
        all_users = db.query(User).all()
        print(f"\nAll users in database ({len(all_users)}):")
        for user in all_users:
            print(f"  - ID: {user.id}, Email: {user.email}, Username: {user.username}, Role: {user.role}, Active: {user.is_active}")
        
        # Test authentication
        if admin_by_email:
            auth_service = AuthService(db)
            print(f"\nTesting authentication for {admin_by_email.email}...")
            
            # Test password verification
            from app.modules.auth.utils.password import verify_password
            password_valid = verify_password(settings.default_admin_password, admin_by_email.hashed_password)
            print(f"Password verification result: {password_valid}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_user() 