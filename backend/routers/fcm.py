from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.fcm_token import FCMToken

from schemas.fcm import TokenCreate

router = APIRouter(
    prefix="/fcm",
    tags=["Firebase Notifications"]
)


# ==========================================
# REGISTER / UPDATE FCM TOKEN
# ==========================================

@router.post("/register")
def register_token(
    data: TokenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing = db.query(
        FCMToken
    ).filter(
        FCMToken.user_id == current_user.user_id
    ).first()

    if existing:

        existing.token = data.token

        db.commit()

        db.refresh(existing)

        return {

            "message": "FCM token updated successfully",

            "user_id": current_user.user_id,

            "token": existing.token

        }

    token = FCMToken(

        user_id=current_user.user_id,

        token=data.token

    )

    db.add(token)

    db.commit()

    db.refresh(token)

    return {

        "message": "FCM token registered successfully",

        "user_id": current_user.user_id,

        "token": token.token

    }


# ==========================================
# GET MY TOKEN
# ==========================================

@router.get("/my-token")
def get_my_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    token = db.query(
        FCMToken
    ).filter(
        FCMToken.user_id == current_user.user_id
    ).first()

    if token is None:

        return {

            "message": "No token registered"

        }

    return {

        "user_id": current_user.user_id,

        "token": token.token

    }


# ==========================================
# DELETE MY TOKEN
# ==========================================

@router.delete("/remove")
def remove_token(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    token = db.query(
        FCMToken
    ).filter(
        FCMToken.user_id == current_user.user_id
    ).first()

    if token is None:

        return {

            "message": "Token not found"

        }

    db.delete(token)

    db.commit()

    return {

        "message": "FCM token removed successfully"

    }