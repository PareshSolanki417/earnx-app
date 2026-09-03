from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(50), default="task", nullable=False)
    reward_coins = Column(Numeric(18, 4), default=10.0000, nullable=False)
    action_url = Column(String(500), nullable=True)
    verification_method = Column(String(50), default="MANUAL_OR_URL", nullable=False)  # URL_VISIT, TELEGRAM_CHANNEL, REWARD_MILESTONE, CODE
    verification_data = Column(String(255), nullable=True)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE, EXPIRED
    max_completions = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    completions = relationship("TaskCompletion", back_populates="task", cascade="all, delete-orphan")


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)  # PENDING, COMPLETED, REJECTED
    reward_coins = Column(Numeric(18, 4), nullable=False)
    transaction_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_user_completion"),
    )

    task = relationship("Task", back_populates="completions")
    user = relationship("User", back_populates="task_completions")
