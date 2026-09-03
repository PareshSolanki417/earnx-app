from decimal import Decimal
import json
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models.wallet import Wallet, WalletTransaction
from app.models.settings import AppSetting

logger = logging.getLogger("earnx.wallet")


class WalletService:
    @staticmethod
    def get_coins_per_rupee(db: Session) -> Decimal:
        """Fetch dynamic conversion rate or fallback to settings."""
        try:
            setting = db.query(AppSetting).filter(AppSetting.key == "COINS_PER_RUPEE").first()
            if setting and setting.value:
                return Decimal(setting.value)
        except Exception:
            pass
        return settings.COINS_PER_RUPEE

    @staticmethod
    def get_or_create_wallet(db: Session, user_id: int) -> Wallet:
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                available_coins=Decimal("0.0000"),
                pending_coins=Decimal("0.0000"),
                lifetime_earned=Decimal("0.0000"),
                lifetime_withdrawn=Decimal("0.0000"),
            )
            db.add(wallet)
            db.flush()
        return wallet

    @classmethod
    def credit_coins(
        cls,
        db: Session,
        user_id: int,
        amount: Decimal,
        tx_type: str,
        source: str,
        external_event_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[WalletTransaction, bool]:
        """
        Atomically credits coins to user's wallet with ledger entry.
        Returns: (WalletTransaction, is_new: bool).
        If external_event_id is already present, returns existing transaction without re-crediting.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be strictly positive")

        # Deduplication check for idempotency
        if external_event_id:
            existing_tx = (
                db.query(WalletTransaction)
                .filter(WalletTransaction.external_event_id == external_event_id)
                .first()
            )
            if existing_tx:
                logger.warning("Duplicate credit event detected: %s", external_event_id)
                return existing_tx, False

        wallet = cls.get_or_create_wallet(db, user_id)
        balance_before = Decimal(str(wallet.available_coins))
        balance_after = balance_before + amount

        wallet.available_coins = balance_after
        wallet.lifetime_earned = Decimal(str(wallet.lifetime_earned)) + amount

        tx = WalletTransaction(
            user_id=user_id,
            type=tx_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            external_event_id=external_event_id,
            status="COMPLETED",
            metadata_json=json.dumps(metadata) if metadata else None,
            ip_address=ip_address,
        )
        db.add(tx)

        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            # Double check if another worker just inserted this event
            if external_event_id:
                existing_tx = (
                    db.query(WalletTransaction)
                    .filter(WalletTransaction.external_event_id == external_event_id)
                    .first()
                )
                if existing_tx:
                    return existing_tx, False
            raise

        return tx, True

    @classmethod
    def debit_coins(
        cls,
        db: Session,
        user_id: int,
        amount: Decimal,
        tx_type: str,
        source: str,
        external_event_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> WalletTransaction:
        """
        Atomically debits coins from user's wallet with ledger entry.
        Raises ValueError if insufficient available balance.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be strictly positive")

        wallet = cls.get_or_create_wallet(db, user_id)
        balance_before = Decimal(str(wallet.available_coins))

        if balance_before < amount:
            raise ValueError(f"Insufficient balance. Available: {balance_before}, Required: {amount}")

        balance_after = balance_before - amount
        wallet.available_coins = balance_after

        # If withdrawal, track in lifetime_withdrawn
        if tx_type == "WITHDRAWAL":
            wallet.lifetime_withdrawn = Decimal(str(wallet.lifetime_withdrawn)) + amount

        tx = WalletTransaction(
            user_id=user_id,
            type=tx_type,
            amount=-amount,  # Negative for debit
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            external_event_id=external_event_id,
            status="COMPLETED",
            metadata_json=json.dumps(metadata) if metadata else None,
            ip_address=ip_address,
        )
        db.add(tx)
        db.flush()
        return tx

    @classmethod
    def refund_coins(
        cls,
        db: Session,
        user_id: int,
        amount: Decimal,
        source: str,
        reason: str,
    ) -> WalletTransaction:
        """Refunds debited coins back to the user upon withdrawal cancellation/rejection."""
        wallet = cls.get_or_create_wallet(db, user_id)
        balance_before = Decimal(str(wallet.available_coins))
        balance_after = balance_before + Decimal(str(amount))

        wallet.available_coins = balance_after
        # Revert lifetime_withdrawn if previously debited as withdrawal
        wallet.lifetime_withdrawn = max(
            Decimal("0.0000"), Decimal(str(wallet.lifetime_withdrawn)) - Decimal(str(amount))
        )

        tx = WalletTransaction(
            user_id=user_id,
            type="ADJUSTMENT",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            source=source,
            status="COMPLETED",
            metadata_json=json.dumps({"action": "REFUND", "reason": reason}),
        )
        db.add(tx)
        db.flush()
        return tx


wallet_service = WalletService()
