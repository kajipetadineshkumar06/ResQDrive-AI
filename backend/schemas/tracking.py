from pydantic import BaseModel


class TrackingUpdate(BaseModel):
    provider_id: int
    latitude: float
    longitude: float
