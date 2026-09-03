import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.ads import (
    AdStartRequest,
    AdStartResponse,
    MonetagPostbackPayload,
    PostbackResultResponse,
)
from app.security.deps import get_current_user, get_client_ip
from app.services.monetag_service import monetag_service
from app.services.fraud_service import fraud_service

router = APIRouter(tags=["Ads & Monetag"])


@router.post("/ads/start", response_model=AdStartResponse)
def start_ad(
    payload: AdStartRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initializes a rewarded ad session.
    Enforces cooldown and anti-fraud limits, generating a unique event ID for tracking.
    """
    client_ip = get_client_ip(request)

    # Check cooldown
    if not fraud_service.check_ad_cooldown(db, user.id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {settings.MIN_SECONDS_BETWEEN_ADS} seconds between watching ads.",
        )

    event_id = f"evt_{user.id}_{int(uuid.uuid4().hex[:12], 16)}"
    is_mock = not settings.is_production

    mock_url = None
    if is_mock:
        mock_url = f"/api/monetag/postback?sub_id={user.id}&event_id={event_id}&zone_id={settings.MONETAG_ZONE_ID}"

    return AdStartResponse(
        event_id=event_id,
        zone_id=settings.MONETAG_ZONE_ID,
        cooldown_seconds=settings.MIN_SECONDS_BETWEEN_ADS,
        is_mock=is_mock,
        mock_postback_url=mock_url,
        message="Rewarded ad session started. Awaiting verified network postback.",
    )


@router.get("/ads/status")
def check_ad_status(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Checks whether the user is currently eligible to watch an ad or is on cooldown."""
    client_ip = get_client_ip(request)
    can_watch = fraud_service.check_ad_cooldown(db, user.id, client_ip)
    reward_coins = monetag_service.get_ad_reward_coins(db)

    return {
        "can_watch": can_watch,
        "cooldown_seconds": settings.MIN_SECONDS_BETWEEN_ADS if not can_watch else 0,
        "reward_coins": reward_coins,
    }


@router.post("/monetag/postback", response_model=PostbackResultResponse)
async def monetag_postback_post(
    request: Request,
    payload: Optional[MonetagPostbackPayload] = None,
    sub_id: Optional[str] = Query(None),
    event_id: Optional[str] = Query(None),
    zone_id: Optional[str] = Query(None),
    payout: Optional[Decimal] = Query(None),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Monetag Postback Endpoint (POST).
    Verifies ad event, rejects duplicate event IDs, credits coins to ledger, and updates user wallet.
    """
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    # Read from JSON body or Query Params
    target_sub_id = payload.sub_id if payload else sub_id
    target_event_id = payload.event_id if payload else event_id
    target_zone_id = (payload.zone_id if payload else zone_id) or settings.MONETAG_ZONE_ID
    target_payout = (payload.payout if payload else payout) or Decimal("0.0")
    target_token = payload.token if payload else token

    try:
        raw_body = await request.body()
        raw_payload_str = raw_body.decode("utf-8") if raw_body else None
    except Exception:
        raw_payload_str = None

    if not target_sub_id or not target_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: sub_id and event_id",
        )

    success, msg, credited_coins, is_dup = monetag_service.process_postback(
        db=db,
        sub_id=str(target_sub_id),
        event_id=str(target_event_id),
        zone_id=target_zone_id,
        payout=target_payout,
        token=target_token,
        ip_address=client_ip,
        user_agent=user_agent,
        raw_payload=raw_payload_str,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return PostbackResultResponse(
        success=True,
        message=msg,
        event_id=str(target_event_id),
        coins_credited=credited_coins,
        is_duplicate=is_dup,
    )


@router.get("/monetag/postback", response_model=PostbackResultResponse)
def monetag_postback_get(
    request: Request,
    sub_id: str = Query(..., description="User ID or tracking sub ID"),
    event_id: str = Query(..., description="Unique ad view event ID"),
    zone_id: Optional[str] = Query(None),
    payout: Optional[Decimal] = Query(None),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Monetag Postback Endpoint (GET) for network integrations requesting via HTTP GET."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    success, msg, credited_coins, is_dup = monetag_service.process_postback(
        db=db,
        sub_id=sub_id,
        event_id=event_id,
        zone_id=zone_id or settings.MONETAG_ZONE_ID,
        payout=payout or Decimal("0.0"),
        token=token,
        ip_address=client_ip,
        user_agent=user_agent,
        raw_payload=str(request.query_params),
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return PostbackResultResponse(
        success=True,
        message=msg,
        event_id=event_id,
        coins_credited=credited_coins,
        is_duplicate=is_dup,
    )
