import logging
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.ad_event import AdEvent
from app.models.settings import AppSetting
from app.services.wallet_service import wallet_service
from app.security.deps import get_client_ip

logger = logging.getLogger("earnx.adsgram")

router = APIRouter(prefix="/adsgram", tags=["Adsgram"])


def get_ad_reward_coins(db: Session) -> Decimal:
    """Fetch configured coins per rewarded ad from AppSetting."""
    try:
        setting = db.query(AppSetting).filter(AppSetting.key == "AD_REWARD_COINS").first()
        if setting and setting.value:
            return Decimal(setting.value)
    except Exception:
        pass
    return Decimal("10.0000")


@router.get("/reward")
def adsgram_reward_webhook(
    request: Request,
    userid: str = Query(..., description="Telegram ID of the user sent by Adsgram"),
    db: Session = Depends(get_db),
):
    """
    Adsgram Server-to-Server Reward Webhook.
    Adsgram replaces [userId] with the Telegram ID when the user finishes watching a rewarded video ad.
    """
    client_ip = get_client_ip(request)
    logger.info("Adsgram reward webhook received for user: %s from IP %s", userid, client_ip)

    if not userid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing userid")

    user_id_clean = userid.strip()
    user = None
    if user_id_clean.isdigit():
        user = db.query(User).filter(User.telegram_id == int(user_id_clean)).first()
        if not user:
            user = db.query(User).filter(User.id == int(user_id_clean)).first()

    if not user:
        logger.warning("Adsgram reward rejected: user %s not found", user_id_clean)
        return {"ok": False, "detail": f"User {user_id_clean} not found"}

    if user.status in ("SUSPENDED", "BANNED"):
        return {"ok": False, "detail": "User suspended"}

    reward_coins = get_ad_reward_coins(db)

    # Credit coins into wallet ledger
    import time
    tx_event_id = f"adsgram_{user.id}_{int(time.time() * 1000)}"
    
    tx, is_new = wallet_service.credit_coins(
        db=db,
        user_id=user.id,
        amount=reward_coins,
        tx_type="AD_REWARD",
        source="ADSGRAM",
        external_event_id=tx_event_id,
        metadata={"provider": "ADSGRAM", "telegram_id": user.telegram_id},
        ip_address=client_ip,
    )

    # Record AdEvent
    ad_event = AdEvent(
        user_id=user.id,
        provider="ADSGRAM",
        zone_id="adsgram_tma",
        external_event_id=tx_event_id,
        reward_coins=reward_coins,
        payout_amount=Decimal("0.005"),
        status="VERIFIED",
        ip_address=client_ip,
    )
    db.add(ad_event)
    db.commit()

    logger.info("Credited %s coins to user %s via Adsgram", reward_coins, user.id)
    return {"ok": True, "coins_credited": float(reward_coins), "user_id": user.id}
