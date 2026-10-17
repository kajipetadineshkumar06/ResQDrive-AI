# ==========================================
# models/emergency.py
# ==========================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    TIMESTAMP
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class Emergency(Base):

    __tablename__ = "emergencies"

    emergency_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.vehicle_id"),
        nullable=True
    )

    emergency_type = Column(
        String(100),
        nullable=False
    )

    description = Column(
        String(500),
        nullable=True
    )

    location_lat = Column(
        Float,
        nullable=False
    )

    location_lng = Column(
        Float,
        nullable=False
    )

    status = Column(
        String(30),
        default="Pending"
    )

    priority = Column(
        String(20),
        default="Medium"
    )

    recommended_service = Column(
        String(100),
        nullable=True
    )

    created_at = Column(
        TIMESTAMP,
        server_default=func.now()
    )

    resolved_at = Column(
        TIMESTAMP,
        nullable=True
    )

    # ==========================================
    # USER RELATIONSHIP
    # ==========================================

    user = relationship(
        "User",
        back_populates="emergencies"
    )

    # ==========================================
    # VEHICLE RELATIONSHIP
    # ==========================================

    vehicle = relationship(
        "Vehicle",
        back_populates="emergencies"
    )

    # ==========================================
    # SERVICE REQUEST RELATIONSHIP
    # ==========================================

    service_requests = relationship(
        "ServiceRequest",
        back_populates="emergency"
    )

    # ==========================================
    # NOTIFICATION RELATIONSHIP
    # ==========================================

    notifications = relationship(
        "Notification",
        back_populates="emergency"
    )