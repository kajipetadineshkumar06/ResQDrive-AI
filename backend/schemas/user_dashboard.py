from pydantic import BaseModel
from typing import Optional


class EmergencyDashboard(BaseModel):
    id: int
    type: str
    description: str
    priority: str
    status: str


class ServiceDashboard(BaseModel):
    provider: str
    service_type: str
    phone: str
    rating: float
    request_status: str


class ProviderLocationDashboard(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class UserDashboardResponse(BaseModel):
    emergency: EmergencyDashboard
    service: ServiceDashboard
    provider_location: ProviderLocationDashboard