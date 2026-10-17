from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.vehicle import Vehicle

from schemas.vehicle import (
    VehicleCreate,
    VehicleResponse
)


router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"]
)


# ==========================================
# CREATE VEHICLE
# ==========================================

@router.post(
    "/",
    response_model=VehicleResponse
)
def create_vehicle(
    vehicle: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    existing_vehicle = db.query(Vehicle).filter(
        Vehicle.plate_number == vehicle.plate_number,
        Vehicle.user_id == current_user.user_id
    ).first()

    if existing_vehicle:

        raise HTTPException(
            status_code=400,
            detail="Vehicle already exists for this user"
        )

    new_vehicle = Vehicle(
        user_id=current_user.user_id,
        plate_number=vehicle.plate_number.upper(),
        make=vehicle.make,
        model=vehicle.model,
        year=vehicle.year,
        vehicle_type=vehicle.vehicle_type,
        fuel_type=vehicle.fuel_type,
        vehicle_color=vehicle.vehicle_color
    )

    db.add(new_vehicle)

    try:

        db.commit()
        db.refresh(new_vehicle)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to create vehicle"
        )

    return new_vehicle


# ==========================================
# GET MY VEHICLES
# ==========================================

@router.get(
    "/",
    response_model=list[VehicleResponse]
)
def get_my_vehicles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == current_user.user_id
    ).all()

    return vehicles


# ==========================================
# GET SINGLE VEHICLE
# ==========================================

@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse
)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    vehicle = db.query(Vehicle).filter(
        Vehicle.vehicle_id == vehicle_id,
        Vehicle.user_id == current_user.user_id
    ).first()

    if not vehicle:

        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    return vehicle


# ==========================================
# DELETE VEHICLE
# ==========================================

@router.delete("/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    vehicle = db.query(Vehicle).filter(
        Vehicle.vehicle_id == vehicle_id,
        Vehicle.user_id == current_user.user_id
    ).first()

    if not vehicle:

        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    db.delete(vehicle)

    db.commit()

    return {
        "message": "Vehicle deleted successfully"
    }