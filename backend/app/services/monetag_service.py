from decimal import Decimal
import hmac
import hashlib
import json
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ad_event import AdEvent
from app.models.user import User
from app.models.settings import AppSetting
from app.models.notification import Notification
from app.services.wallet_service import wallet_service

logger = logging.getLogger("earnx.monetag")


class MonetagService:
    """
    Monetag Ad Network Integration Layer.
    Isolated adapter handling rewarded ad initialization, signature verification,
    idempotent postbacks, and referral qualifying milestones.
    """

    @staticmethod
    def get_ad_reward_coins(db: Session) -> Decimal:
        """Fetch configured coins per rewarded ad view."""
        try:
            setting = db.query(AppSetting).filter(AppSetting.key == "AD_REWARD_COINS").first()
            if setting and setting.value:
                return Decimal(setting.value)
        except Exception:
            pass
        return Decimal("15.0000")

    @classmethod
    def verify_postback_signature(
        cls, sub_id: str, event_id: str, token: Optional[str]
    ) -> bool:
        """
        Validates postback security signature if secret key is configured.
        In development mode or when token is not mandated, bypasses check.
        """
        secret = settings.MONETAG_POSTBACK_SECRET
        if not secret or secret == "mock_secret_key" or not settings.is_production:
            return True

        if not token:
            return False

        # Compute HMAC SHA256 of "event_id:sub_id" using MONETAG_POSTBACK_SECRET
        message = f"{event_id}:{sub_id}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, token)

    @classmethod
    def process_postback(
        cls,
        db: Session,
        sub_id: str,
        event_id: str,
        zone_id: Optional[str] = None,
        payout: Optional[Decimal] = None,
        token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        raw_payload: Optional[str] = None,
    ) -> Tuple[bool, str, Decimal, bool]:
        """
        Processes an incoming Monetag postback.
        Returns: (success: bool, message: str, coins_credited: Decimal, is_duplicate: bool)
        """
        if not sub_id or not event_id:
            return False, "Missing sub_id or event_id in postback payload", Decimal("0.0"), False

        event_id_clean = str(event_id).strip()
        sub_id_clean = str(sub_id).strip()

        # 1. Signature check
        if not cls.verify_postback_signature(sub_id_clean, event_id_clean, token):
            logger.warning("Invalid postback signature received for event %s", event_id_clean)
            return False, "Invalid postback signature", Decimal("0.0"), False

        # 2. Duplicate check in AdEvents
        existing_event = (
            db.query(AdEvent).filter(AdEvent.external_event_id == event_id_clean).first()
        )
        if existing_event:
            logger.info("Monetag postback already processed for event %s. Idempotent return.", event_id_clean)
            return True, "Event already processed (idempotent)", Decimal("0.0"), True

        # 3. Locate User (sub_id can be User.id or Telegram ID)
        user = None
        if sub_id_clean.isdigit():
            user = db.query(User).filter(User.id == int(sub_id_clean)).first()
            if not user:
                user = db.query(User).filter(User.telegram_id == int(sub_id_clean)).first()

        if not user:
            logger.error("User not found for postback sub_id: %s", sub_id_clean)
            return False, f"User '{sub_id_clean}' not found", Decimal("0.0"), False

        if user.status in ("SUSPENDED", "BANNED"):
            logger.warning("Postback rejected for suspended user ID: %s", user.id)
            return False, "User account is suspended", Decimal("0.0"), False

        # 4. Calculate Reward
        reward_coins = cls.get_ad_reward_coins(db)

        # 5. Ledger Transaction (external_event_id ensures strict DB-level uniqueness)
        external_tx_id = f"monetag_{event_id_clean}"
        tx, is_new = wallet_service.credit_coins(
            db=db,
            user_id=user.id,
            amount=reward_coins,
            tx_type="AD_REWARD",
            source="MONETAG",
            external_event_id=external_tx_id,
            metadata={"zone_id": zone_id, "payout": str(payout) if payout else "0"},
            ip_address=ip_address,
        )

        if not is_new:
            # Transaction already existed
            return True, "Event already processed (idempotent)", Decimal("0.0"), True

        # 6. Record AdEvent
        ad_event = AdEvent(
            user_id=user.id,
            provider="MONETAG",
            zone_id=zone_id or settings.MONETAG_ZONE_ID,
            external_event_id=event_id_clean,
            reward_coins=reward_coins,
            payout_amount=payout,
            signature=token,
            status="VERIFIED",
            ip_address=ip_address,
            user_agent=user_agent,
            raw_payload=raw_payload,
        )
        db.add(ad_event)

        # 7. Create in-app notification
        notif = Notification(
            user_id=user.id,
            title="Ad Reward Credited! 🎉",
            message=f"You earned +{reward_coins:.0f} Coins for watching an eligible sponsored video.",
            type="REWARD",
        )
        db.add(notif)

        # 8. Check referral qualification: If referred by another user, check if qualifying actions reached
        cls._check_referral_milestone(db, user)

        db.commit()
        return True, "Ad reward verified and credited successfully", reward_coins, False

    @classmethod
    def _check_referral_milestone(cls, db: Session, user: User):
        """If user was referred and hits qualifying action milestone, reward the referrer."""
        if not user.referred_by_id:
            return

        # Check total verified ad events for this user
        ad_count = db.query(AdEvent).filter(AdEvent.user_id == user.id, AdEvent.status == "VERIFIED").count()
        qualifying_needed = settings.REFERRAL_QUALIFYING_ACTIONS

        if ad_count == qualifying_needed:
            # Reward the referrer
            referrer = db.query(User).filter(User.id == user.referred_by_id).first()
            if referrer and referrer.status == "ACTIVE":
                bonus_coins = settings.REFERRAL_BONUS_COINS
                ref_event_id = f"ref_qualify_{referrer.id}_{user.id}"
                wallet_service.credit_coins(
                    db=db,
                    user_id=referrer.id,
                    amount=bonus_coins,
                    tx_type="REFERRAL_REWARD",
                    source="REFERRAL_QUALIFIED",
                    external_event_id=ref_event_id,
                    metadata={"referred_user_id": user.id, "username": user.username},
                )
                db.add(
                    Notification(
                        user_id=referrer.id,
                        title="Referral Milestone Reached! 👥",
                        message=f"Your referred friend @{user.username or user.first_name} completed qualifying activities. You earned +{bonus_coins:.0f} Coins!",
                        type="REWARD",
                    )
                )


monetag_service = MonetagService()
