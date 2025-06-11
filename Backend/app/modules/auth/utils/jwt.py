"""
Enhanced JWT utilities for the auth module.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.auth.models.token_blacklist import TokenBlacklist


class JWTManager:
    """Enhanced JWT token manager with blacklisting and custom claims."""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(
        self,
        user_id: UUID,
        additional_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None
    ) -> tuple[str, str]:
        """
        Create an access token with custom claims.

        Args:
            user_id: User UUID
            additional_claims: Additional claims to include
            expires_delta: Custom expiration time

        Returns:
            Tuple of (token, jti)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        jti = str(uuid4())

        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "access",
            "token_version": 1  # For future token versioning
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti

    def create_refresh_token(
        self,
        user_id: UUID,
        additional_claims: dict[str, Any] | None = None
    ) -> tuple[str, str]:
        """
        Create a refresh token.

        Args:
            user_id: User UUID
            additional_claims: Additional claims to include

        Returns:
            Tuple of (token, jti)
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        jti = str(uuid4())

        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "refresh",
            "token_version": 1
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti

    def create_token_pair(
        self,
        user_id: UUID,
        additional_claims: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User UUID
            additional_claims: Additional claims to include

        Returns:
            Dictionary with token information
        """
        access_token, access_jti = self.create_access_token(user_id, additional_claims)
        refresh_token, refresh_jti = self.create_refresh_token(user_id, additional_claims)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "access_jti": access_jti,
            "refresh_jti": refresh_jti
        }

    def verify_token(
        self,
        token: str,
        db: Session,
        expected_type: str | None = None
    ) -> dict[str, Any] | None:
        """
        Verify a token and check if it's blacklisted.

        Args:
            token: JWT token to verify
            db: Database session
            expected_type: Expected token type (access, refresh)

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            # Check token type if specified
            if expected_type and payload.get("type") != expected_type:
                return None

            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and TokenBlacklist.is_token_blacklisted(db, jti):
                return None

            return payload

        except jwt.PyJWTError:
            return None

    def refresh_access_token(
        self,
        refresh_token: str,
        db: Session
    ) -> dict[str, Any] | None:
        """
        Create a new access token using a refresh token.

        Args:
            refresh_token: Valid refresh token
            db: Database session

        Returns:
            New token pair or None if refresh token is invalid
        """
        payload = self.verify_token(refresh_token, db, expected_type="refresh")
        if not payload:
            return None

        user_id = UUID(payload["sub"])

        # Create new access token
        access_token, access_jti = self.create_access_token(user_id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "access_jti": access_jti
        }

    def blacklist_token(
        self,
        token: str,
        db: Session,
        reason: str | None = None
    ) -> bool:
        """
        Blacklist a token.

        Args:
            token: Token to blacklist
            db: Database session
            reason: Reason for blacklisting

        Returns:
            True if token was blacklisted successfully
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            jti = payload.get("jti")
            if not jti:
                return False

            TokenBlacklist.blacklist_token(
                db=db,
                jti=jti,
                token_type=payload.get("type", "unknown"),
                expires_at=datetime.fromtimestamp(payload["exp"]),
                user_id=payload.get("sub"),
                reason=reason,
                token_hash=self._hash_token(token)
            )

            return True

        except jwt.PyJWTError:
            return False

    def blacklist_user_tokens(
        self,
        user_id: UUID,
        db: Session,
        reason: str = "user_logout_all"
    ) -> int:
        """
        Blacklist all tokens for a user.

        Args:
            user_id: User UUID
            db: Database session
            reason: Reason for blacklisting

        Returns:
            Number of tokens blacklisted
        """
        return TokenBlacklist.blacklist_user_tokens(
            db=db,
            user_id=str(user_id),
            reason=reason
        )

    def get_token_claims(self, token: str) -> dict[str, Any] | None:
        """
        Get token claims without verification (for debugging).

        Args:
            token: JWT token

        Returns:
            Token claims or None if invalid format
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
        except jwt.PyJWTError:
            return None

    def _hash_token(self, token: str) -> str:
        """
        Create a hash of the token for storage.

        Args:
            token: JWT token

        Returns:
            SHA256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()


# Global JWT manager instance
jwt_manager = JWTManager()


def create_user_tokens(user_id: UUID, **kwargs) -> dict[str, Any]:
    """
    Create access and refresh tokens for a user.

    Args:
        user_id: User UUID
        **kwargs: Additional claims

    Returns:
        Token pair dictionary
    """
    return jwt_manager.create_token_pair(user_id, kwargs if kwargs else None)


def verify_access_token(token: str, db: Session) -> dict[str, Any] | None:
    """
    Verify an access token.

    Args:
        token: Access token
        db: Database session

    Returns:
        Token payload or None if invalid
    """
    return jwt_manager.verify_token(token, db, expected_type="access")


def verify_refresh_token(token: str, db: Session) -> dict[str, Any] | None:
    """
    Verify a refresh token.

    Args:
        token: Refresh token
        db: Database session

    Returns:
        Token payload or None if invalid
    """
    return jwt_manager.verify_token(token, db, expected_type="refresh")


def refresh_access_token(refresh_token: str, db: Session) -> dict[str, Any] | None:
    """
    Refresh an access token.

    Args:
        refresh_token: Valid refresh token
        db: Database session

    Returns:
        New access token or None if refresh token is invalid
    """
    return jwt_manager.refresh_access_token(refresh_token, db)


def blacklist_token(token: str, db: Session, reason: str | None = None) -> bool:
    """
    Blacklist a token.

    Args:
        token: Token to blacklist
        db: Database session
        reason: Reason for blacklisting

    Returns:
        True if successful
    """
    return jwt_manager.blacklist_token(token, db, reason)


def logout_user_all_devices(user_id: UUID, db: Session) -> int:
    """
    Logout user from all devices by blacklisting all tokens.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Number of tokens blacklisted
    """
    return jwt_manager.blacklist_user_tokens(user_id, db, "logout_all_devices")


def cleanup_expired_blacklisted_tokens(db: Session) -> int:
    """
    Clean up expired blacklisted tokens.

    Args:
        db: Database session

    Returns:
        Number of tokens cleaned up
    """
    return TokenBlacklist.cleanup_expired_tokens(db)


def generate_api_key(user_id: UUID, name: str, expires_days: int = 365) -> str:
    """
    Generate a long-lived API key for a user.

    Args:
        user_id: User UUID
        name: API key name/description
        expires_days: Expiration in days

    Returns:
        API key token
    """
    expire = datetime.utcnow() + timedelta(days=expires_days)
    jti = str(uuid4())

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "type": "api_key",
        "name": name,
        "token_version": 1
    }

    return jwt.encode(payload, jwt_manager.secret_key, algorithm=jwt_manager.algorithm)
