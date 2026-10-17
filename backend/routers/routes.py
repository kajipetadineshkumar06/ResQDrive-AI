from fastapi import APIRouter

from schemas.route import RouteRequest

from services.maps_service import get_route

router = APIRouter(
    prefix="/routes",
    tags=["Google Maps"]
)


@router.post("/eta")
def calculate_route(data: RouteRequest):

    return get_route(

        data.origin_lat,

        data.origin_lng,

        data.destination_lat,

        data.destination_lng

    )