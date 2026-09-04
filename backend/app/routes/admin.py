from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet, WalletTransaction
from app.models.ad_event import AdEvent
from app.models.withdrawal import Withdrawal
from app.models.task import Task, TaskCompletion
from app.models.admin import AdminUser, AdminAction
from app.models.settings import AppSetting
from app.models.fraud import FraudEvent
from app.models.notification import Notification
from app.schemas.admin import (
    AdminDashboardMetrics,
    AdminUserItem,
    AdminUserDetail,
    AdminBalanceAdjustRequest,
    AdminUserStatusUpdate,
    AdminWithdrawalActionRequest,
    AdminTaskCreate,
    AdminSettingItem,
    AdminSettingUpdate,
    AdminActionLogItem,
    FraudEventItem,
)
from app.schemas.withdrawal import WithdrawalResponse
from app.schemas.tasks import TaskItemResponse
from app.security.deps import get_current_admin, get_client_ip
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


def log_admin_action(
    db: Session,
    admin_id: int,
    action_type: str,
    details: str,
    target_user_id: Optional[int] = None,
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Writes an immutable entry to the admin audit log."""
    action = AdminAction(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action_type=action_type,
        details=details,
        previous_state=previous_state,
        new_state=new_state,
        ip_address=ip_address,
    )
    db.add(action)
    db.flush()


@router.get("/dashboard", response_model=AdminDashboardMetrics)
def get_dashboard_metrics(
    admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)
):
    """Returns platform-wide operational KPIs, economics, and revenue estimations."""
    today = date.today()
    today_dt = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "ACTIVE").count()
    todays_users = db.query(User).filter(User.created_at >= today_dt).count()

    # Total coins issued (positive transactions)
    coins_issued_result = (
        db.query(func.sum(WalletTransaction.amount))
        .filter(WalletTransaction.amount > 0)
        .scalar()
    )
    total_coins_issued = Decimal(str(coins_issued_result or 0.0))

    # Withdrawals metrics
    total_withdrawals_count = db.query(Withdrawal).count()
    pending_withdrawals_count = (
        db.query(Withdrawal).filter(Withdrawal.status == "PENDING").count()
    )
    paid_withdrawals_count = (
        db.query(Withdrawal).filter(Withdrawal.status == "PAID").count()
    )

    pending_amount_result = (
        db.query(func.sum(Withdrawal.amount_rupees))
        .filter(Withdrawal.status == "PENDING")
        .scalar()
    )
    pending_withdrawals_amount = Decimal(str(pending_amount_result or 0.0))

    paid_amount_result = (
        db.query(func.sum(Withdrawal.amount_rupees))
        .filter(Withdrawal.status == "PAID")
        .scalar()
    )
    paid_withdrawals_amount = Decimal(str(paid_amount_result or 0.0))

    # Ad events
    todays_ad_events = (
        db.query(AdEvent)
        .filter(AdEvent.created_at >= today_dt, AdEvent.status == "VERIFIED")
        .count()
    )
    total_ad_events = db.query(AdEvent).filter(AdEvent.status == "VERIFIED").count()

    # Economics & revenue estimation:
    # Example model: $0.30 gross ad revenue per verified impression
    rev_per_ad_setting = db.query(AppSetting).filter(AppSetting.key == "ESTIMATED_REVENUE_PER_AD_RUPEES").first()
    rev_per_ad = Decimal(rev_per_ad_setting.value) if rev_per_ad_setting else Decimal("0.35")
    coins_per_rupee = wallet_service.get_coins_per_rupee(db)

    estimated_gross_revenue = Decimal(total_ad_events) * rev_per_ad
    estimated_user_rewards = (
        (total_coins_issued / coins_per_rupee).quantize(Decimal("0.01"))
        if coins_per_rupee > 0
        else Decimal("0.00")
    )
    estimated_platform_margin = estimated_gross_revenue - estimated_user_rewards

    return AdminDashboardMetrics(
        total_users=total_users,
        active_users=active_users,
        todays_users=todays_users,
        total_coins_issued=total_coins_issued,
        total_withdrawals_count=total_withdrawals_count,
        pending_withdrawals_count=pending_withdrawals_count,
        paid_withdrawals_count=paid_withdrawals_count,
        pending_withdrawals_amount=pending_withdrawals_amount,
        paid_withdrawals_amount=paid_withdrawals_amount,
        todays_ad_events=todays_ad_events,
        estimated_gross_revenue=estimated_gross_revenue,
        estimated_user_rewards=estimated_user_rewards,
        estimated_platform_margin=estimated_platform_margin,
        demo_mode=(settings.APP_ENV == "development"),
    )


@router.get("/users", response_model=List[AdminUserItem])
def list_users(
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Lists users with optional search by username, first name, or referral code."""
    query = db.query(User)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_pattern))
            | (User.first_name.ilike(search_pattern))
            | (User.referral_code.ilike(search_pattern))
        )

    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for u in users:
        wallet = wallet_service.get_or_create_wallet(db, u.id)
        items.append(
            AdminUserItem(
                id=u.id,
                telegram_id=u.telegram_id,
                username=u.username,
                first_name=u.first_name,
                referral_code=u.referral_code,
                status=u.status,
                risk_level=u.risk_level,
                available_coins=Decimal(str(wallet.available_coins)),
                lifetime_earned=Decimal(str(wallet.lifetime_earned)),
                created_at=u.created_at,
                last_login_at=u.last_login_at,
            )
        )
    return items


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user_detail(
    user_id: int, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)
):
    """Returns complete details, balances, activity counts for a user."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    wallet = wallet_service.get_or_create_wallet(db, u.id)
    ref_count = db.query(User).filter(User.referred_by_id == u.id).count()
    ad_count = db.query(AdEvent).filter(AdEvent.user_id == u.id, AdEvent.status == "VERIFIED").count()
    task_count = db.query(TaskCompletion).filter(TaskCompletion.user_id == u.id).count()

    return AdminUserDetail(
        id=u.id,
        telegram_id=u.telegram_id,
        username=u.username,
        first_name=u.first_name,
        referral_code=u.referral_code,
        status=u.status,
        risk_level=u.risk_level,
        available_coins=Decimal(str(wallet.available_coins)),
        pending_coins=Decimal(str(wallet.pending_coins)),
        lifetime_earned=Decimal(str(wallet.lifetime_earned)),
        lifetime_withdrawn=Decimal(str(wallet.lifetime_withdrawn)),
        total_referrals=ref_count,
        total_ads_watched=ad_count,
        total_tasks_completed=task_count,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


@router.post("/users/{user_id}/adjust")
def adjust_user_balance(
    user_id: int,
    payload: AdminBalanceAdjustRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Manually adjusts a user's coin balance.
    Strictly recorded into an immutable audit trail and ledger transaction.
    """
    client_ip = get_client_ip(request)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    wallet = wallet_service.get_or_create_wallet(db, u.id)
    balance_before = Decimal(str(wallet.available_coins))
    adjust_amount = Decimal(str(payload.amount_coins))

    if adjust_amount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Adjustment amount cannot be zero"
        )

    if adjust_amount > 0:
        tx, _ = wallet_service.credit_coins(
            db=db,
            user_id=u.id,
            amount=adjust_amount,
            tx_type="ADJUSTMENT",
            source=f"ADMIN_{admin.username}",
            metadata={"admin_id": admin.id, "reason": payload.reason},
            ip_address=client_ip,
        )
    else:
        abs_amount = abs(adjust_amount)
        if balance_before < abs_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot debit {abs_amount} coins. User only has {balance_before} coins.",
            )
        tx = wallet_service.debit_coins(
            db=db,
            user_id=u.id,
            amount=abs_amount,
            tx_type="ADJUSTMENT",
            source=f"ADMIN_{admin.username}",
            metadata={"admin_id": admin.id, "reason": payload.reason},
            ip_address=client_ip,
        )

    balance_after = Decimal(str(wallet.available_coins))

    log_admin_action(
        db=db,
        admin_id=admin.id,
        target_user_id=u.id,
        action_type="BALANCE_ADJUSTMENT",
        details=f"Adjusted balance by {adjust_amount:+.2f} coins. Reason: {payload.reason}",
        previous_state=str(balance_before),
        new_state=str(balance_after),
        ip_address=client_ip,
    )

    db.add(
        Notification(
            user_id=u.id,
            title="Balance Adjusted by Admin ⚙️",
            message=f"Your balance was adjusted by {adjust_amount:+.2f} coins. Note: {payload.reason}",
            type="SYSTEM",
        )
    )

    db.commit()

    return {
        "success": True,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "adjustment": adjust_amount,
        "message": "Balance adjusted successfully and logged to audit trail.",
    }


