from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from database import get_db

from models.models import User

from schemas.schemas import UserResponse


router = APIRouter(
    tags=["Users"]
)


# =========================================================
# GET ALL USERS
# =========================================================

@router.get(
    "/users",
    response_model=list[UserResponse]
)
def get_users(
    db: Session = Depends(get_db)
):

    return db.query(User).all()