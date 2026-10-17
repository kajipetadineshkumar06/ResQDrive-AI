from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DECIMAL,
    TIMESTAMP
)

from sqlalchemy.sql import func

from database import Base


class ProviderLocation(Base):

    __tablename__ = "provider_locations"

    location_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    provider_id = Column(
        Integer,
        ForeignKey("service_providers.provider_id"),
        nullable=False
    )

    latitude = Column(
        DECIMAL(10, 7),
        nullable=False
    )

    longitude = Column(
        DECIMAL(10, 7),
        nullable=False
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )