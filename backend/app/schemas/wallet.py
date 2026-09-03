from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class WalletResponse(BaseModel):
    user_id: int
    available_coins: Decimal
    rupee_value: Decimal
    pending_coins: Decimal
    lifetime_earned: Decimal
    lifetime_withdrawn: Decimal
    coins_per_rupee: Decimal

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: str
    user_id: int
    type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    source: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    total: int
    items: List[TransactionResponse]
