from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from schemas.tracking import TrackingUpdate

from models.provider_location import ProviderLocation
from models.service_provider import ServiceProvider
from models.service_request import ServiceRequest


router = APIRouter(
    prefix="/tracking",
    tags=["Live Tracking"]
)


@router.post("/update")
def update_tracking(
    data: TrackingUpdate,
    db: Session = Depends(get_db)
):

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == data.provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    location = db.query(ProviderLocation).filter(
        ProviderLocation.provider_id == data.provider_id
    ).first()

    if location:

        location.latitude = data.latitude
        location.longitude = data.longitude

    else:

        location = ProviderLocation(
            provider_id=data.provider_id,
            latitude=data.latitude,
            longitude=data.longitude
        )

        db.add(location)

    db.commit()
    db.refresh(location)

    return {
        "message": "Live location updated",
        "provider_id": data.provider_id,
        "latitude": data.latitude,
        "longitude": data.longitude
    }


@router.get("/{emergency_id}")
def track_provider(
    emergency_id: int,
    db: Session = Depends(get_db)
):

    request = db.query(ServiceRequest).filter(
        ServiceRequest.emergency_id == emergency_id
    ).first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Service request not found"
        )

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == request.provider_id
    ).first()

    location = db.query(ProviderLocation).filter(
        ProviderLocation.provider_id == request.provider_id
    ).first()

    if not location:
        raise HTTPException(
            status_code=404,
            detail="Provider location not found"
        )

    return {
        "provider": provider.name,
        "service": provider.service_type,
        "phone": provider.phone,
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
        "status": request.request_status
    }
