from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ==========================================
# CREATE REQUEST
# ==========================================

class ServiceRequestCreate(BaseModel):

    emergency_id: int

    provider_id: int

    estimated_arrival: Optional[int] = None

    notes: Optional[str] = None


# ==========================================
# UPDATE REQUEST
# ==========================================
#
# Customer can update:
#   - estimated_arrival
#   - notes
#
# Customer cannot change request_status.
#
# Provider status changes are handled by:
#
# /provider/request/{id}/accept
# /provider/request/{id}/start
# /provider/request/{id}/arrived
# /provider/request/{id}/complete
#
# ==========================================

class ServiceRequestUpdate(BaseModel):

    request_status: Optional[str] = None

    estimated_arrival: Optional[int] = None

    notes: Optional[str] = None


# ==========================================
# RESPONSE
# ==========================================

class ServiceRequestResponse(BaseModel):

    request_id: int

    emergency_id: int

    # Provider can be None while the request
    # is waiting for an available provider.

    provider_id: Optional[int] = None

    user_id: int

    request_status: str

    estimated_arrival: Optional[int] = None

    notes: Optional[str] = None

    requested_at: datetime

    accepted_at: Optional[datetime] = None

    started_at: Optional[datetime] = None

    arrived_at: Optional[datetime] = None

    completed_at: Optional[datetime] = None

    cancelled_at: Optional[datetime] = None

    class Config:
        from_attributes = True