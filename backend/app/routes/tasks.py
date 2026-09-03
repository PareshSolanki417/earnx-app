from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskCompletion
from app.models.settings import AppSetting
from app.models.notification import Notification
from app.schemas.tasks import (
    TaskItemResponse,
    TaskCompleteRequest,
    TaskCompleteResponse,
    DailyBonusStatusResponse,
    DailyBonusClaimResponse,
    StreakDayItem,
)
from app.security.deps import get_current_user
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/tasks", tags=["Tasks & Daily Bonus"])

# Default 7-day streak bonus values (configurable by Admin)
DEFAULT_STREAK_COINS = [
    Decimal("10.0"),
    Decimal("15.0"),
    Decimal("20.0"),
    Decimal("25.0"),
    Decimal("30.0"),
    Decimal("40.0"),
    Decimal("50.0"),
]


def get_streak_rewards(db: Session) -> List[Decimal]:
    rewards = []
    for day in range(1, 8):
        setting = db.query(AppSetting).filter(AppSetting.key == f"DAILY_BONUS_DAY_{day}").first()
        if setting and setting.value:
            try:
                rewards.append(Decimal(setting.value))
                continue
            except Exception:
                pass
        rewards.append(DEFAULT_STREAK_COINS[day - 1])
    return rewards


@router.get("", response_model=List[TaskItemResponse])
def get_user_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns active tasks and flags which ones the user has completed."""
    tasks = db.query(Task).filter(Task.status == "ACTIVE").all()
    user_completions = {
        tc.task_id for tc in db.query(TaskCompletion).filter(TaskCompletion.user_id == user.id).all()
    }

    result = []
    for task in tasks:
        result.append(
            TaskItemResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                icon=task.icon,
                reward_coins=Decimal(str(task.reward_coins)),
                action_url=task.action_url,
                verification_method=task.verification_method,
                status=task.status,
                is_completed=(task.id in user_completions),
            )
        )
    return result


@router.post("/{task_id}/complete", response_model=TaskCompleteResponse)
def complete_task(
    task_id: int,
    payload: TaskCompleteRequest = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits task completion and credits reward coins atomically."""
    task = db.query(Task).filter(Task.id == task_id, Task.status == "ACTIVE").first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or is no longer active",
        )

    # Check if already completed
    existing = (
        db.query(TaskCompletion)
        .filter(TaskCompletion.task_id == task_id, TaskCompletion.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already completed this task",
        )

    reward_coins = Decimal(str(task.reward_coins))
    tx_event_id = f"task_{task_id}_{user.id}"

    # Credit coins in ledger
    tx, is_new = wallet_service.credit_coins(
        db=db,
        user_id=user.id,
        amount=reward_coins,
        tx_type="TASK_REWARD",
        source=f"TASK_{task_id}",
        external_event_id=tx_event_id,
        metadata={"task_title": task.title},
    )

    # Record completion
    completion = TaskCompletion(
        task_id=task_id,
        user_id=user.id,
        status="COMPLETED",
        reward_coins=reward_coins,
        transaction_id=tx.id,
    )
    db.add(completion)

    # In-app notification
    db.add(
        Notification(
            user_id=user.id,
            title="Task Reward Credited! 📋",
            message=f"You earned +{reward_coins:.0f} Coins for completing: {task.title}",
            type="REWARD",
        )
    )

    db.commit()

    wallet = wallet_service.get_or_create_wallet(db, user.id)
    return TaskCompleteResponse(
        success=True,
        task_id=task.id,
        reward_coins=reward_coins,
        new_balance=Decimal(str(wallet.available_coins)),
        message="Task completed successfully! Reward added to your balance.",
    )


@router.get("/daily-bonus/status", response_model=DailyBonusStatusResponse)
def get_daily_bonus_status(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Returns the user's current 7-day streak status, rewards, and eligibility."""
    today = date.today()
    streak_rewards = get_streak_rewards(db)

    last_date = user.last_bonus_date
    current_streak = user.consecutive_bonus_days

    can_claim_today = True
    if last_date == today:
        can_claim_today = False
    elif last_date and last_date < (today - timedelta(days=1)):
        # Missed a day: reset streak to 0
        current_streak = 0

    # Determine today's day index (1..7)
    today_day_idx = (current_streak % 7) + 1 if can_claim_today else ((current_streak - 1) % 7) + 1
    today_coins = streak_rewards[today_day_idx - 1]

    days_list = []
    for day in range(1, 8):
        claimed = False
        is_curr = False
        if can_claim_today:
            claimed = (day < today_day_idx)
            is_curr = (day == today_day_idx)
        else:
            claimed = (day <= today_day_idx)

        days_list.append(
            StreakDayItem(
                day=day,
                coins=streak_rewards[day - 1],
                is_claimed=claimed,
                is_current=is_curr,
            )
        )

    msg = "Claim your daily bonus now!" if can_claim_today else "You have already claimed today's bonus. Come back tomorrow!"

    return DailyBonusStatusResponse(
        current_streak=current_streak,
        can_claim_today=can_claim_today,
        today_coins=today_coins,
        days=days_list,
        message=msg,
    )


@router.post("/daily-bonus/claim", response_model=DailyBonusClaimResponse)
def claim_daily_bonus(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Claims the daily bonus with streak advancement and duplicate-claim protection."""
    today = date.today()
    if user.last_bonus_date == today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already claimed today's bonus. Come back tomorrow!",
        )

    # Streak calculation
    if user.last_bonus_date == (today - timedelta(days=1)):
        new_streak = user.consecutive_bonus_days + 1
    else:
        new_streak = 1  # Streak reset or starting first time

    streak_rewards = get_streak_rewards(db)
    day_idx = ((new_streak - 1) % 7) + 1
    coins_to_award = streak_rewards[day_idx - 1]

    # Ledger event ID prevents any concurrent race conditions
    tx_event_id = f"daily_{user.id}_{today.isoformat()}"

    tx, is_new = wallet_service.credit_coins(
        db=db,
        user_id=user.id,
        amount=coins_to_award,
        tx_type="DAILY_BONUS",
        source=f"DAY_{day_idx}_STREAK",
        external_event_id=tx_event_id,
        metadata={"streak_day": day_idx, "claim_date": today.isoformat()},
    )

    if not is_new:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Daily bonus for today was already claimed",
        )

    user.consecutive_bonus_days = new_streak
    user.last_bonus_date = today

    db.add(
        Notification(
            user_id=user.id,
            title="Daily Bonus Claimed! 🎁",
            message=f"You claimed your Day {day_idx} bonus of +{coins_to_award:.0f} Coins. Keep your streak alive!",
            type="REWARD",
        )
    )

    db.commit()

    wallet = wallet_service.get_or_create_wallet(db, user.id)
    return DailyBonusClaimResponse(
        success=True,
        streak_day=day_idx,
        coins_earned=coins_to_award,
        new_balance=Decimal(str(wallet.available_coins)),
        message=f"Successfully claimed Day {day_idx} bonus of +{coins_to_award:.0f} Coins!",
    )
