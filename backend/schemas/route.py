from pydantic import BaseModel
from decimal import Decimal


class RouteRequest(BaseModel):
    origin_lat: Decimal
    origin_lng: Decimal

    destination_lat: Decimal
    destination_lng: Decimal
