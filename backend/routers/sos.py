from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.sos_alert import SOSAlert


router = APIRouter(
    prefix="/sos",
    tags=["SOS"]
)


@router.post("/create")
def create_sos(
    user_id:int,
    latitude:float,
    longitude:float,
    db:Session = Depends(get_db)
):

    alert = SOSAlert(
        user_id=user_id,
        latitude=latitude,
        longitude=longitude
    )


    db.add(alert)
    db.commit()
    db.refresh(alert)


    return {
        "message":"SOS Activated",
        "alert_id":alert.alert_id,
        "status":alert.status
    }