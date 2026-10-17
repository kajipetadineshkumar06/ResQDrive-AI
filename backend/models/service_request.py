# ==========================================
# models/service_request.py
# ==========================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    # ==========================================
    # REQUEST ID
    # ==========================================

    request_id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ==========================================
    # EMERGENCY ID
    # ==========================================

    emergency_id = Column(
        Integer,
        ForeignKey(
            "emergencies.emergency_id"
        ),
        nullable=False,
    )

    # ==========================================
    # PROVIDER ID
    # ==========================================

    provider_id = Column(
        Integer,
        ForeignKey(
            "service_providers.provider_id"
        ),
        nullable=True,
    )

    # ==========================================
    # EXCLUDED PROVIDERS
    #
    # MutableList makes SQLAlchemy persist:
    #
    # request.excluded_provider_ids.append(12)
    # ==========================================

    excluded_provider_ids = Column(
        MutableList.as_mutable(JSON),
        nullable=True,
        default=list,
    )

    # ==========================================
    # USER ID
    # ==========================================

    user_id = Column(
        Integer,
        ForeignKey(
            "users.user_id"
        ),
        nullable=False,
    )

    # ==========================================
    # REQUEST STATUS
    # ==========================================

    request_status = Column(
        String(50),
        nullable=False,
        default="pending",
    )

    # ==========================================
    # ESTIMATED ARRIVAL
    # ==========================================

    estimated_arrival = Column(
        Integer,
        nullable=True,
    )

    # ==========================================
    # NOTES
    # ==========================================

    notes = Column(
        String(500),
        nullable=True,
    )

    # ==========================================
    # REQUESTED AT
    # ==========================================

    requested_at = Column(
        DateTime,
        server_default=func.now(),
    )

    # ==========================================
    # ACCEPTED AT
    # ==========================================

    accepted_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================================
    # STARTED AT
    # ==========================================

    started_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================================
    # ARRIVED AT
    # ==========================================

    arrived_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================================
    # COMPLETED AT
    # ==========================================

    completed_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================================
    # CANCELLED AT
    # ==========================================

    cancelled_at = Column(
        DateTime,
        nullable=True,
    )

    # ==========================================
    # EMERGENCY RELATIONSHIP
    # ==========================================

    emergency = relationship(
        "Emergency",
        back_populates="service_requests",
    )

    # ==========================================
    # PROVIDER RELATIONSHIP
    # ==========================================

    provider = relationship(
        "ServiceProvider",
        back_populates="service_requests",
    )

    # ==========================================
    # USER RELATIONSHIP
    # ==========================================

    user = relationship(
        "User",
        back_populates="service_requests",
    )