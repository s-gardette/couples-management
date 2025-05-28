"""
Authentication API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.auth.schemas.auth import (
    AuthResponse,
    EmailVerificationRequest,
    EmailVerificationResend,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordStrengthCheck,
    PasswordStrengthResponse,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.modules.auth.schemas.user import UserResponse
from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.utils.password import validate_password_strength_detailed

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    Creates a new user account with email verification required.
    """
    auth_service = AuthService(db)

    # Get client info for session tracking
    request.headers.get("user-agent")

    success, message, user = await auth_service.register_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return RegisterResponse(
        message=message,
        user_id=str(user.id) if user else None,
        email_verification_required=True
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access tokens.

    Validates credentials and returns JWT tokens for API access.
    """
    auth_service = AuthService(db)

    # Get client info for session tracking
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    success, message, token_data = await auth_service.authenticate_user(
        email_or_username=login_data.email_or_username,
        password=login_data.password,
        user_agent=user_agent,
        ip_address=ip_address
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"}
        )

    return LoginResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type="bearer",
        expires_in=token_data["expires_in"],
        user=token_data["user"]
    )


@router.post("/logout", response_model=AuthResponse)
async def logout(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Logout user and invalidate tokens.

    Blacklists the current access token and optionally deactivates session.
    """
    auth_service = AuthService(db)

    # Extract access token from Authorization header
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization header"
        )

    access_token = auth_header.split(" ")[1]

    success, message = await auth_service.logout_user(
        user_id=current_user.id,
        access_token=access_token,
        session_token=logout_data.session_token
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Generates a new access token pair using a valid refresh token.
    """
    from app.modules.auth.utils.jwt import refresh_access_token

    token_data = refresh_access_token(
        refresh_token=refresh_data.refresh_token,
        db=db
    )

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return TokenRefreshResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type="bearer",
        expires_in=token_data["expires_in"]
    )


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset token.

    Sends a password reset link to the user's email address.
    """
    auth_service = AuthService(db)

    success, message, masked_email = await auth_service.request_password_reset(
        email=reset_data.email
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return PasswordResetResponse(
        message=message,
        masked_email=masked_email
    )


@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password using reset token.

    Changes the user's password using a valid reset token.
    """
    auth_service = AuthService(db)

    success, message = await auth_service.reset_password(
        token=reset_data.token,
        new_password=reset_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email address.

    Confirms email verification using a verification token.
    """
    auth_service = AuthService(db)

    success, message = await auth_service.verify_email(
        token=verification_data.token
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.post("/resend-verification", response_model=AuthResponse)
async def resend_verification(
    resend_data: EmailVerificationResend,
    db: Session = Depends(get_db)
):
    """
    Resend email verification token.

    Sends a new verification email to the user.
    """
    auth_service = AuthService(db)

    success, message = await auth_service.resend_verification_email(
        email=resend_data.email
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    return AuthResponse(
        success=True,
        message=message
    )


@router.post("/check-password-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(
    password_data: PasswordStrengthCheck
):
    """
    Check password strength and get improvement suggestions.

    Validates password strength and provides feedback.
    """
    result = validate_password_strength_detailed(password_data.password)

    return PasswordStrengthResponse(
        is_valid=result["is_valid"],
        score=result["score"],
        level=result["level"],
        errors=result["errors"],
        suggestions=result["suggestions"]
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Returns the profile information of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)
