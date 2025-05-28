"""
Tests for JWT token system.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from app.modules.auth.models.token_blacklist import TokenBlacklist
from app.modules.auth.utils.jwt import (
    blacklist_token,
    create_user_tokens,
    generate_api_key,
    jwt_manager,
    logout_user_all_devices,
    verify_access_token,
    verify_refresh_token,
)


class TestJWTManager:
    """Test JWT manager functionality."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        assert isinstance(jti, str)
        assert len(jti) == 36  # UUID length with hyphens

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = uuid4()
        token, jti = jwt_manager.create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 50
        assert isinstance(jti, str)
        assert len(jti) == 36

    def test_create_token_pair(self):
        """Test creating both access and refresh tokens."""
        user_id = uuid4()
        tokens = jwt_manager.create_token_pair(user_id)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert "access_jti" in tokens
        assert "refresh_jti" in tokens

        assert tokens["token_type"] == "bearer"
        assert isinstance(tokens["expires_in"], int)

    def test_create_token_with_additional_claims(self):
        """Test creating tokens with additional claims."""
        user_id = uuid4()
        additional_claims = {
            "role": "admin",
            "permissions": ["read", "write"]
        }

        token, jti = jwt_manager.create_access_token(user_id, additional_claims)
        claims = jwt_manager.get_token_claims(token)

        assert claims["role"] == "admin"
        assert claims["permissions"] == ["read", "write"]

    def test_get_token_claims(self):
        """Test getting token claims without verification."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        claims = jwt_manager.get_token_claims(token)

        assert claims["sub"] == str(user_id)
        assert claims["type"] == "access"
        assert claims["jti"] == jti
        assert "exp" in claims
        assert "iat" in claims


class TestTokenVerification:
    """Test token verification functionality."""

    def test_verify_valid_access_token(self, db_session):
        """Test verifying a valid access token."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        payload = jwt_manager.verify_token(token, db_session, expected_type="access")

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert payload["jti"] == jti

    def test_verify_valid_refresh_token(self, db_session):
        """Test verifying a valid refresh token."""
        user_id = uuid4()
        token, jti = jwt_manager.create_refresh_token(user_id)

        payload = jwt_manager.verify_token(token, db_session, expected_type="refresh")

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti

    def test_verify_wrong_token_type(self, db_session):
        """Test verifying token with wrong expected type."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        # Try to verify access token as refresh token
        payload = jwt_manager.verify_token(token, db_session, expected_type="refresh")

        assert payload is None

    def test_verify_invalid_token(self, db_session):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"

        payload = jwt_manager.verify_token(invalid_token, db_session)

        assert payload is None

    def test_verify_expired_token(self, db_session):
        """Test verifying an expired token."""
        user_id = uuid4()
        # Create token that expires immediately
        expired_delta = timedelta(seconds=-1)
        token, jti = jwt_manager.create_access_token(user_id, expires_delta=expired_delta)

        payload = jwt_manager.verify_token(token, db_session)

        assert payload is None


class TestTokenBlacklisting:
    """Test token blacklisting functionality."""

    def test_blacklist_token(self, db_session):
        """Test blacklisting a token."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        # Verify token works before blacklisting
        payload = jwt_manager.verify_token(token, db_session)
        assert payload is not None

        # Blacklist the token
        success = jwt_manager.blacklist_token(token, db_session, reason="test")
        assert success is True

        # Verify token no longer works
        payload = jwt_manager.verify_token(token, db_session)
        assert payload is None

        # Check blacklist entry was created
        blacklist_entry = db_session.query(TokenBlacklist).filter(
            TokenBlacklist.jti == jti
        ).first()
        assert blacklist_entry is not None
        assert blacklist_entry.revocation_reason == "test"

    def test_blacklist_user_tokens(self, db_session):
        """Test blacklisting all tokens for a user."""
        user_id = uuid4()

        # Create multiple tokens
        token1, jti1 = jwt_manager.create_access_token(user_id)
        token2, jti2 = jwt_manager.create_refresh_token(user_id)

        # Blacklist all user tokens
        count = jwt_manager.blacklist_user_tokens(user_id, db_session, "logout_all")
        assert count == 1  # Creates one special blacklist entry

        # Check that a blacklist entry was created
        blacklist_entries = db_session.query(TokenBlacklist).filter(
            TokenBlacklist.user_id == str(user_id)
        ).all()
        assert len(blacklist_entries) == 1
        assert blacklist_entries[0].token_type == "all"

    def test_blacklist_invalid_token(self, db_session):
        """Test blacklisting an invalid token."""
        invalid_token = "invalid.token.here"

        success = jwt_manager.blacklist_token(invalid_token, db_session)
        assert success is False


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_access_token(self, db_session):
        """Test refreshing an access token."""
        user_id = uuid4()
        refresh_token, refresh_jti = jwt_manager.create_refresh_token(user_id)

        # Refresh the access token
        result = jwt_manager.refresh_access_token(refresh_token, db_session)

        assert result is not None
        assert "access_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        assert "access_jti" in result

        assert result["token_type"] == "bearer"

        # Verify the new access token works
        new_access_token = result["access_token"]
        payload = jwt_manager.verify_token(new_access_token, db_session, expected_type="access")
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_refresh_with_invalid_token(self, db_session):
        """Test refreshing with an invalid refresh token."""
        invalid_token = "invalid.token.here"

        result = jwt_manager.refresh_access_token(invalid_token, db_session)
        assert result is None

    def test_refresh_with_access_token(self, db_session):
        """Test refreshing with an access token (should fail)."""
        user_id = uuid4()
        access_token, access_jti = jwt_manager.create_access_token(user_id)

        # Try to refresh using access token (should fail)
        result = jwt_manager.refresh_access_token(access_token, db_session)
        assert result is None


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_user_tokens_function(self):
        """Test the create_user_tokens utility function."""
        user_id = uuid4()

        tokens = create_user_tokens(user_id)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"

    def test_verify_access_token_function(self, db_session):
        """Test the verify_access_token utility function."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        payload = verify_access_token(token, db_session)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_verify_refresh_token_function(self, db_session):
        """Test the verify_refresh_token utility function."""
        user_id = uuid4()
        token, jti = jwt_manager.create_refresh_token(user_id)

        payload = verify_refresh_token(token, db_session)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_blacklist_token_function(self, db_session):
        """Test the blacklist_token utility function."""
        user_id = uuid4()
        token, jti = jwt_manager.create_access_token(user_id)

        success = blacklist_token(token, db_session, "test")
        assert success is True

        # Verify token is blacklisted
        payload = verify_access_token(token, db_session)
        assert payload is None

    def test_logout_user_all_devices_function(self, db_session):
        """Test the logout_user_all_devices utility function."""
        user_id = uuid4()

        count = logout_user_all_devices(user_id, db_session)
        assert count == 1

    def test_generate_api_key(self):
        """Test API key generation."""
        user_id = uuid4()
        api_key = generate_api_key(user_id, "test-api-key", expires_days=30)

        assert isinstance(api_key, str)
        assert len(api_key) > 50

        # Verify the API key contains correct claims
        claims = jwt_manager.get_token_claims(api_key)
        assert claims["sub"] == str(user_id)
        assert claims["type"] == "api_key"
        assert claims["name"] == "test-api-key"


class TestTokenBlacklistModel:
    """Test TokenBlacklist model functionality."""

    def test_is_token_blacklisted(self, db_session):
        """Test checking if a token is blacklisted."""
        jti = str(uuid4())

        # Token should not be blacklisted initially
        assert TokenBlacklist.is_token_blacklisted(db_session, jti) is False

        # Add token to blacklist
        TokenBlacklist.blacklist_token(
            db=db_session,
            jti=jti,
            token_type="access",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            reason="test"
        )

        # Token should now be blacklisted
        assert TokenBlacklist.is_token_blacklisted(db_session, jti) is True

    def test_cleanup_expired_tokens(self, db_session):
        """Test cleaning up expired blacklisted tokens."""
        # Create expired token
        expired_jti = str(uuid4())
        TokenBlacklist.blacklist_token(
            db=db_session,
            jti=expired_jti,
            token_type="access",
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            reason="test"
        )

        # Create non-expired token
        valid_jti = str(uuid4())
        TokenBlacklist.blacklist_token(
            db=db_session,
            jti=valid_jti,
            token_type="access",
            expires_at=datetime.utcnow() + timedelta(hours=1),  # Not expired
            reason="test"
        )

        # Clean up expired tokens
        deleted_count = TokenBlacklist.cleanup_expired_tokens(db_session)
        assert deleted_count == 1

        # Verify only expired token was deleted
        assert TokenBlacklist.is_token_blacklisted(db_session, expired_jti) is False
        assert TokenBlacklist.is_token_blacklisted(db_session, valid_jti) is True


if __name__ == "__main__":
    # Run a quick test
    print("Testing JWT system...")

    # Test token creation
    user_id = uuid4()
    tokens = create_user_tokens(user_id)
    print(f"Created tokens: {list(tokens.keys())}")

    # Test token claims
    claims = jwt_manager.get_token_claims(tokens["access_token"])
    print(f"Token claims: {claims}")

    print("JWT system tests completed!")
