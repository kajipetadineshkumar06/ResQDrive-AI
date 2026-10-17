from sqlalchemy import Column, Integer, DECIMAL, Enum, ForeignKey
from database import Base


class SOSAlert(Base):

    __tablename__ = "sos_alerts"

    alert_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False
    )

    latitude = Column(
        DECIMAL(10,7),
        nullable=False
    )

    longitude = Column(
        DECIMAL(10,7),
        nullable=False
    )

    status = Column(
        Enum(
            "sent",
            "received",
            "acknowledged"
        ),
        default="sent"
    )