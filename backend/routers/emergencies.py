from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.emergency import Emergency
from services.emergency_service import create_emergency_service
from schemas.emergency import (
    EmergencyCreate,
    EmergencyUpdate,
    EmergencyResponse
)

router = APIRouter(
    prefix="/emergencies",
    tags=["Emergencies"]
)


# ==============================
# Create Emergency
# ==============================

@router.post("/", response_model=EmergencyResponse)
def create_emergency(
    emergency: EmergencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    result = create_emergency_service(

        db=db,

        current_user=current_user,

        data=emergency

    )

    return result["emergency"]


# ==============================
# Get My Emergencies
# ==============================

@router.get("/", response_model=list[EmergencyResponse])
def get_my_emergencies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    emergencies = db.query(Emergency).filter(
        Emergency.user_id == current_user.user_id
    ).order_by(
        Emergency.created_at.desc()
    ).all()

    return emergencies


# ==============================
# Get Emergency By ID
# ==============================

@router.get("/{emergency_id}", response_model=EmergencyResponse)
def get_emergency(
    emergency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    emergency = db.query(Emergency).filter(
        Emergency.emergency_id == emergency_id,
        Emergency.user_id == current_user.user_id
    ).first()

    if emergency is None:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found"
        )

    return emergency


# ==============================
# Update Emergency
# ==============================

@router.put("/{emergency_id}", response_model=EmergencyResponse)
def update_emergency(
    emergency_id: int,
    request: EmergencyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    emergency = db.query(Emergency).filter(
        Emergency.emergency_id == emergency_id,
        Emergency.user_id == current_user.user_id
    ).first()

    if emergency is None:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found"
        )

    emergency.status = request.status

    if request.status == "resolved":
        emergency.resolved_at = func.now()

    db.commit()
    db.refresh(emergency)

    return emergency


# ==============================
# Delete Emergency
# ==============================

@router.delete("/{emergency_id}")
def delete_emergency(
    emergency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    emergency = db.query(Emergency).filter(
        Emergency.emergency_id == emergency_id,
        Emergency.user_id == current_user.user_id
    ).first()

    if emergency is None:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found"
        )

    db.delete(emergency)
    db.commit()

    return {
        "message": "Emergency deleted successfully"
    }