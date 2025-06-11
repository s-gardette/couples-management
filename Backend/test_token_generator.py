#!/usr/bin/env python3
"""
Test token generator for bypassing authentication during development and testing.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from jose import jwt
from sqlalchemy.orm import Session

# Add the app directory to the path
sys.path.append('.')

from app.database import get_db
from app.config import settings
from app.modules.auth.models.user import User


def generate_test_token(user_email: str = "admin@gmail.com") -> str:
    """Generate a test JWT token for the specified user."""
    
    # Get user from database
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"User with email {user_email} not found!")
            return None
        
        # Create token payload
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "iat": now,
            "exp": now + timedelta(hours=24),  # 24 hour expiry
            "type": "access"
        }
        
        # Generate token
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        
        print(f"Generated token for user: {user.email}")
        print(f"User ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Role: {user.role}")
        print(f"Token expires: {payload['exp']}")
        print(f"\nToken: {token}")
        print(f"\nCurl example:")
        print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/households/')
        
        return token
        
    finally:
        db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@gmail.com"
    token = generate_test_token(email) 