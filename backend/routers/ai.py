from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from models.emergency import Emergency
from models.service_provider import ServiceProvider

from ai.recommendation import recommend_service

router = APIRouter(
    prefix="/ai",
    tags=["AI Recommendation"]
)


@router.get("/recommend/{emergency_id}")
def recommend_provider(
    emergency_id: int,
    db: Session = Depends(get_db)
):

    emergency = db.query(Emergency).filter(
        Emergency.emergency_id == emergency_id
    ).first()

    if not emergency:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found"
        )

    service = recommend_service(emergency.emergency_type)

    providers = db.query(ServiceProvider).filter(
        ServiceProvider.service_type == service,
        ServiceProvider.is_available.is_(True),
        ServiceProvider.verified.is_(True),
    ).all()

    return {
        "emergency_id": emergency.emergency_id,
        "emergency_type": emergency.emergency_type,
        "recommended_service": service,
        "providers": [
            {
                "provider_id": p.provider_id,
                "name": p.name,
                "phone": p.phone,
                "rating": float(p.rating_avg),
                "verified": p.verified
            }
            for p in providers
        ]
    }
