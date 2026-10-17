# ==========================================
# schemas/emergency.py
# ==========================================

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime


# ==========================================
# CREATE EMERGENCY
# ==========================================

class EmergencyCreate(BaseModel):

    vehicle_id: int

    emergency_type: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    description: str | None = None

    location_lat: Decimal

    location_lng: Decimal

    priority: str = "high"


# ==========================================
# UPDATE EMERGENCY
# ==========================================

class EmergencyUpdate(BaseModel):

    status: str


# ==========================================
# RESPONSE
# ==========================================

class EmergencyResponse(BaseModel):

    emergency_id: int

    user_id: int

    vehicle_id: int

    emergency_type: str

    description: str | None = None

    location_lat: Decimal

    location_lng: Decimal

    priority: str

    status: str

    recommended_service: str | None = None

    created_at: datetime

    resolved_at: datetime | None = None

    class Config:
        from_attributes = True