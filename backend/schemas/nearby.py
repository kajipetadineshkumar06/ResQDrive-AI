from pydantic import BaseModel


class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    service_type: str