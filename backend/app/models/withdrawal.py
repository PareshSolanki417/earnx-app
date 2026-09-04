from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    amount_rupees = Column(Numeric(18, 4), nullable=False)
    coins_deducted = Column(Numeric(18, 4), nullable=False)
    payout_method = Column(String(30), nullable=False)  # TON, WLD, BINANCE, PAYPAL
    payout_account = Column(String(255), nullable=False)  # Wallet address, Pay ID, or PayPal Email
    account_holder_name = Column(String(100), nullable=True)
    status = Column(String(20), default="PENDING", index=True, nullable=False)  # PENDING, PROCESSING, APPROVED, PAID, REJECTED, CANCELLED
    admin_notes = Column(Text, nullable=True)
    processed_by_admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="withdrawals")
    processed_by = relationship("AdminUser", foreign_keys=[processed_by_admin_id])
