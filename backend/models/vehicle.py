# ==========================================
# models/vehicle.py
# ==========================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey
)

from sqlalchemy.orm import relationship

from database import Base


class Vehicle(Base):

    __tablename__ = "vehicles"

    # ==========================================
    # VEHICLE ID
    # ==========================================

    vehicle_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # ==========================================
    # USER ID
    # ==========================================

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    # ==========================================
    # VEHICLE NUMBER
    # ==========================================

    plate_number = Column(
        String(50),
        nullable=False
    )

    # ==========================================
    # BRAND / MAKE
    # ==========================================

    make = Column(
        String(100),
        nullable=False
    )

    # ==========================================
    # MODEL
    # ==========================================

    model = Column(
        String(100),
        nullable=False
    )

    # ==========================================
    # MANUFACTURING YEAR
    # ==========================================

    year = Column(
        Integer,
        nullable=False
    )

    # ==========================================
    # VEHICLE TYPE
    # ==========================================

    vehicle_type = Column(
        String(50),
        nullable=True
    )

    # ==========================================
    # FUEL TYPE
    # ==========================================

    fuel_type = Column(
        String(50),
        nullable=True
    )

    # ==========================================
    # VEHICLE COLOR
    # ==========================================

    vehicle_color = Column(
        String(50),
        nullable=True
    )

    # ==========================================
    # USER RELATIONSHIP
    # ==========================================

    user = relationship(
        "User",
        back_populates="vehicles"
    )

    # ==========================================
    # EMERGENCY RELATIONSHIP
    # ==========================================

    emergencies = relationship(
        "Emergency",
        back_populates="vehicle"
    )