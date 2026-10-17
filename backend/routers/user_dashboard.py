from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

from models.emergency import Emergency
from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.provider_location import ProviderLocation

from schemas.user_dashboard import UserDashboardResponse


router = APIRouter(
    prefix="/user-dashboard",
    tags=["User Dashboard"]
)


@router.get(
    "/{user_id}",
    response_model=UserDashboardResponse
)
def user_dashboard(
    user_id: int,
    db: Session = Depends(get_db)
):

    emergency = db.query(Emergency).filter(
        Emergency.user_id == user_id
    ).order_by(
        Emergency.emergency_id.desc()
    ).first()

    if not emergency:
        return {
            "message": "No emergency found"
        }

    service_request = db.query(ServiceRequest).filter(
        ServiceRequest.emergency_id == emergency.emergency_id
    ).first()

    if not service_request:
        return {
            "emergency_id": emergency.emergency_id,
            "status": emergency.status,
            "message": "Waiting for provider assignment"
        }

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == service_request.provider_id
    ).first()

    if not provider:
        return {
            "message": "Provider not found"
        }

    location = db.query(ProviderLocation).filter(
        ProviderLocation.provider_id == provider.provider_id
    ).first()

    return {
        "emergency": {
            "id": emergency.emergency_id,
            "type": emergency.emergency_type,
            "description": emergency.description,
            "priority": emergency.priority,
            "status": emergency.status
        },
        "service": {
            "provider": provider.name,
            "service_type": provider.service_type,
            "phone": provider.phone,
            "rating": float(provider.rating_avg),
            "request_status": service_request.status
        },
        "provider_location": {
            "latitude": float(location.latitude) if location else None,
            "longitude": float(location.longitude) if location else None
        }
    }