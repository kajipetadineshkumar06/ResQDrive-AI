# ==========================================
# models/service_provider.py
# ==========================================

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from database import Base


class ServiceProvider(Base):

    __tablename__ = "service_providers"

    # ==========================================
    # PRIMARY KEY
    # ==========================================

    provider_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # ==========================================
    # BASIC INFORMATION
    # ==========================================

    name = Column(
        String(100),
        nullable=False
    )

    service_type = Column(
        String(50),
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=False
    )

    # ==========================================
    # LOCATION
    # ==========================================

    location_lat = Column(
        Numeric(10, 7),
        nullable=True
    )

    location_lng = Column(
        Numeric(10, 7),
        nullable=True
    )

    # ==========================================
    # RATING
    # ==========================================

    rating_avg = Column(
        Numeric(3, 2),
        default=0.00,
        nullable=False
    )

    # ==========================================
    # AVAILABILITY
    # ==========================================

    is_available = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # ==========================================
    # PROVIDER DETAILS
    # ==========================================

    provider_image = Column(
        String(255),
        nullable=True
    )

    experience_years = Column(
        Integer,
        nullable=True
    )

    verified = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ==========================================
    # CREATED TIME
    # ==========================================

    created_at = Column(
        DateTime,
        nullable=True
    )

    # ==========================================
    # TRACKING
    # ==========================================

    is_tracking = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # ==========================================
    # USER RELATIONSHIP
    # ==========================================

    user_id = Column(
        Integer,
        ForeignKey(
            "users.user_id",
            name="fk_provider_user"
        ),
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="service_provider"
    )

    # ==========================================
    # SERVICE REQUEST RELATIONSHIP
    # ==========================================

    service_requests = relationship(
        "ServiceRequest",
        back_populates="provider"
    )

    # ==========================================
    # NOTIFICATION RELATIONSHIP
    # ==========================================

    notifications = relationship(
        "Notification",
        back_populates="provider"
    )