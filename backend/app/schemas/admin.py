from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AdminDashboardMetrics(BaseModel):
    total_users: int
    active_users: int
    todays_users: int
    total_coins_issued: Decimal
    total_withdrawals_count: int
    pending_withdrawals_count: int
    paid_withdrawals_count: int
    pending_withdrawals_amount: Decimal
    paid_withdrawals_amount: Decimal
    todays_ad_events: int
    estimated_gross_revenue: Decimal
    estimated_user_rewards: Decimal
    estimated_platform_margin: Decimal
    demo_mode: bool


class AdminUserItem(BaseModel):
    id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    referral_code: str
    status: str
    risk_level: str
    available_coins: Decimal
    lifetime_earned: Decimal
    created_at: datetime
    last_login_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetail(AdminUserItem):
    pending_coins: Decimal
    lifetime_withdrawn: Decimal
    total_referrals: int
    total_ads_watched: int
    total_tasks_completed: int


class AdminBalanceAdjustRequest(BaseModel):
    amount_coins: Decimal = Field(..., description="Positive to credit, negative to debit")
    reason: str = Field(..., min_length=3, max_length=255, description="Audited reason for manual adjustment")


class AdminUserStatusUpdate(BaseModel):
    status: Optional[str] = None  # ACTIVE, SUSPENDED, BANNED
    risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH, BLOCKED
    reason: str = Field(..., min_length=3)


class AdminWithdrawalActionRequest(BaseModel):
    status: str = Field(..., description="APPROVED, PAID, REJECTED, CANCELLED")
    admin_notes: Optional[str] = None


class AdminTaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=150)
    description: str
    icon: str = "task"
    reward_coins: Decimal = Field(..., gt=0)
    action_url: Optional[str] = None
    verification_method: str = "MANUAL_OR_URL"
    verification_data: Optional[str] = None
    status: str = "ACTIVE"
    max_completions: int = 1


class AdminSettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


class AdminSettingUpdate(BaseModel):
    value: str


class AdminActionLogItem(BaseModel):
    id: int
    admin_username: str
    target_user_id: Optional[int] = None
    action_type: str
    details: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FraudEventItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    event_type: str
    severity: str
    details: str
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
