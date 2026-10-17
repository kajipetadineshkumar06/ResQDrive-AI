from pydantic import BaseModel
from typing import List


class ProviderJob(BaseModel):
    request_id: int
    emergency_id: int
    customer_id: int
    emergency_type: str
    description: str
    priority: str
    latitude: float
    longitude: float
    status: str


class JobStatusUpdate(BaseModel):
    status: str