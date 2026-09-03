from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.wallet import WalletTransaction
from app.models.ad_event import AdEvent
from app.schemas.referral import ReferralStatsResponse, ReferredUserItem
from app.security.deps import get_current_user

router = APIRouter(prefix="/referral", tags=["Referral System"])


@router.get("", response_model=ReferralStatsResponse)
def get_referral_stats(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Returns the user's referral code, bot share URL, and referred friends list."""
    bot_username = settings.BOT_USERNAME.lstrip("@")
    referral_link = f"https://t.me/{bot_username}?start={user.referral_code}"

    # Query referred users
    referred_users = (
        db.query(User)
        .filter(User.referred_by_id == user.id)
        .order_by(User.created_at.desc())
        .limit(50)
        .all()
    )

    total_referred = len(referred_users)
    qualifying_needed = settings.REFERRAL_QUALIFYING_ACTIONS

    user_items = []
    qualified_count = 0
    for ref_u in referred_users:
        ad_count = (
            db.query(AdEvent)
            .filter(AdEvent.user_id == ref_u.id, AdEvent.status == "VERIFIED")
            .count()
        )
        is_qual = ad_count >= qualifying_needed
        if is_qual:
            qualified_count += 1

        user_items.append(
            ReferredUserItem(
                id=ref_u.id,
                username=ref_u.username,
                first_name=ref_u.first_name,
                joined_at=ref_u.created_at,
                status=ref_u.status,
                is_qualified=is_qual,
            )
        )

    # Sum referral rewards earned from transactions ledger
    ref_transactions = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.user_id == user.id,
            WalletTransaction.type == "REFERRAL_REWARD",
        )
        .all()
    )
    total_earned = sum((Decimal(str(tx.amount)) for tx in ref_transactions), Decimal("0.0"))

    return ReferralStatsResponse(
        referral_code=user.referral_code,
        referral_link=referral_link,
        total_referred=total_referred,
        qualified_referred=qualified_count,
        coins_earned=total_earned,
        bonus_per_referral=settings.REFERRAL_BONUS_COINS,
        qualifying_actions_needed=qualifying_needed,
        recent_referrals=user_items,
    )
