from sqlalchemy.orm import Session

from models.provider_location import ProviderLocation


# ==========================================
# SAVE OR UPDATE PROVIDER LOCATION
# ==========================================

def update_provider_location(
    db: Session,
    provider_id: int,
    latitude: float,
    longitude: float
):

    location = db.query(
        ProviderLocation
    ).filter(
        ProviderLocation.provider_id == provider_id
    ).first()

    if location:

        location.latitude = latitude
        location.longitude = longitude

    else:

        location = ProviderLocation(

            provider_id=provider_id,

            latitude=latitude,

            longitude=longitude
        )

        db.add(location)

    db.commit()

    db.refresh(location)

    return location


# ==========================================
# GET PROVIDER LOCATION
# ==========================================

def get_provider_location(
    db: Session,
    provider_id: int
):

    return db.query(
        ProviderLocation
    ).filter(
        ProviderLocation.provider_id == provider_id
    ).first()


# ==========================================
# GET ALL PROVIDER LOCATIONS
# ==========================================

def get_all_provider_locations(
    db: Session
):

    return db.query(
        ProviderLocation
    ).all()
