# ==========================================
# schemas/service_provider.py
# ==========================================

from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


# ==========================================
# CREATE PROVIDER
# ==========================================

class ProviderCreate(BaseModel):

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    provider_image: str | None = None

    experience_years: int | None = None

    user_id: int | None = None


# ==========================================
# UPDATE PROVIDER
# ==========================================

class ProviderUpdate(BaseModel):

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    provider_image: str | None = None

    experience_years: int | None = None

    class Config:
        extra = "forbid"


# ==========================================
# RESPONSE
# ==========================================

class ProviderResponse(BaseModel):

    provider_id: int

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    rating_avg: Decimal

    is_available: bool

    provider_image: str | None = None

    experience_years: int | None = None

    verified: bool

    user_id: int | None = None

    is_tracking: bool

    class Config:
        from_attributes = True
