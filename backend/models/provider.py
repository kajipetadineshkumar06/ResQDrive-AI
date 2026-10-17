from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP
from sqlalchemy.sql import func

from database import Base


class Provider(Base):

    __tablename__ = "providers"

    provider_id = Column(Integer, primary_key=True, index=True)

    provider_name = Column(String(100), nullable=False)

    service_type = Column(String(50), nullable=False)

    phone = Column(String(15), nullable=False)

    email = Column(String(100))

    latitude = Column(DECIMAL(10, 7), nullable=False)

    longitude = Column(DECIMAL(10, 7), nullable=False)

    city = Column(String(100))

    rating = Column(DECIMAL(2, 1), default=5.0)

    availability = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now())