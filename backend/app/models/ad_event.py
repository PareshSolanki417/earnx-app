from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from app.database import Base


class AdEvent(Base):
    __tablename__ = "ad_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider = Column(String(50), default="MONETAG", nullable=False)
    zone_id = Column(String(50), nullable=True, index=True)
    external_event_id = Column(String(100), unique=True, index=True, nullable=False)
    reward_coins = Column(Numeric(18, 4), default=0.0000, nullable=False)
    payout_amount = Column(Numeric(10, 4), nullable=True)
    signature = Column(String(255), nullable=True)
    status = Column(String(20), default="VERIFIED", nullable=False)  # INITIATED, VERIFIED, REJECTED, DUPLICATE
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    raw_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

    user = relationship("User", back_populates="ad_events")
