from pydantic import BaseModel


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
    user_id: int
    plate_number: str
    make: str
    model: str
    year: int
    vehicle_type: str
    fuel_type: str
    vehicle_color: str

    class Config:
        from_attributes = True