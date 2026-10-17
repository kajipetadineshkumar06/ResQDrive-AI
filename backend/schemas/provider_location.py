from pydantic import BaseModel, Field


# =========================================================
# PROVIDER GPS UPDATE REQUEST
# =========================================================

class ProviderLocationCreate(BaseModel):

    latitude: float = Field(
        ...,
        ge=-90,
        le=90
    )

    longitude: float = Field(
        ...,
        ge=-180,
        le=180
    )


# =========================================================
# PROVIDER GPS RESPONSE
# =========================================================

class ProviderLocationResponse(BaseModel):

    provider_id: int

    latitude: float

    longitude: float

    updated_at: object

    class Config:
        from_attributes = True