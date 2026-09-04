import hashlib
import logging
from decimal import Decimal
from typing import Dict
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.services.wallet_service import wallet_service
from app.security.deps import get_current_user, get_client_ip

logger = logging.getLogger("earnx.paymentwall")

router = APIRouter(prefix="/paymentwall", tags=["Paymentwall Offerwall"])

PAYMENTWALL_PROJECT_KEY = "ce252a6d92b644859afba630d4bc3361"
PAYMENTWALL_SECRET_KEY = "0de80970eecf98d2eb4e4526897813be"


def calculate_paymentwall_signature(params: Dict[str, str], secret: str) -> str:
    """Calculates Paymentwall MD5 signature version 2/3."""
    sorted_keys = sorted([k for k in params.keys() if k != "sig"])
    base_str = "".join(f"{k}={params[k]}" for k in sorted_keys) + secret
    return hashlib.md5(base_str.encode("utf-8")).hexdigest()


@router.get("/widget-url")
def get_offerwall_url(user: User = Depends(get_current_user)):
    """Returns the authenticated Paymentwall Offerwall widget URL for the user."""
    uid = str(user.telegram_id or user.id)
    url = f"https://api.paymentwall.com/api/ps/?key={PAYMENTWALL_PROJECT_KEY}&uid={uid}&widget=p1_1&email={user.username or 'user'}@earnx.app"
    return {
        "url": url,
        "uid": uid,
        "project_key": PAYMENTWALL_PROJECT_KEY,
    }


@router.get("/pingback")
@router.post("/pingback")
async def paymentwall_pingback(request: Request, db: Session = Depends(get_db)):
    """
    Paymentwall Server-to-Server Pingback.
    Triggered when a user completes a survey, game task, or app install.
    Returns plain text 'OK' on success as required by Paymentwall protocol.
    """
    client_ip = get_client_ip(request)
    if request.method == "POST":
        form_data = await request.form()
        params = dict(form_data)
    else:
        params = dict(request.query_params)

    logger.info("Paymentwall pingback received: %s from %s", params, client_ip)

    uid = params.get("uid")
    currency = params.get("currency")
    tx_type = str(params.get("type", "0"))
    ref = params.get("ref")
    sig = params.get("sig")

    if not uid or not currency or not ref:
        return Response(content="Missing required parameters", status_code=400)

    # Validate Paymentwall signature
    if sig:
        expected_sig = calculate_paymentwall_signature(params, PAYMENTWALL_SECRET_KEY)
        if sig != expected_sig:
            logger.warning("Paymentwall signature mismatch: expected %s, got %s", expected_sig, sig)

    # Locate user
    user = None
    if uid.isdigit():
        user = db.query(User).filter(User.telegram_id == int(uid)).first()
        if not user:
            user = db.query(User).filter(User.id == int(uid)).first()

    if not user:
        logger.warning("Paymentwall pingback user not found for uid: %s", uid)
        return Response(content="User not found", status_code=404)

    # Idempotency check via external_event_id
    external_tx_id = f"pw_{ref}"

    try:
        coins_to_credit = Decimal(str(currency))
    except Exception:
        coins_to_credit = Decimal("0.0")

    if coins_to_credit <= 0:
        return Response(content="OK", media_type="text/plain")

    # Regular reward credit (type 0 or 2 for test)
    if tx_type in ("0", "2"):
        tx, is_new = wallet_service.credit_coins(
            db=db,
            user_id=user.id,
            amount=coins_to_credit,
            tx_type="TASK_REWARD",
            source="PAYMENTWALL_OFFERWALL",
            external_event_id=external_tx_id,
            metadata={"ref": ref, "type": tx_type, "params": params},
            ip_address=client_ip,
        )

        if is_new:
            # Send in-app notification
            notif = Notification(
                user_id=user.id,
                title="Offerwall Reward Credited!",
                message=f"You earned +{coins_to_credit} coins from completing an offerwall task.",
                type="REWARD",
            )
            db.add(notif)
            db.commit()
            logger.info("Successfully credited %s coins to user %s via Paymentwall ref %s", coins_to_credit, user.id, ref)

    elif tx_type == "1":
        # Chargeback / reversal
        try:
            wallet_service.debit_coins(
                db=db,
                user_id=user.id,
                amount=coins_to_credit,
                tx_type="ADJUSTMENT",
                source="PAYMENTWALL_CHARGEBACK",
                metadata={"ref": ref},
                ip_address=client_ip,
            )
            logger.warning("Reversed %s coins for user %s due to Paymentwall chargeback ref %s", coins_to_credit, user.id, ref)
        except Exception as e:
            logger.error("Error processing Paymentwall chargeback: %s", e)

    return Response(content="OK", media_type="text/plain")
