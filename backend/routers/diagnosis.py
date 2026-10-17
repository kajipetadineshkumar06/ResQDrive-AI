# ==========================================
# routers/diagnosis.py
# ResQDrive AI - Vehicle NLP Diagnosis API
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

from models.vehicle import Vehicle

from schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResponse,
)

from services.vehicle_ai_service import (
    analyze_vehicle_problem,
)


# ==========================================
# ROUTER
# ==========================================

router = APIRouter(
    prefix="/diagnosis",
    tags=["AI Diagnosis"],
)


# ==========================================
# AI VEHICLE DIAGNOSIS
# ==========================================

@router.post(
    "/",
    response_model=DiagnosisResponse,
)
def diagnose(
    data: DiagnosisRequest,

    db: Session = Depends(get_db),

    current_user: User = Depends(
        get_current_user
    ),
):
    # ==========================================
    # CHECK VEHICLE OWNERSHIP
    # ==========================================

    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.vehicle_id == data.vehicle_id,
            Vehicle.user_id == current_user.user_id,
        )
        .first()
    )

    # ==========================================
    # VEHICLE NOT FOUND
    # ==========================================

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found",
        )

    # ==========================================
    # RUN RESQDRIVE VEHICLE AI
    # ==========================================

    result = analyze_vehicle_problem(
        data.symptoms
    )

    # ==========================================
    # NORMALIZE PRIORITY
    # ==========================================

    priority = str(
        result.get(
            "priority",
            "MEDIUM",
        )
    ).strip().lower()

    # ==========================================
    # RETURN AI RESULT
    # ==========================================

    return {
        "vehicle_id": vehicle.vehicle_id,

        "diagnosis": result.get(
            "vehicle_problem",
            data.symptoms,
        ),

        "possible_causes": result.get(
            "possible_causes",
            [],
        ),

        "recommended_service": result.get(
            "required_service",
            "roadside_assistance",
        ),

        "priority": priority,

        "confidence": result.get(
            "confidence",
            0,
        ),

        "advice": result.get(
            "safety_advice",
            (
                "Move to a safe location if possible. "
                "Avoid driving if the vehicle appears unsafe."
            ),
        ),
    }