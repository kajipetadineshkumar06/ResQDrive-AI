# ==========================================
# routers/notification.py
# ResQDrive AI - Notification API
# ==========================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from database import get_db
from auth.oauth2 import get_current_user

from models.models import User
from models.notification import Notification

from schemas.notification import (
    NotificationCreate,
    NotificationResponse,
)


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


# =========================================================
# GET CURRENT USER NOTIFICATIONS
# =========================================================

@router.get(
    "/me",
    response_model=list[NotificationResponse],
)
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id
            == current_user.user_id
        )
        .order_by(
            Notification.created_at.desc()
        )
        .all()
    )

    return notifications


# =========================================================
# GET UNREAD NOTIFICATIONS
# =========================================================

@router.get(
    "/me/unread",
    response_model=list[NotificationResponse],
)
def get_unread_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id
            == current_user.user_id,
            Notification.status == "unread",
        )
        .order_by(
            Notification.created_at.desc()
        )
        .all()
    )

    return notifications


# =========================================================
# CREATE NOTIFICATION
# =========================================================

@router.post(
    "/create",
    response_model=NotificationResponse,
)
def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    new_notification = Notification(
        user_id=current_user.user_id,
        emergency_id=notification.emergency_id,
        provider_id=notification.provider_id,
        title=notification.title,
        message=notification.message,
        status="unread",
    )

    try:

        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)

    except Exception as error:

        db.rollback()

        print(
            "Create notification error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create notification",
        )

    return new_notification


# =========================================================
# MARK ONE NOTIFICATION AS READ
# =========================================================

@router.put(
    "/read/{notification_id}",
    response_model=NotificationResponse,
)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.notification_id
            == notification_id,
            Notification.user_id
            == current_user.user_id,
        )
        .first()
    )

    if notification is None:

        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification.status = "read"

    try:

        db.commit()
        db.refresh(notification)

    except Exception as error:

        db.rollback()

        print(
            "Mark notification read error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to mark notification as read",
        )

    return notification


# =========================================================
# MARK ALL NOTIFICATIONS AS READ
# =========================================================

@router.put(
    "/read-all",
)
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id
            == current_user.user_id,
            Notification.status != "read",
        )
        .all()
    )

    for notification in notifications:
        notification.status = "read"

    try:

        db.commit()

    except Exception as error:

        db.rollback()

        print(
            "Mark all notifications read error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to mark notifications as read",
        )

    return {
        "message": "All notifications marked as read",
        "count": len(notifications),
    }