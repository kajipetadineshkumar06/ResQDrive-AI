from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from math import radians, sin, cos, sqrt, atan2

from database import get_db
from schemas.nearby import NearbyRequest
from models.service_provider import ServiceProvider
from models.provider_location import ProviderLocation


router = APIRouter(
    prefix="/nearby",
    tags=["Nearby Assistance"]
)


def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    R = 6371   # Earth radius in km

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))


    dlat = lat2 - lat1
    dlon = lon2 - lon1


    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2

    c = 2 * atan2(sqrt(a), sqrt(1-a))


    return R * c



@router.post("/providers")
def nearby_providers(
    data: NearbyRequest,
    db: Session = Depends(get_db)
):

    providers = db.query(
        ServiceProvider,
        ProviderLocation
    ).join(
        ProviderLocation,
        ServiceProvider.provider_id == ProviderLocation.provider_id
    ).filter(
        ServiceProvider.service_type == data.service_type,
        ServiceProvider.is_available.is_(True),
        ServiceProvider.verified.is_(True),
    ).all()


    result = []


    for provider, location in providers:

        distance = calculate_distance(
            data.latitude,
            data.longitude,
            location.latitude,
            location.longitude
        )


        # Calculate ETA
        eta = max(1, round((distance / 30) * 60))


        result.append({

            "provider_id": provider.provider_id,
            "name": provider.name,
            "service": provider.service_type,
            "phone": provider.phone,
            "rating": provider.rating_avg,
            "distance_km": round(distance,2),
            "eta_minutes": eta

        })


    result.sort(
        key=lambda x:x["distance_km"]
    )


    return {
        "count":len(result),
        "providers":result
    }
