from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    available_coins = Column(Numeric(18, 4), default=0.0000, nullable=False)
    pending_coins = Column(Numeric(18, 4), default=0.0000, nullable=False)
    lifetime_earned = Column(Numeric(18, 4), default=0.0000, nullable=False)
    lifetime_withdrawn = Column(Numeric(18, 4), default=0.0000, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="wallet")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    type = Column(String(30), nullable=False, index=True)  # AD_REWARD, DAILY_BONUS, TASK_REWARD, REFERRAL_REWARD, WITHDRAWAL, ADJUSTMENT
    amount = Column(Numeric(18, 4), nullable=False)  # Positive for credit, negative for debit
    balance_before = Column(Numeric(18, 4), nullable=False)
    balance_after = Column(Numeric(18, 4), nullable=False)
    source = Column(String(50), nullable=False)  # e.g., MONETAG, DAILY_BONUS, TASK_1, UPI_WITHDRAWAL
    external_event_id = Column(String(100), unique=True, nullable=True, index=True)  # Strictly unique for idempotency
    status = Column(String(20), default="COMPLETED", nullable=False)  # COMPLETED, PENDING, REVERSED
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="transactions")