@router.post("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates user status (ACTIVE, SUSPENDED, BANNED) and risk level with audit log."""
    client_ip = get_client_ip(request)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    prev_state = f"status={u.status}, risk={u.risk_level}"
    if payload.status:
        u.status = payload.status.upper()
    if payload.risk_level:
        u.risk_level = payload.risk_level.upper()

    new_state = f"status={u.status}, risk={u.risk_level}"

    log_admin_action(
        db=db,
        admin_id=admin.id,
        target_user_id=u.id,
        action_type="USER_STATUS_CHANGE",
        details=f"Changed user status. Reason: {payload.reason}",
        previous_state=prev_state,
        new_state=new_state,
        ip_address=client_ip,
    )
    db.commit()

    return {"success": True, "user_id": u.id, "status": u.status, "risk_level": u.risk_level}


@router.get("/withdrawals", response_model=List[WithdrawalResponse])
def list_withdrawals(
    status_filter: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Lists withdrawal requests across the platform with filtering."""
    query = db.query(Withdrawal)
    if status_filter:
        query = query.filter(Withdrawal.status == status_filter.upper())

    withdrawals = query.order_by(Withdrawal.created_at.desc()).offset(offset).limit(limit).all()
    return [WithdrawalResponse.model_validate(w) for w in withdrawals]


@router.post("/withdrawals/{withdrawal_id}/action")
def process_withdrawal_action(
    withdrawal_id: str,
    payload: AdminWithdrawalActionRequest,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Processes withdrawal status change (APPROVED, PAID, REJECTED, CANCELLED).
    If REJECTED or CANCELLED, automatically refunds debited coins back to the user wallet!
    """
    client_ip = get_client_ip(request)
    w = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal request not found")

    target_status = payload.status.upper()
    valid_statuses = ("APPROVED", "PAID", "REJECTED", "CANCELLED")
    if target_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {', '.join(valid_statuses)}",
        )

    prev_status = w.status
    w.status = target_status
    w.admin_notes = payload.admin_notes
    w.processed_by_admin_id = admin.id
    w.processed_at = datetime.now(timezone.utc)

    # If rejected or cancelled, refund coins back to user
    if target_status in ("REJECTED", "CANCELLED") and prev_status in ("PENDING", "PROCESSING", "APPROVED"):
        coins_to_refund = Decimal(str(w.coins_deducted))
        wallet_service.refund_coins(
            db=db,
            user_id=w.user_id,
            amount=coins_to_refund,
            source=f"WITHDRAWAL_REFUND_{w.id[:8]}",
            reason=f"Withdrawal {target_status}: {payload.admin_notes or 'No reason provided'}",
        )
        db.add(
            Notification(
                user_id=w.user_id,
                title="Withdrawal Refunded ↩️",
                message=f"Your withdrawal of {w.amount_rupees:.4f} {w.payout_method} was {target_status.lower()}. {coins_to_refund:.0f} coins were refunded back to your wallet.",
                type="WITHDRAWAL",
            )
        )
    elif target_status == "PAID":
        db.add(
            Notification(
                user_id=w.user_id,
                title="Withdrawal Paid Successfully! 💰",
                message=f"Your payout of {w.amount_rupees:.4f} {w.payout_method} via {w.payout_method} has been sent.",
                type="WITHDRAWAL",
            )
        )

    log_admin_action(
        db=db,
        admin_id=admin.id,
        target_user_id=w.user_id,
        action_type="WITHDRAWAL_ACTION",
        details=f"Changed withdrawal {w.id} status to {target_status}. Notes: {payload.admin_notes}",
        previous_state=prev_status,
        new_state=target_status,
        ip_address=client_ip,
    )

    db.commit()
    db.refresh(w)

    return WithdrawalResponse.model_validate(w)


@router.get("/tasks", response_model=List[TaskItemResponse])
def admin_list_tasks(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.id.desc()).all()
    return [
        TaskItemResponse(
            id=t.id,
            title=t.title,
            description=t.description,
            icon=t.icon,
            reward_coins=Decimal(str(t.reward_coins)),
            action_url=t.action_url,
            verification_method=t.verification_method,
            status=t.status,
            is_completed=False,
        )
        for t in tasks
    ]


@router.post("/tasks", response_model=TaskItemResponse)
def admin_create_task(
    payload: AdminTaskCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    task = Task(
        title=payload.title,
        description=payload.description,
        icon=payload.icon,
        reward_coins=payload.reward_coins,
        action_url=payload.action_url,
        verification_method=payload.verification_method,
        verification_data=payload.verification_data,
        status=payload.status,
        max_completions=payload.max_completions,
    )
    db.add(task)
    db.flush()

    log_admin_action(
        db=db,
        admin_id=admin.id,
        action_type="TASK_CREATE",
        details=f"Created task: {task.title} (Reward: {task.reward_coins} coins)",
        ip_address=client_ip,
    )
    db.commit()
    db.refresh(task)

    return TaskItemResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        icon=task.icon,
        reward_coins=Decimal(str(task.reward_coins)),
        action_url=task.action_url,
        verification_method=task.verification_method,
        status=task.status,
        is_completed=False,
    )


@router.get("/settings", response_model=List[AdminSettingItem])
def list_settings(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    settings_list = db.query(AppSetting).all()
    return [
        AdminSettingItem(key=s.key, value=s.value, description=s.description)
        for s in settings_list
    ]


@router.put("/settings/{key}")
def update_setting(
    key: str,
    payload: AdminSettingUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    client_ip = get_client_ip(request)
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not setting:
        setting = AppSetting(key=key, value=payload.value)
        db.add(setting)
        prev_val = None
    else:
        prev_val = setting.value
        setting.value = payload.value

    log_admin_action(
        db=db,
        admin_id=admin.id,
        action_type="SETTING_UPDATE",
        details=f"Updated setting {key} = {payload.value}",
        previous_state=prev_val,
        new_state=payload.value,
        ip_address=client_ip,
    )
    db.commit()

    return {"success": True, "key": key, "value": setting.value}


@router.get("/fraud", response_model=List[FraudEventItem])
def list_fraud_events(
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    events = db.query(FraudEvent).order_by(FraudEvent.created_at.desc()).limit(limit).all()
    return [FraudEventItem.model_validate(e) for e in events]


@router.get("/logs", response_model=List[AdminActionLogItem])
def list_admin_logs(
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    actions = db.query(AdminAction).order_by(AdminAction.created_at.desc()).limit(limit).all()
    items = []
    for a in actions:
        admin_user = db.query(AdminUser).filter(AdminUser.id == a.admin_id).first()
        items.append(
            AdminActionLogItem(
                id=a.id,
                admin_username=admin_user.username if admin_user else "Unknown",
                target_user_id=a.target_user_id,
                action_type=a.action_type,
                details=a.details,
                previous_state=a.previous_state,
                new_state=a.new_state,
                ip_address=a.ip_address,
                created_at=a.created_at,
            )
        )
    return items
