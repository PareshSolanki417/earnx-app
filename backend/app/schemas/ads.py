from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class AdStartRequest(BaseModel):
    ad_type: str = "rewarded"


class AdStartResponse(BaseModel):
    event_id: str
    zone_id: str
    cooldown_seconds: int
    is_mock: bool
    mock_postback_url: Optional[str] = None
    message: str


class MonetagPostbackPayload(BaseModel):
    sub_id: str  # User ID or session token passed when ad started
    event_id: str  # Unique ad impression / completion event ID from Monetag
    zone_id: Optional[str] = None
    payout: Optional[Decimal] = Decimal("0.0")
    token: Optional[str] = None  # Signature / security token


class PostbackResultResponse(BaseModel):
    success: bool
    message: str
    event_id: str
    coins_credited: Decimal
    is_duplicate: bool = False
