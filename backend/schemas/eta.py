from pydantic import BaseModel


class ETAResponse(BaseModel):
    provider_name: str
    distance_km: float
    estimated_time_minutes: int
    status: str