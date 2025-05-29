"""
Comprehensive tests for authentication service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.models.user import User, UserRole
from app.modules.auth.models.password_reset import PasswordResetToken
from app.modules.auth.models.email_verification import EmailVerificationToken
from app.modules.auth.models.user_session import UserSession
from app.modules.auth.models.password_history import PasswordHistory
from app.modules.auth.schemas.user import UserCreate, UserResponse


class TestAuthServiceComprehensive:
    """Comprehensive test cases for AuthService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        db.get = Mock()
        db.rollback = Mock()
        db.flush = Mock()
        return db
    
    @pytest.fixture
    def auth_service(self, mock_db):
        """Create an AuthService instance."""
        return AuthService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        user = User()
        user.id = uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.hashed_password = "hashed_password"
        user.is_active = True
        user.email_verified = True
        user.created_at = datetime.utcnow()
        user.last_login = None
        return user

    @pytest.mark.asyncio
    async def test_register_user_success_basic(self, auth_service, mock_db):
        """Test successful basic user registration."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No existing user
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                    with patch('app.modules.auth.services.auth_service.generate_verification_token') as mock_token:
                        mock_validate_email.return_value = True
                        mock_validate_password.return_value = {"is_valid": True, "errors": []}
                        mock_hash.return_value = "hashed_password"
                        mock_token.return_value = "verification_token"
                        
                        success, message, user = await auth_service.register_user(
                            email="test@example.com",
                            username="testuser",
                            password="StrongPass123!",
                            first_name="Test",
                            last_name="User"
                        )
        
        assert success is True
        assert "successfully" in message
        assert user is not None
        mock_db.add.assert_called()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_admin_creation(self, auth_service, mock_db):
        """Test user registration by admin."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                    with patch('app.modules.auth.services.auth_service.generate_verification_token') as mock_token:
                        mock_validate_email.return_value = True
                        mock_validate_password.return_value = {"is_valid": True, "errors": []}
                        mock_hash.return_value = "hashed_password"
                        mock_token.return_value = "verification_token"
                        
                        success, message, user = await auth_service.register_user(
                            email="test@example.com",
                            username="testuser",
                            password="StrongPass123!",
                            created_by_admin=True,
                            admin_id="admin_123"
                        )
        
        assert success is True
        assert "successfully" in message

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, auth_service):
        """Test registration with invalid email."""
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            mock_validate_email.return_value = False
            
            success, message, user = await auth_service.register_user(
                email="invalid-email",
                username="testuser",
                password="StrongPass123!"
            )
        
        assert success is False
        assert "Invalid email format" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, auth_service):
        """Test registration with weak password."""
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                mock_validate_email.return_value = True
                mock_validate_password.return_value = {
                    "is_valid": False, 
                    "errors": ["Password too short", "No special characters"]
                }
                
                success, message, user = await auth_service.register_user(
                    email="test@example.com",
                    username="testuser",
                    password="weak"
                )
        
        assert success is False
        assert "Password validation failed" in message
        assert "Password too short" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, auth_service, mock_db, sample_user):
        """Test registration with existing email."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user  # Existing user
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            mock_validate_email.return_value = True
            
            success, message, user = await auth_service.register_user(
                email="test@example.com",
                username="newuser",
                password="StrongPass123!"
            )
        
        assert success is False
        assert "already registered" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_register_user_username_exists(self, auth_service, mock_db, sample_user):
        """Test registration with existing username."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        # First call returns None (email check), second returns existing user (username check)
        mock_query.first.side_effect = [None, sample_user]
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                mock_validate_email.return_value = True
                mock_validate_password.return_value = {"is_valid": True, "errors": []}
                
                success, message, user = await auth_service.register_user(
                    email="new@example.com",
                    username="testuser",
                    password="StrongPass123!"
                )
        
        assert success is False
        assert "already taken" in message
        assert user is None

    @pytest.mark.asyncio
    async def test_register_user_integrity_error(self, auth_service, mock_db):
        """Test registration with database integrity error."""
        from sqlalchemy.exc import IntegrityError
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.commit.side_effect = IntegrityError("", "", "")
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                    mock_validate_email.return_value = True
                    mock_validate_password.return_value = {"is_valid": True, "errors": []}
                    mock_hash.return_value = "hashed_password"
                    
                    success, message, user = await auth_service.register_user(
                        email="test@example.com",
                        username="testuser",
                        password="StrongPass123!"
                    )
        
        assert success is False
        assert "already exists" in message
        assert user is None
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_general_exception(self, auth_service, mock_db):
        """Test registration with general exception."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.commit.side_effect = Exception("Database error")
        
        with patch('app.modules.auth.services.auth_service.validate_email') as mock_validate_email:
            with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate_password:
                with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                    mock_validate_email.return_value = True
                    mock_validate_password.return_value = {"is_valid": True, "errors": []}
                    mock_hash.return_value = "hashed_password"
                    
                    success, message, user = await auth_service.register_user(
                        email="test@example.com",
                        username="testuser",
                        password="StrongPass123!"
                    )
        
        assert success is False
        assert "Registration failed" in message
        assert user is None
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db, sample_user):
        """Test successful user authentication."""
        # Mock database query chain
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        with patch('app.modules.auth.services.auth_service.verify_password_secure') as mock_verify:
            with patch('app.modules.auth.services.auth_service.create_user_tokens') as mock_tokens:
                with patch('app.modules.auth.services.auth_service.generate_session_token') as mock_session:
                    with patch('app.modules.auth.schemas.user.UserResponse.model_validate') as mock_user_response:
                        # Setup mocks
                        mock_verify.return_value = True
                        mock_tokens.return_value = {
                            "access_token": "access_token",
                            "refresh_token": "refresh_token",
                            "expires_in": 3600
                        }
                        mock_session.return_value = "session_token"
                        mock_user_response.return_value.model_dump.return_value = {
                            "id": str(sample_user.id),
                            "email": sample_user.email,
                            "username": sample_user.username
                        }
                        
                        # Mock the UserSession creation
                        mock_user_session = Mock()
                        with patch('app.modules.auth.services.auth_service.UserSession', return_value=mock_user_session):
                            success, message, token_data = await auth_service.authenticate_user(
                                email_or_username="test@example.com",
                                password="correct_password",
                                user_agent="Mozilla/5.0",
                                ip_address="127.0.0.1"
                            )
        
        assert success is True
        assert "successful" in message
        assert token_data is not None
        assert "access_token" in token_data
        assert "user" in token_data
        mock_db.add.assert_called_with(mock_user_session)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test authentication with non-existent user."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        success, message, token_data = await auth_service.authenticate_user(
            email_or_username="nonexistent@example.com",
            password="password"
        )
        
        assert success is False
        assert "Invalid credentials" in message
        assert token_data is None

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, auth_service, mock_db, sample_user):
        """Test authentication with inactive user."""
        sample_user.is_active = False
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        success, message, token_data = await auth_service.authenticate_user(
            email_or_username="test@example.com",
            password="password"
        )
        
        assert success is False
        assert "deactivated" in message
        assert token_data is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, auth_service, mock_db, sample_user):
        """Test authentication with wrong password."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        with patch('app.modules.auth.services.auth_service.verify_password_secure') as mock_verify:
            mock_verify.return_value = False
            
            success, message, token_data = await auth_service.authenticate_user(
                email_or_username="test@example.com",
                password="wrong_password"
            )
        
        assert success is False
        assert "Invalid credentials" in message
        assert token_data is None

    @pytest.mark.asyncio
    async def test_logout_user_success(self, auth_service, mock_db):
        """Test successful user logout."""
        user_id = uuid4()
        access_token = "access_token"
        session_token = "session_token"
        
        # Mock session query
        mock_session = Mock()
        mock_session.is_active = True
        mock_session.deactivate = Mock()  # Add deactivate method
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_session
        
        with patch('app.modules.auth.services.auth_service.blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = True  # Return True for success
            
            success, message = await auth_service.logout_user(
                user_id=user_id,
                access_token=access_token,
                session_token=session_token
            )
        
        assert success is True
        assert "successful" in message
        mock_session.deactivate.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_user_no_session(self, auth_service, mock_db):
        """Test logout when session not found."""
        user_id = uuid4()
        access_token = "access_token"
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        with patch('app.modules.auth.services.auth_service.blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = True  # Return True for success
            
            success, message = await auth_service.logout_user(
                user_id=user_id,
                access_token=access_token
            )
        
        assert success is True
        assert "successful" in message

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, auth_service, mock_db, sample_user):
        """Test successful password reset request."""
        # Mock user query
        mock_user_query = Mock()
        mock_user_query.filter.return_value = mock_user_query
        mock_user_query.first.return_value = sample_user
        
        # Mock existing tokens query
        mock_tokens_query = Mock()
        mock_tokens_query.filter.return_value = mock_tokens_query
        mock_tokens_query.all.return_value = []  # No existing tokens
        
        # Setup query side effects for different calls
        mock_db.query.side_effect = [mock_user_query, mock_tokens_query]
        
        with patch('app.modules.auth.services.auth_service.generate_password_reset_token_secure') as mock_token:
            with patch('app.modules.auth.services.auth_service.mask_email') as mock_mask:
                with patch('app.modules.auth.models.password_reset.PasswordResetToken') as mock_reset_token_class:
                    mock_token.return_value = "reset_token"
                    mock_mask.return_value = "t***@example.com"
                    mock_reset_token_instance = Mock()
                    mock_reset_token_class.return_value = mock_reset_token_instance
                    
                    # Don't patch the class used in the query, just the constructor
                    success, message, masked_email = await auth_service.request_password_reset(
                        email="test@example.com"
                    )
        
        assert success is True
        assert "sent" in message
        assert masked_email == "t***@example.com"
        mock_db.add.assert_called()  # Just check that add was called
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_user_not_found(self, auth_service, mock_db):
        """Test password reset request for non-existent user."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        with patch('app.modules.auth.services.auth_service.mask_email') as mock_mask:
            mock_mask.return_value = "n***@example.com"
            
            success, message, masked_email = await auth_service.request_password_reset(
                email="nonexistent@example.com"
            )
        
        # For security reasons, the service returns success=True even for non-existent users
        assert success is True
        assert "reset link has been sent" in message
        assert masked_email == "n***@example.com"

    @pytest.mark.asyncio
    async def test_request_password_reset_inactive_user(self, auth_service, mock_db, sample_user):
        """Test password reset request for inactive user."""
        sample_user.is_active = False
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        success, message, masked_email = await auth_service.request_password_reset(
            email="test@example.com"
        )
        
        assert success is False
        assert "deactivated" in message
        assert masked_email is None

    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service, mock_db, sample_user):
        """Test successful password reset."""
        # Mock password reset token
        reset_token = Mock()
        reset_token.user_id = sample_user.id
        reset_token.token = "reset_token"
        reset_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        reset_token.is_used = False
        reset_token.mark_as_used = Mock()
        
        # Mock password history query
        mock_history_query = Mock()
        mock_history_query.filter.return_value = mock_history_query
        mock_history_query.order_by.return_value = mock_history_query
        mock_history_query.limit.return_value = mock_history_query
        mock_history_query.all.return_value = []  # No password history
        
        # Setup query side effects for different calls
        def query_side_effect(model):
            if model == PasswordResetToken:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = reset_token
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = sample_user
                return mock_query
            else:  # PasswordHistory
                return mock_history_query
        
        mock_db.query.side_effect = query_side_effect
        
        with patch('app.modules.auth.services.auth_service.validate_password_strength_detailed') as mock_validate:
            with patch('app.modules.auth.services.auth_service.hash_password') as mock_hash:
                with patch('app.modules.auth.services.auth_service.check_password_history') as mock_check_history:
                    with patch('app.modules.auth.services.auth_service.PasswordHistory') as mock_password_history_class:
                        mock_validate.return_value = {"is_valid": True, "errors": []}
                        mock_hash.return_value = "new_hashed_password"
                        mock_check_history.return_value = (True, None)  # Password allowed
                        mock_password_history_instance = Mock()
                        mock_password_history_class.return_value = mock_password_history_instance
                        
                        success, message = await auth_service.reset_password(
                            token="reset_token",
                            new_password="NewStrongPass123!"
                        )
        
        assert success is True
        assert "successfully" in message
        reset_token.mark_as_used.assert_called_once()
        assert sample_user.hashed_password == "new_hashed_password"
        mock_db.add.assert_called_with(mock_password_history_instance)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, auth_service, mock_db):
        """Test password reset with invalid token."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        success, message = await auth_service.reset_password(
            token="invalid_token",
            new_password="NewStrongPass123!"
        )
        
        assert success is False
        assert "Invalid or expired" in message

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, auth_service, mock_db):
        """Test password reset with expired token."""
        # The service filters out expired tokens in the query, so it returns None
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Expired tokens are filtered out
        
        success, message = await auth_service.reset_password(
            token="expired_token",
            new_password="NewStrongPass123!"
        )
        
        assert success is False
        assert "Invalid or expired" in message

    @pytest.mark.asyncio
    async def test_reset_password_used_token(self, auth_service, mock_db):
        """Test password reset with already used token."""
        # The service filters out used tokens in the query, so it returns None
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Used tokens are filtered out
        
        success, message = await auth_service.reset_password(
            token="used_token",
            new_password="NewStrongPass123!"
        )
        
        assert success is False
        assert "Invalid or expired" in message

    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_service, mock_db, sample_user):
        """Test successful email verification."""
        sample_user.email_verified = False
        
        # Mock verification token
        verification_token = Mock()
        verification_token.user_id = sample_user.id
        verification_token.token = "verification_token"
        verification_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        verification_token.is_used = False
        verification_token.mark_as_used = Mock()
        
        # Setup query side effects for different calls
        def query_side_effect(model):
            if model == EmailVerificationToken:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = verification_token
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = sample_user
                return mock_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        success, message = await auth_service.verify_email(token="verification_token")
        
        assert success is True
        assert "verified" in message
        assert sample_user.email_verified is True
        verification_token.mark_as_used.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_service, mock_db):
        """Test email verification with invalid token."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        success, message = await auth_service.verify_email(token="invalid_token")
        
        assert success is False
        assert "Invalid or expired" in message

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(self, auth_service, mock_db, sample_user):
        """Test email verification when already verified."""
        sample_user.email_verified = True
        
        verification_token = Mock()
        verification_token.user_id = sample_user.id
        verification_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        verification_token.is_used = False
        
        # Setup query side effects for different calls
        def query_side_effect(model):
            if model == EmailVerificationToken:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = verification_token
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = sample_user
                return mock_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        success, message = await auth_service.verify_email(token="verification_token")
        
        assert success is True
        assert "verified" in message

    @pytest.mark.asyncio
    async def test_resend_verification_email_success(self, auth_service, mock_db, sample_user):
        """Test successful verification email resend."""
        sample_user.email_verified = False
        
        # Mock existing tokens query
        mock_tokens_query = Mock()
        mock_tokens_query.filter.return_value = mock_tokens_query
        mock_tokens_query.all.return_value = []  # No existing tokens
        
        # Setup query side effects for different calls
        def query_side_effect(model):
            if model == User:
                mock_query = Mock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = sample_user
                return mock_query
            elif model == EmailVerificationToken:
                return mock_tokens_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        with patch('app.modules.auth.services.auth_service.generate_verification_token') as mock_token:
            with patch('app.modules.auth.models.email_verification.EmailVerificationToken') as mock_verification_token_class:
                mock_token.return_value = "new_verification_token"
                mock_verification_token_instance = Mock()
                mock_verification_token_class.return_value = mock_verification_token_instance
                
                success, message = await auth_service.resend_verification_email(
                    email="test@example.com"
                )
        
        assert success is True
        assert "sent" in message
        mock_db.add.assert_called()  # Just check that add was called
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_resend_verification_email_user_not_found(self, auth_service, mock_db):
        """Test verification email resend for non-existent user."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        success, message = await auth_service.resend_verification_email(
            email="nonexistent@example.com"
        )
        
        assert success is False
        assert "not found" in message

    @pytest.mark.asyncio
    async def test_resend_verification_email_already_verified(self, auth_service, mock_db, sample_user):
        """Test verification email resend when already verified."""
        sample_user.email_verified = True
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_user
        
        success, message = await auth_service.resend_verification_email(
            email="test@example.com"
        )
        
        assert success is False
        assert "already verified" in message 