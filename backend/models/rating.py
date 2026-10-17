from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP, func
from database import Base


class Rating(Base):
    __tablename__ = "ratings"

    rating_id = Column(Integer, primary_key=True, index=True)

    request_id = Column(Integer, ForeignKey("service_requests.request_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    provider_id = Column(Integer, ForeignKey("service_providers.provider_id"))

    rating_value = Column(Integer)
    review_text = Column(Text)

    created_at = Column(TIMESTAMP, server_default=func.now())