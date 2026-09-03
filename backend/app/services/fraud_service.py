from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models.fraud import FraudEvent
from app.models.user import User
from app.models.ad_event import AdEvent

logger = logging.getLogger("earnx.fraud")


class FraudService:
    @staticmethod
    def record_fraud_event(
        db: Session,
        event_type: str,
        severity: str,
        details: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> FraudEvent:
        event = FraudEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            details=details,
            ip_address=ip_address,
        )
        db.add(event)

        # Elevate risk if critical or high severity
        if user_id and severity in ("HIGH", "CRITICAL"):
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if severity == "CRITICAL":
                    user.risk_level = "BLOCKED"
                    user.status = "SUSPENDED"
                elif user.risk_level == "LOW":
                    user.risk_level = "MEDIUM"
                elif user.risk_level == "MEDIUM":
                    user.risk_level = "HIGH"

        db.flush()
        return event

    @classmethod
    def check_ad_cooldown(cls, db: Session, user_id: int, ip_address: Optional[str] = None) -> bool:
        """
        Ensures user does not exceed ad frequency limits.
        Returns True if eligible, False if cooldown active.
        """
        threshold_time = datetime.now(timezone.utc) - timedelta(seconds=settings.MIN_SECONDS_BETWEEN_ADS)
        last_ad = (
            db.query(AdEvent)
            .filter(AdEvent.user_id == user_id, AdEvent.created_at >= threshold_time)
            .first()
        )
        if last_ad:
            cls.record_fraud_event(
                db=db,
                event_type="RAPID_AD_REQUEST",
                severity="LOW",
                details=f"User requested ad view within {settings.MIN_SECONDS_BETWEEN_ADS}s cooldown",
                user_id=user_id,
                ip_address=ip_address,
            )
            return False
        return True

    @classmethod
    def check_self_referral(cls, db: Session, user_telegram_id: int, referral_code: str) -> bool:
        """Validates that a user is not attempting to refer themselves."""
        referrer = db.query(User).filter(User.referral_code == referral_code).first()
        if referrer and referrer.telegram_id == user_telegram_id:
            cls.record_fraud_event(
                db=db,
                event_type="SELF_REFERRAL_ATTEMPT",
                severity="MEDIUM",
                details=f"User {user_telegram_id} attempted self-referral using code {referral_code}",
                user_id=referrer.id,
            )
            return True
        return False


fraud_service = FraudService()
