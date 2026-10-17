from pydantic import BaseModel


# ==========================
# USER SCHEMAS
# ==========================

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str



class UserResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    phone: str


    class Config:
        from_attributes = True

# ==========================
# VEHICLE SCHEMAS
# ==========================

class VehicleCreate(BaseModel):
    plate_number: str
    make: str
    model: str
    year: int
    vehicle_type: str
    fuel_type: str
    vehicle_color: str


class VehicleResponse(BaseModel):
    vehicle_id: int
    plate_number: str
    make: str
    model: str
    year: int
    vehicle_type: str
    fuel_type: str
    vehicle_color: str

    class Config:
        from_attributes = True


# ==========================
# EMERGENCY SCHEMAS
# ==========================

class EmergencyCreate(BaseModel):
    user_id: int
    vehicle_id: int | None = None
    emergency_type: str
    description: str
    location_lat: float
    location_lng: float
    priority: str
    recommended_service: str | None = None


class EmergencyResponse(BaseModel):
    emergency_id: int
    user_id: int
    vehicle_id: int | None = None
    emergency_type: str
    description: str
    location_lat: float
    location_lng: float
    status: str
    priority: str
    recommended_service: str | None = None

    class Config:
        from_attributes = True