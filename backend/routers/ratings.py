from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.rating import Rating
from schemas.rating import RatingCreate, RatingResponse

router = APIRouter(
    prefix="/ratings",
    tags=["Ratings"]
)


# Add Rating
@router.post("/", response_model=RatingResponse)
def add_rating(
    rating: RatingCreate,
    db: Session = Depends(get_db)
):

    new_rating = Rating(
        request_id=rating.request_id,
        user_id=rating.user_id,
        provider_id=rating.provider_id,
        rating_value=rating.rating_value,
        review_text=rating.review_text
    )

    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)

    return new_rating


# Get Ratings of a Provider
@router.get("/provider/{provider_id}")
def get_provider_ratings(
    provider_id: int,
    db: Session = Depends(get_db)
):

    ratings = db.query(Rating).filter(
        Rating.provider_id == provider_id
    ).all()

    if not ratings:
        raise HTTPException(
            status_code=404,
            detail="No ratings found for this provider"
        )

    return ratings