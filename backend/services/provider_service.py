from sqlalchemy.orm import Session

from models.service_provider import ServiceProvider


# ==========================================
# MARK PROVIDER BUSY
# ==========================================

def mark_provider_busy(
    db: Session,
    provider_id: int
):

    provider = db.query(
        ServiceProvider
    ).filter(
        ServiceProvider.provider_id == provider_id
    ).first()

    if provider:

        provider.is_available = 0

        db.commit()

        db.refresh(provider)

    return provider


# ==========================================
# MARK PROVIDER AVAILABLE
# ==========================================

def mark_provider_available(
    db: Session,
    provider_id: int
):

    provider = db.query(
        ServiceProvider
    ).filter(
        ServiceProvider.provider_id == provider_id
    ).first()

    if provider:

        provider.is_available = 1

        db.commit()

        db.refresh(provider)

    return provider


# ==========================================
# GET PROVIDER STATUS
# ==========================================

def get_provider_status(
    db: Session,
    provider_id: int
):

    return db.query(
        ServiceProvider
    ).filter(
        ServiceProvider.provider_id == provider_id
    ).first()