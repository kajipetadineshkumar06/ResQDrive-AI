# ==========================================
# routers/providers.py
# ==========================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from database import get_db
from auth.oauth2 import get_current_user
from models.user import User

from models.service_provider import ServiceProvider

from schemas.service_provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
)


router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


# ==========================================
# CREATE PROVIDER
# ==========================================

@router.post(
    "/",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider(
    provider: ProviderCreate,
    db: Session = Depends(get_db),
):

    # --------------------------------------
    # Check duplicate phone
    # --------------------------------------

    existing = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.phone == provider.phone
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Provider with this phone already exists.",
        )

    # --------------------------------------
    # Create provider
    # --------------------------------------

    new_provider = ServiceProvider(

        name=provider.name,

        service_type=provider.service_type,

        phone=provider.phone,

        location_lat=provider.location_lat,

        location_lng=provider.location_lng,

        provider_image=provider.provider_image,

        experience_years=provider.experience_years,

        user_id=provider.user_id,

        rating_avg=0.00,

        is_available=True,

        verified=False,

        is_tracking=False,
    )

    # --------------------------------------
    # Save
    # --------------------------------------

    db.add(new_provider)

    try:

        db.commit()

        db.refresh(new_provider)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create provider.",
        )

    return new_provider


# ==========================================
# GET ALL PROVIDERS
# ==========================================

@router.get(
    "/",
    response_model=list[ProviderResponse],
)
def get_all_providers(
    db: Session = Depends(get_db),
):

    return (
        db.query(ServiceProvider)
        .filter(ServiceProvider.verified.is_(True))
        .order_by(
            ServiceProvider.rating_avg.desc()
        )
        .all()
    )


# ==========================================
# GET AVAILABLE PROVIDERS
# ==========================================

@router.get(
    "/available",
    response_model=list[ProviderResponse],
)
def get_available_providers(
    db: Session = Depends(get_db),
):

    return (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.is_available.is_(True),
            ServiceProvider.verified.is_(True),
        )
        .order_by(
            ServiceProvider.rating_avg.desc()
        )
        .all()
    )


# ==========================================
# GET PROVIDERS BY SERVICE TYPE
# ==========================================

@router.get(
    "/type/{service_type}",
    response_model=list[ProviderResponse],
)
def get_providers_by_type(
    service_type: str,
    db: Session = Depends(get_db),
):

    providers = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.service_type == service_type,
            ServiceProvider.is_available.is_(True),
            ServiceProvider.verified.is_(True),
        )
        .order_by(
            ServiceProvider.rating_avg.desc()
        )
        .all()
    )

    return providers


# ==========================================
# GET PROVIDER
# ==========================================

@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
):

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id == provider_id,
            ServiceProvider.verified.is_(True),
        )
        .first()
    )

    if provider is None:

        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    return provider


# ==========================================
# UPDATE PROVIDER
# ==========================================

@router.put(
    "/{provider_id}",
    response_model=ProviderResponse,
)
def update_provider(
    provider_id: int,
    provider: ProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    db_provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id == provider_id
        )
        .with_for_update()
        .first()
    )

    if db_provider is None:

        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    if db_provider.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own provider profile.",
        )

    # --------------------------------------
    # Update fields
    # --------------------------------------

    db_provider.name = provider.name

    db_provider.service_type = provider.service_type

    db_provider.phone = provider.phone

    db_provider.location_lat = provider.location_lat

    db_provider.location_lng = provider.location_lng

    db_provider.provider_image = (
        provider.provider_image
    )

    db_provider.experience_years = (
        provider.experience_years
    )

    # --------------------------------------
    # Save
    # --------------------------------------

    db.commit()

    db.refresh(db_provider)

    return db_provider


# ==========================================
# DELETE PROVIDER
# ==========================================

@router.delete(
    "/{provider_id}"
)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
):

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id == provider_id
        )
        .first()
    )

    if provider is None:

        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    db.delete(provider)

    db.commit()

    return {
        "message": "Provider deleted successfully"
    }
