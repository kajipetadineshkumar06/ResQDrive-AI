from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    text,
)

from sqlalchemy.orm import relationship

from database import Base


class Notification(Base):

    __tablename__ = "notifications"

    notification_id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
    )

    emergency_id = Column(
        Integer,
        ForeignKey("emergencies.emergency_id"),
        nullable=True,
    )

    provider_id = Column(
        Integer,
        ForeignKey("service_providers.provider_id"),
        nullable=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    message = Column(
        String(500),
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
        default="sent",
        server_default=text("'sent'"),
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = relationship(
        "User",
        back_populates="notifications",
    )

    provider = relationship(
        "ServiceProvider",
        back_populates="notifications",
    )

    emergency = relationship(
        "Emergency",
        back_populates="notifications",
    )