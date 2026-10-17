from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.service_provider import ServiceProvider

router = APIRouter(
    prefix="/provider-tracking",
    tags=["Provider Tracking"]
)


@router.put("/start/{provider_id}")
def start_tracking(
    provider_id: int,
    db: Session = Depends(get_db)
):

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == provider_id
    ).first()

    if not provider:

        return {
            "message": "Provider not found"
        }

    provider.is_tracking = 1

    db.commit()

    return {
        "message": "Tracking Started"
    }


@router.put("/stop/{provider_id}")
def stop_tracking(
    provider_id: int,
    db: Session = Depends(get_db)
):

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == provider_id
    ).first()

    if not provider:

        return {
            "message": "Provider not found"
        }

    provider.is_tracking = 0

    db.commit()

    return {
        "message": "Tracking Stopped"
    }


@router.get("/{provider_id}")
def tracking_status(
    provider_id: int,
    db: Session = Depends(get_db)
):

    provider = db.query(ServiceProvider).filter(
        ServiceProvider.provider_id == provider_id
    ).first()

    if not provider:

        return {
            "message": "Provider not found"
        }

    return {
        "provider_id": provider.provider_id,
        "tracking": bool(provider.is_tracking)
    }