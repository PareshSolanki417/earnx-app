from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WithdrawalCreateRequest(BaseModel):
    amount_rupees: Decimal = Field(..., gt=0, description="Amount to withdraw (min 0.0050)")
    payout_method: str = Field(..., description="TON, WLD, BINANCE, or PAYPAL")
    payout_account: str = Field(..., min_length=3, max_length=150, description="Wallet address / Pay ID / Email")
    account_holder_name: Optional[str] = Field(None, max_length=100)


class WithdrawalResponse(BaseModel):
    id: str
    user_id: int
    amount_rupees: Decimal
    coins_deducted: Decimal
    payout_method: str
    payout_account: str
    account_holder_name: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WithdrawalListResponse(BaseModel):
    total: int
    min_withdrawal_rupees: Decimal
    available_rupees: Decimal
    items: List[WithdrawalResponse]
