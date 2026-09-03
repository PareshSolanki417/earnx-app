from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ReferredUserItem(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    joined_at: datetime
    status: str
    is_qualified: bool = False

    model_config = ConfigDict(from_attributes=True)


class ReferralStatsResponse(BaseModel):
    referral_code: str
    referral_link: str
    total_referred: int
    qualified_referred: int
    coins_earned: Decimal
    bonus_per_referral: Decimal
    qualifying_actions_needed: int
    recent_referrals: List[ReferredUserItem]
