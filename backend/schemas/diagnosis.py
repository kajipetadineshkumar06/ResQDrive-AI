# ==========================================
# schemas/diagnosis.py
# ==========================================

from pydantic import BaseModel, Field


# ==========================================
# DIAGNOSIS REQUEST
# ==========================================

class DiagnosisRequest(BaseModel):

    vehicle_id: int = Field(
        ...,
        gt=0,
        description="ID of the vehicle"
    )

    symptoms: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Description of vehicle symptoms"
    )


# ==========================================
# DIAGNOSIS RESPONSE
# ==========================================

class DiagnosisResponse(BaseModel):

    vehicle_id: int

    diagnosis: str

    possible_causes: list[str]

    recommended_service: str

    priority: str

    confidence: int

    advice: str