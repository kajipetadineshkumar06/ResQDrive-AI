# ==========================================
# models/user.py
# ==========================================

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime
)

from sqlalchemy.orm import relationship

from database import Base


class User(Base):

    __tablename__ = "users"

    # ==========================================
    # USER ID
    # ==========================================

    user_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # ==========================================
    # FULL NAME
    # ==========================================

    full_name = Column(
        String(100),
        nullable=False
    )

    # ==========================================
    # EMAIL
    # ==========================================

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # ==========================================
    # PHONE
    # ==========================================

    phone = Column(
        String(20),
        nullable=True
    )

    # ==========================================
    # PASSWORD
    # ==========================================

    password_hash = Column(
        String(255),
        nullable=False
    )

    # ==========================================
    # CREATED AT
    # ==========================================

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # ==========================================
    # SERVICE PROVIDER RELATIONSHIP
    # ==========================================

    service_provider = relationship(
        "ServiceProvider",
        back_populates="user",
        uselist=False
    )

    # ==========================================
    # VEHICLE RELATIONSHIP
    # ==========================================

    vehicles = relationship(
        "Vehicle",
        back_populates="user"
    )

    # ==========================================
    # EMERGENCY RELATIONSHIP
    # ==========================================

    emergencies = relationship(
        "Emergency",
        back_populates="user"
    )

    # ==========================================
    # SERVICE REQUEST RELATIONSHIP
    # ==========================================

    service_requests = relationship(
        "ServiceRequest",
        back_populates="user"
    )

    # ==========================================
    # NOTIFICATION RELATIONSHIP
    # ==========================================

    notifications = relationship(
        "Notification",
        back_populates="user"
    )

    # ==========================================
    # FCM TOKEN RELATIONSHIP
    # ==========================================

    fcm_token = relationship(
        "FCMToken",
        back_populates="user",
        uselist=False
    )