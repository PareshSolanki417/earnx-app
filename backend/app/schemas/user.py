from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserProfileResponse(BaseModel):
    id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    referral_code: str
    status: str
    risk_level: str
    consecutive_bonus_days: int
    available_coins: Decimal
    rupee_value: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    total_referrals: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
