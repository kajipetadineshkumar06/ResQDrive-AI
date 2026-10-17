from pydantic import BaseModel


class LocationUpdate(BaseModel):
    provider_id: int
    latitude: float
    longitude: float