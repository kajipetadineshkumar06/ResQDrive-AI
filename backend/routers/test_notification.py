from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

from services.firebase_notification import send_push_notification

router = APIRouter(
    prefix="/notifications",
    tags=["Notification Test"]
)


@router.post("/test/{user_id}")
def test_notification(
    user_id: int,
    db: Session = Depends(get_db)
):

    success = send_push_notification(

        db=db,

        user_id=user_id,

        title="ResQDrive AI",

        body="Firebase Push Notification is working!",

        data={

            "type": "test",

            "screen": "home"

        }

    )

    if success:

        return {

            "message": "Notification sent successfully"

        }

    return {

        "message": "Failed to send notification"

    }