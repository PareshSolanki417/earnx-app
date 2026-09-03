from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TaskItemResponse(BaseModel):
    id: int
    title: str
    description: str
    icon: str
    reward_coins: Decimal
    action_url: Optional[str] = None
    verification_method: str
    status: str
    is_completed: bool = False

    model_config = ConfigDict(from_attributes=True)


class TaskCompleteRequest(BaseModel):
    verification_code: Optional[str] = None


class TaskCompleteResponse(BaseModel):
    success: bool
    task_id: int
    reward_coins: Decimal
    new_balance: Decimal
    message: str


class StreakDayItem(BaseModel):
    day: int
    coins: Decimal
    is_claimed: bool
    is_current: bool


class DailyBonusStatusResponse(BaseModel):
    current_streak: int
    can_claim_today: bool
    today_coins: Decimal
    days: List[StreakDayItem]
    message: str


class DailyBonusClaimResponse(BaseModel):
    success: bool
    streak_day: int
    coins_earned: Decimal
    new_balance: Decimal
    message: str
