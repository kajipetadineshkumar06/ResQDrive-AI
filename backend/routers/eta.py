from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

from models.provider_location import ProviderLocation
from models.emergency import Emergency

from services.eta_service import (
    calculate_distance,
    calculate_eta
)

router = APIRouter(
    prefix="/eta",
    tags=["ETA"]
)


@router.get("/{provider_id}/{emergency_id}")
def get_eta(
    provider_id: int,
    emergency_id: int,
    db: Session = Depends(get_db)
):

    provider = db.query(
        ProviderLocation
    ).filter(
        ProviderLocation.provider_id == provider_id
    ).first()

    if provider is None:
        return {
            "message": "Provider location not found"
        }

    emergency = db.query(
        Emergency
    ).filter(
        Emergency.emergency_id == emergency_id
    ).first()

    if emergency is None:
        return {
            "message": "Emergency not found"
        }

    distance = calculate_distance(

        provider.latitude,
        provider.longitude,

        emergency.location_lat,
        emergency.location_lng

    )

    eta = calculate_eta(distance)

    return {

        "provider_id": provider.provider_id,

        "emergency_id": emergency.emergency_id,

        "distance_km": round(distance, 2),

        "eta_minutes": eta

    }