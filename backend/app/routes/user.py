from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserProfileResponse
from app.security.deps import get_current_user
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/user", tags=["User Profile"])


@router.get("/me", response_model=UserProfileResponse)
def get_user_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns the authenticated user profile and live balance statistics."""
    wallet = wallet_service.get_or_create_wallet(db, user.id)
    coins_per_rupee = wallet_service.get_coins_per_rupee(db)
    available_coins = Decimal(str(wallet.available_coins))
    rupee_val = (available_coins / coins_per_rupee).quantize(Decimal("0.01")) if coins_per_rupee > 0 else Decimal("0.00")

    referral_count = db.query(User).filter(User.referred_by_id == user.id).count()

    return UserProfileResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        photo_url=user.photo_url,
        referral_code=user.referral_code,
        status=user.status,
        risk_level=user.risk_level,
        consecutive_bonus_days=user.consecutive_bonus_days,
        available_coins=available_coins,
        rupee_value=rupee_val,
        lifetime_earned=Decimal(str(wallet.lifetime_earned)),
        lifetime_withdrawn=Decimal(str(wallet.lifetime_withdrawn)),
        total_referrals=referral_count,
        created_at=user.created_at,
    )
