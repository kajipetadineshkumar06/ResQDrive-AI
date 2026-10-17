from pydantic import BaseModel


class LiveTrackingResponse(BaseModel):

    event: str

    provider_id: int

    emergency_id: int

    latitude: float

    longitude: float

    distance_meters: int

    eta: str

    polyline: str