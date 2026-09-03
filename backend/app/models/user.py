from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    username = Column(String(100), index=True, nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    photo_url = Column(String(500), nullable=True)
    referral_code = Column(String(20), unique=True, index=True, nullable=False)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, SUSPENDED, BANNED
    risk_level = Column(String(20), default="LOW", nullable=False)  # LOW, MEDIUM, HIGH, BLOCKED
    consecutive_bonus_days = Column(Integer, default=0, nullable=False)
    last_bonus_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    transactions = relationship("WalletTransaction", back_populates="user", cascade="all, delete-orphan")
    task_completions = relationship("TaskCompletion", back_populates="user", cascade="all, delete-orphan")
    withdrawals = relationship("Withdrawal", back_populates="user", cascade="all, delete-orphan")
    ad_events = relationship("AdEvent", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    referred_by = relationship("User", remote_side=[id], backref="referrals")
