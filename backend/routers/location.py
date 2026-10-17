from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.location import LocationUpdate
from database import get_db
from models.provider_location import ProviderLocation
from models.service_provider import ServiceProvider


router = APIRouter(
    prefix="/location",
    tags=["Live Tracking"]
)


# Update mechanic location
@router.post("/update")
def update_location(
    data: LocationUpdate,
    db: Session = Depends(get_db)
):

    location = ProviderLocation(
    provider_id=data.provider_id,
    latitude=data.latitude,
    longitude=data.longitude
)

    db.add(location)
    db.commit()
    db.refresh(location)


    return {
        "message":"Location updated",
        "provider_id":location.provider_id
    }



# Get mechanic location
@router.get("/provider/{provider_id}")
def get_location(
    provider_id:int,
    db:Session=Depends(get_db)
):

    location = db.query(ProviderLocation).filter(
        ProviderLocation.provider_id == provider_id
    ).order_by(
        ProviderLocation.location_id.desc()
    ).first()


    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == provider_id
    ).first()


    return {
        "provider":provider.name,
        "latitude":location.latitude,
        "longitude":location.longitude
    }