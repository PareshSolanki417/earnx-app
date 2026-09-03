from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.security.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Returns the user's notifications, newest first."""
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )
    return [NotificationResponse.model_validate(n) for n in notifs]


@router.post("/read-all")
def mark_all_as_read(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Marks all notifications as read for the authenticated user."""
    db.query(Notification).filter(
        Notification.user_id == user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All notifications marked as read."}
