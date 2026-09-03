import string
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.admin import AdminUser
from app.models.notification import Notification
from app.schemas.auth import (
    TelegramAuthRequest,
    TelegramAuthResponse,
    AdminLoginRequest,
    TokenResponse,
    AuthUserResponse,
)
from app.services.telegram_service import telegram_service
from app.services.wallet_service import wallet_service
from app.services.fraud_service import fraud_service
from app.security.deps import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


def generate_referral_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "EARN" + "".join(random.choices(chars, k=6))


@router.post("/telegram", response_model=TelegramAuthResponse)
def authenticate_telegram(payload: TelegramAuthRequest, db: Session = Depends(get_db)):
    """
    Validates Telegram WebApp initData HMAC-SHA256 signature server-side.
    Creates or logs in user, attaches referral if applicable, and returns JWT.
    """
    user_info = telegram_service.validate_init_data(payload.init_data)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data or expired signature",
        )

    telegram_id = user_info.get("id")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing telegram user ID in initData",
        )

    # Check existing user
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    is_new = False

    if not user:
        is_new = True
        # Check referral code
        referred_by_id = None
        if payload.referral_code:
            ref_code_clean = payload.referral_code.strip().upper()
            if not fraud_service.check_self_referral(db, telegram_id, ref_code_clean):
                referrer = db.query(User).filter(User.referral_code == ref_code_clean).first()
                if referrer and referrer.status == "ACTIVE":
                    referred_by_id = referrer.id

        # Generate unique referral code for this user
        unique_code = generate_referral_code()
        while db.query(User).filter(User.referral_code == unique_code).first():
            unique_code = generate_referral_code()

        user = User(
            telegram_id=telegram_id,
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            photo_url=user_info.get("photo_url"),
            referral_code=unique_code,
            referred_by_id=referred_by_id,
            status="ACTIVE",
            risk_level="LOW",
        )
        db.add(user)
        db.flush()

        # Initialize wallet
        wallet_service.get_or_create_wallet(db, user.id)

        # Welcome notification
        welcome_notif = Notification(
            user_id=user.id,
            title="Welcome to EarnX! 🚀",
            message="Start completing verified activities, watching sponsored videos, and claiming daily bonuses to earn coins.",
            type="INFO",
        )
        db.add(welcome_notif)
    else:
        # Update user profile information if changed
        if user_info.get("username"):
            user.username = user_info.get("username")
        if user_info.get("first_name"):
            user.first_name = user_info.get("first_name")
        if user_info.get("last_name"):
            user.last_name = user_info.get("last_name")
        if user_info.get("photo_url"):
            user.photo_url = user_info.get("photo_url")
        user.last_login_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    # Check if user account is restricted
    if user.status in ("SUSPENDED", "BANNED"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.lower()}. Please contact support.",
        )

    # Generate JWT token
    token = create_access_token({"sub": str(user.id), "role": "user", "telegram_id": user.telegram_id})

    return TelegramAuthResponse(
        token=TokenResponse(access_token=token, expires_in=86400),
        user=AuthUserResponse.model_validate(user),
        is_new_user=is_new,
    )


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    """Admin credentials login returning admin JWT token."""
    admin = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if not admin or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated",
        )

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token({"sub": str(admin.id), "role": "admin", "username": admin.username})
    return TokenResponse(access_token=token, expires_in=86400)
