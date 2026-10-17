from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.emergency import Emergency
from schemas.history import HistoryResponse

router = APIRouter(
    prefix="/history",
    tags=["Emergency History"]
)


@router.get("/{user_id}", response_model=list[HistoryResponse])
def get_history(
    user_id: int,
    db: Session = Depends(get_db)
):

    history = db.query(Emergency).filter(
        Emergency.user_id == user_id
    ).order_by(
        Emergency.emergency_id.desc()
    ).all()

    if not history:
        raise HTTPException(
            status_code=404,
            detail="No emergency history found."
        )

    return history