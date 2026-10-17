from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class FCMToken(Base):

    __tablename__ = "fcm_tokens"

    token_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
        unique=True
    )

    token = Column(
        String(500),
        nullable=False,
        unique=True
    )

    user = relationship(
        "User",
        back_populates="fcm_token"
    )