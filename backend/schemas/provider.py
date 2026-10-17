from pydantic import BaseModel
from decimal import Decimal
from typing import Optional


# ==========================
# CREATE PROVIDER
# ==========================

class ProviderCreate(BaseModel):

    user_id: int

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    provider_image: Optional[str] = None

    experience_years: int = 0


# ==========================
# UPDATE PROVIDER
# ==========================

class ProviderUpdate(BaseModel):

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    provider_image: Optional[str] = None

    experience_years: int

    is_available: int

    verified: int


# ==========================
# RESPONSE
# ==========================

class ProviderResponse(BaseModel):

    provider_id: int

    user_id: Optional[int]

    name: str

    service_type: str

    phone: str

    location_lat: Decimal

    location_lng: Decimal

    rating_avg: Decimal

    is_available: int

    provider_image: Optional[str]

    experience_years: int

    verified: int

    class Config:
        from_attributes = True