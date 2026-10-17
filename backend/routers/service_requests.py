# ==========================================
# routers/service_requests.py
# ==========================================

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.service_request import ServiceRequest
from models.emergency import Emergency
from models.service_provider import ServiceProvider

from schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceRequestResponse,
)

router = APIRouter(
    prefix="/service-requests",
    tags=["Service Requests"],
)

TERMINAL_REQUEST_STATUSES = (
    "completed",
    "cancelled",
    "canceled",
    "rejected",
    "timeout",
    "timed_out",
)


# ======================================================
# TIMEZONE
# ======================================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


def utc_now():
    """
    Return current India time as a naive datetime.

    The project database currently stores DateTime values
    without timezone information, so application-side
    timestamps must use the same IST-naive format.
    """

    return datetime.now(
        INDIA_TIMEZONE
    ).replace(
        tzinfo=None
    )


# ======================================================
# CREATE SERVICE REQUEST
# ======================================================

@router.post(
    "/",
    response_model=ServiceRequestResponse,
)
def create_service_request(
    request: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ==========================================
    # CHECK EMERGENCY
    # ==========================================

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id,

            Emergency.user_id
            == current_user.user_id,
        )
        .first()
    )

    if not emergency:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found",
        )

    # ==========================================
    # CHECK PROVIDER
    # ==========================================

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id
            == request.provider_id,
        )
        .with_for_update()
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    if not provider.verified:
        raise HTTPException(
            status_code=409,
            detail="Provider is not verified and cannot be assigned.",
        )

    if not provider.is_available:
        raise HTTPException(
            status_code=409,
            detail="Provider is not available.",
        )

    active_request = (
        db.query(ServiceRequest.request_id)
        .filter(
            ServiceRequest.provider_id == provider.provider_id,
            ServiceRequest.request_status.notin_(TERMINAL_REQUEST_STATUSES),
        )
        .with_for_update()
        .first()
    )
    if active_request is not None:
        raise HTTPException(
            status_code=409,
            detail="Provider already has an active service request.",
        )

    # ==========================================
    # CREATE SERVICE REQUEST
    # ==========================================

    new_request = ServiceRequest(
        emergency_id=request.emergency_id,

        provider_id=request.provider_id,

        user_id=current_user.user_id,

        request_status="pending",

        requested_at=utc_now(),

        estimated_arrival=(
            request.estimated_arrival
        ),

        notes=request.notes,
    )

    # Reserve the provider in the same transaction as the pending offer.
    provider.is_available = False

    # ==========================================
    # SAVE
    # ==========================================

    try:

        db.add(new_request)

        db.commit()

        db.refresh(new_request)

    except Exception as error:

        db.rollback()

        print(
            "Create service request error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to create service request",
        )

    return new_request


# ======================================================
# GET MY SERVICE REQUESTS
# ======================================================

@router.get(
    "/",
    response_model=list[ServiceRequestResponse],
)
def get_my_service_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requests = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.user_id
            == current_user.user_id,
        )
        .order_by(
            ServiceRequest.requested_at.desc()
        )
        .all()
    )

    return requests


# ======================================================
# GET SINGLE SERVICE REQUEST
# ======================================================

@router.get(
    "/{request_id}",
    response_model=ServiceRequestResponse,
)
def get_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request_id,

            ServiceRequest.user_id
            == current_user.user_id,
        )
        .first()
    )

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Service request not found",
        )

    return request


# ======================================================
# UPDATE SERVICE REQUEST DETAILS
# ======================================================
#
# IMPORTANT:
#
# Customer is NOT allowed to change request_status.
#
# Provider lifecycle is controlled by:
#
# /provider/request/{id}/accept
# /provider/request/{id}/start
# /provider/request/{id}/arrived
# /provider/request/{id}/complete
#
# This endpoint only updates:
#
# estimated_arrival
# notes
#
# ======================================================

@router.put(
    "/{request_id}",
    response_model=ServiceRequestResponse,
)
def update_service_request(
    request_id: int,
    request: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request_id,

            ServiceRequest.user_id
            == current_user.user_id,
        )
        .first()
    )

    if not db_request:

        raise HTTPException(
            status_code=404,
            detail="Service request not found",
        )

    # ==========================================
    # FINAL STATUS PROTECTION
    # ==========================================

    if db_request.request_status in {
        "completed",
        "cancelled",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot update a "
                f"{db_request.request_status} "
                f"service request"
            ),
        )

    # ==========================================
    # CUSTOMER CANNOT CHANGE STATUS
    # ==========================================

    if (
        request.request_status is not None
        and request.request_status
        != db_request.request_status
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Customers cannot change "
                "the service request status"
            ),
        )

    # ==========================================
    # UPDATE DETAILS ONLY
    # ==========================================

    if request.estimated_arrival is not None:

        db_request.estimated_arrival = (
            request.estimated_arrival
        )

    if request.notes is not None:

        db_request.notes = request.notes

    # ==========================================
    # SAVE
    # ==========================================

    try:

        db.commit()

        db.refresh(db_request)

    except Exception as error:

        db.rollback()

        print(
            "Update service request error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to update service request",
        )

    return db_request


# ======================================================
# CANCEL SERVICE REQUEST
# ======================================================

@router.delete(
    "/{request_id}",
)
def cancel_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request_id,

            ServiceRequest.user_id
            == current_user.user_id,
        )
        .first()
    )

    if not request:

        raise HTTPException(
            status_code=404,
            detail="Service request not found",
        )

    # ==========================================
    # COMPLETED
    # ==========================================

    if request.request_status == "completed":

        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot cancel a completed "
                "service request"
            ),
        )

    # ==========================================
    # ALREADY CANCELLED
    # ==========================================

    if request.request_status == "cancelled":

        raise HTTPException(
            status_code=400,
            detail=(
                "Service request is already "
                "cancelled"
            ),
        )

    # ==========================================
    # CANCEL
    # ==========================================

    request.request_status = "cancelled"

    request.cancelled_at = utc_now()

    # ==========================================
    # MAKE PROVIDER AVAILABLE
    # ==========================================

    if request.provider_id is not None:

        provider = (
            db.query(ServiceProvider)
            .filter(
                ServiceProvider.provider_id
                == request.provider_id,
            )
            .first()
        )

        if provider:

            provider.is_available = True

    # ==========================================
    # UPDATE EMERGENCY
    # ==========================================

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id,
        )
        .first()
    )

    if emergency:

        emergency.status = "cancelled"

    # ==========================================
    # SAVE
    # ==========================================

    try:

        db.commit()

        db.refresh(request)

    except Exception as error:

        db.rollback()

        print(
            "Cancel service request error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to cancel service request",
        )

    # ==========================================
    # RESPONSE
    # ==========================================

    return {
        "message":
            "Service request cancelled successfully",

        "request_id":
            request.request_id,

        "request_status":
            request.request_status,

        "cancelled_at":
            request.cancelled_at,
    }
