from pydantic import BaseModel
from typing import Optional


class RatingCreate(BaseModel):
    request_id: int
    user_id: int
    provider_id: int
    rating_value: int
    review_text: Optional[str] = None


class RatingResponse(BaseModel):
    rating_id: int
    request_id: int
    user_id: int
    provider_id: int
    rating_value: int
    review_text: Optional[str] = None

    class Config:
        from_attributes = True