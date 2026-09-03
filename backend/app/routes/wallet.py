from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.wallet import WalletTransaction
from app.schemas.wallet import WalletResponse, TransactionResponse, TransactionListResponse
from app.security.deps import get_current_user
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/wallet", tags=["Wallet & Ledger"])


@router.get("", response_model=WalletResponse)
def get_wallet(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns the user's live wallet balances and rupee conversion value."""
    wallet = wallet_service.get_or_create_wallet(db, user.id)
    coins_per_rupee = wallet_service.get_coins_per_rupee(db)
    available_coins = Decimal(str(wallet.available_coins))
    rupee_val = (available_coins / coins_per_rupee).quantize(Decimal("0.01")) if coins_per_rupee > 0 else Decimal("0.00")

    return WalletResponse(
        user_id=user.id,
        available_coins=available_coins,
        rupee_value=rupee_val,
        pending_coins=Decimal(str(wallet.pending_coins)),
        lifetime_earned=Decimal(str(wallet.lifetime_earned)),
        lifetime_withdrawn=Decimal(str(wallet.lifetime_withdrawn)),
        coins_per_rupee=coins_per_rupee,
    )


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tx_type: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns ledger transactions for the authenticated user."""
    query = db.query(WalletTransaction).filter(WalletTransaction.user_id == user.id)
    if tx_type:
        query = query.filter(WalletTransaction.type == tx_type)

    total = query.count()
    items = query.order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit).all()

    return TransactionListResponse(
        total=total,
        items=[TransactionResponse.model_validate(tx) for tx in items],
    )
