from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.withdrawal import Withdrawal
from app.models.settings import AppSetting
from app.models.notification import Notification
from app.schemas.withdrawal import (
    WithdrawalCreateRequest,
    WithdrawalResponse,
    WithdrawalListResponse,
)
from app.security.deps import get_current_user, get_client_ip
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])


def get_min_withdrawal_rupees(db: Session) -> Decimal:
    try:
        setting = db.query(AppSetting).filter(AppSetting.key == "MIN_WITHDRAWAL_RUPEES").first()
        if setting and setting.value:
            return Decimal(setting.value)
    except Exception:
        pass
    return settings.MIN_WITHDRAWAL_RUPEES


@router.get("", response_model=WithdrawalListResponse)
def get_user_withdrawals(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Returns the user's withdrawal history and current withdrawal thresholds."""
    items = (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == user.id)
        .order_by(Withdrawal.created_at.desc())
        .all()
    )

    wallet = wallet_service.get_or_create_wallet(db, user.id)
    coins_per_rupee = wallet_service.get_coins_per_rupee(db)
    available_rupees = (
        Decimal(str(wallet.available_coins)) / coins_per_rupee
    ).quantize(Decimal("0.01")) if coins_per_rupee > 0 else Decimal("0.00")

    return WithdrawalListResponse(
        total=len(items),
        min_withdrawal_rupees=get_min_withdrawal_rupees(db),
        available_rupees=available_rupees,
        items=[WithdrawalResponse.model_validate(w) for w in items],
    )


@router.post("", response_model=WithdrawalResponse)
def create_withdrawal(
    payload: WithdrawalCreateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a withdrawal request.
    Validates minimum amount (0.0050), checks user balance, atomically debits coins from ledger,
    and enqueues the request for admin verification.
    """
    client_ip = get_client_ip(request)
    min_rupees = get_min_withdrawal_rupees(db)
    req_rupees = Decimal(str(payload.amount_rupees))

    valid_methods = {"TON", "WLD", "BINANCE", "PAYPAL"}
    chosen_method = payload.payout_method.strip().upper()
    if chosen_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payout method '{payload.payout_method}'. Supported options: TON, WLD, BINANCE, PAYPAL",
        )

    if req_rupees < min_rupees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum withdrawal amount is {min_rupees:.4f}",
        )

    # Check pending withdrawal limit (e.g. max 2 pending at a time to prevent flood)
    pending_count = (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == user.id, Withdrawal.status == "PENDING")
        .count()
    )
    if pending_count >= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have pending withdrawal requests under review. Please wait for them to be processed.",
        )

    # Calculate coins to deduct
    coins_per_rupee = wallet_service.get_coins_per_rupee(db)
    coins_needed = req_rupees * coins_per_rupee

    # Atomically debit coins from ledger
    try:
        tx = wallet_service.debit_coins(
            db=db,
            user_id=user.id,
            amount=coins_needed,
            tx_type="WITHDRAWAL",
            source=f"{chosen_method}_REQUEST",
            metadata={
                "amount": str(req_rupees),
                "payout_method": chosen_method,
                "payout_account": payload.payout_account,
            },
            ip_address=client_ip,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Create withdrawal record
    withdrawal = Withdrawal(
        user_id=user.id,
        amount_rupees=req_rupees,
        coins_deducted=coins_needed,
        payout_method=chosen_method,
        payout_account=payload.payout_account.strip(),
        account_holder_name=payload.account_holder_name,
        status="PENDING",
    )
    db.add(withdrawal)

    # In-app notification
    db.add(
        Notification(
            user_id=user.id,
            title="Withdrawal Requested ⏳",
            message=f"Your withdrawal request of {req_rupees} ({coins_needed:.2f} coins) via {chosen_method} is submitted and under review.",
            type="WITHDRAWAL",
        )
    )

    db.commit()
    db.refresh(withdrawal)

    return WithdrawalResponse.model_validate(withdrawal)
