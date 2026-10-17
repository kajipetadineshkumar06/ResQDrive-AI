# =========================================================
# routers/provider_dashboard.py
# ResQDrive AI - Provider Dashboard
# =========================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth.oauth2 import get_current_user

from models.models import User
from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.emergency import Emergency

from services.assignment_service import (
    accept_request,
    reject_request,
)

from services.timeout_service import db_now
from services.agent_event_service import record_agent_event
from services.ai_eta_prediction_service import reset_provider_eta


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    tags=["Provider Dashboard"]
)


# =========================================================
# COMMON HELPER
# =========================================================

def get_logged_in_provider(
    db: Session,
    current_user: User,
):
    """
    Find the ServiceProvider profile connected
    to the currently logged-in user.
    """

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.user_id
            == current_user.user_id
        )
        .first()
    )

    if provider is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "No provider profile is linked "
                "to your account."
            ),
        )

    return provider


# =========================================================
# PROVIDER REQUESTS
# GET /provider/requests
#
# This is the endpoint used by the React
# ProviderDashboard.tsx
# =========================================================

@router.get(
    "/provider/requests"
)
def get_provider_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all service requests assigned to
    the currently logged-in provider.
    """

    provider = get_logged_in_provider(
        db,
        current_user,
    )

    requests = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.provider_id
            == provider.provider_id
        )
        .order_by(
            ServiceRequest.requested_at.desc()
        )
        .all()
    )

    result = []

    for request in requests:

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.emergency_id
                == request.emergency_id
            )
            .first()
        )

        if emergency is None:
            continue

        result.append(
            {
                # -----------------------------------------
                # REQUEST
                # -----------------------------------------

                "request_id":
                    request.request_id,

                "emergency_id":
                    request.emergency_id,

                "provider_id":
                    request.provider_id,

                "user_id":
                    request.user_id,

                "request_status":
                    request.request_status,

                "estimated_arrival":
                    request.estimated_arrival,

                "notes":
                    request.notes,

                "requested_at":
                    request.requested_at,

                "accepted_at":
                    request.accepted_at,

                "started_at":
                    request.started_at,

                "arrived_at":
                    request.arrived_at,

                "completed_at":
                    request.completed_at,

                "cancelled_at":
                    request.cancelled_at,

                # -----------------------------------------
                # EMERGENCY
                # -----------------------------------------

                "emergency_type":
                    emergency.emergency_type,

                "description":
                    emergency.description,

                "priority":
                    emergency.priority,

                "location_lat":
                    float(
                        emergency.location_lat
                    )
                    if emergency.location_lat
                    is not None
                    else None,

                "location_lng":
                    float(
                        emergency.location_lng
                    )
                    if emergency.location_lng
                    is not None
                    else None,

                "emergency_status":
                    emergency.status,

                # -----------------------------------------
                # PROVIDER
                # -----------------------------------------

                "provider_name":
                    provider.name,

                "provider_service_type":
                    provider.service_type,

                "provider_phone":
                    provider.phone,

                "provider_rating":
                    float(provider.rating_avg)
                    if provider.rating_avg
                    is not None
                    else 0,

                "provider_verified":
                    bool(provider.verified),

                "provider_available":
                    bool(provider.is_available),

                "provider_tracking":
                    bool(provider.is_tracking),
            }
        )

    return result


# =========================================================
# PROVIDER PROFILE
# GET /provider/profile
# =========================================================

@router.get(
    "/provider/profile"
)
def get_provider_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return provider information for the
    logged-in provider.
    """

    provider = get_logged_in_provider(
        db,
        current_user,
    )

    return {
        "provider_id":
            provider.provider_id,

        "user_id":
            provider.user_id,

        "name":
            provider.name,

        "service_type":
            provider.service_type,

        "phone":
            provider.phone,

        "location_lat":
            float(provider.location_lat)
            if provider.location_lat is not None
            else None,

        "location_lng":
            float(provider.location_lng)
            if provider.location_lng is not None
            else None,

        "rating_avg":
            float(provider.rating_avg)
            if provider.rating_avg is not None
            else 0,

        "is_available":
            bool(provider.is_available),

        "is_tracking":
            bool(provider.is_tracking),

        "verified":
            bool(provider.verified),

        "experience_years":
            provider.experience_years,

        "provider_image":
            provider.provider_image,
    }


# =========================================================
# LEGACY PROVIDER DASHBOARD ENDPOINT
# GET /provider-dashboard/{provider_id}
#
# Kept so existing backend functionality does not break.
# =========================================================

@router.get(
    "/provider-dashboard/{provider_id}"
)
def get_jobs(
    provider_id: int,
    db: Session = Depends(get_db),
):
    """
    Legacy provider dashboard endpoint.
    """

    requests = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.provider_id
            == provider_id
        )
        .order_by(
            ServiceRequest.requested_at.desc()
        )
        .all()
    )

    result = []

    for request in requests:

        emergency = (
            db.query(Emergency)
            .filter(
                Emergency.emergency_id
                == request.emergency_id
            )
            .first()
        )

        if emergency is None:
            continue

        result.append(
            {
                "request_id":
                    request.request_id,

                "emergency_id":
                    emergency.emergency_id,

                "customer_id":
                    emergency.user_id,

                "emergency_type":
                    emergency.emergency_type,

                "description":
                    emergency.description,

                "priority":
                    emergency.priority,

                "latitude":
                    float(
                        emergency.location_lat
                    ),

                "longitude":
                    float(
                        emergency.location_lng
                    ),

                "status":
                    request.request_status,
            }
        )

    return {
        "count":
            len(result),

        "jobs":
            result,
    }


# =========================================================
# LEGACY STATUS UPDATE
# PUT /provider-dashboard/status/{request_id}
#
# Kept for compatibility.
# =========================================================

@router.put(
    "/provider-dashboard/status/{request_id}"
)
def update_status(
    request_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Legacy status endpoint.

    The newer ProviderDashboard frontend should use
    provider_actions.py endpoints instead.
    """

    provider = get_logged_in_provider(
        db,
        current_user,
    )

    request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request_id,
            ServiceRequest.provider_id
            == provider.provider_id,
        )
        .first()
    )

    if request is None:
        raise HTTPException(
            status_code=404,
            detail="Service request not found",
        )

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id
        )
        .first()
    )

    if emergency is None:
        raise HTTPException(
            status_code=404,
            detail="Emergency not found",
        )

    new_status = (
        str(data.get("status", ""))
        .strip()
        .lower()
    )

    if not new_status:
        raise HTTPException(
            status_code=400,
            detail="Status is required",
        )

    # =====================================================
    # ACCEPT
    # =====================================================

    if new_status == "accepted":

        if not provider.verified:
            raise HTTPException(
                status_code=409,
                detail="Provider verification is required before accepting requests.",
            )

        accepted_request = accept_request(
            db=db,
            request=request,
        )

        return {
            "message":
                "Request Accepted",

            "request_id":
                accepted_request.request_id,

            "status":
                accepted_request.request_status,

            "provider_id":
                accepted_request.provider_id,
        }

    # =====================================================
    # REJECT
    # =====================================================

    if new_status == "rejected":

        old_provider_id = (
            request.provider_id
        )

        new_request = reject_request(
            db=db,
            request=request,
            emergency=emergency,
            reason="provider_rejected",
            actor_user_id=current_user.user_id,
        )

        if new_request is None:

            return {
                "message":
                    "No alternate provider available",

                "request_id":
                    request.request_id,

                "provider_id":
                    None,

                "status":
                    "pending",
            }

        return {
            "message":
                "Request reassigned",

            "request_id":
                new_request.request_id,

            "old_provider_id":
                old_provider_id,

            "provider_id":
                new_request.provider_id,

            "status":
                new_request.request_status,
        }

    # =====================================================
    # START / ON THE WAY
    # =====================================================

    if new_status in {
        "on_the_way",
        "started",
    }:

        if request.request_status != "accepted":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Request must be accepted "
                    "before starting service."
                ),
            )

        reset_provider_eta(provider.provider_id)
        request.request_status = "on_the_way"

        if request.started_at is None:
            request.started_at = db_now()

        provider.is_available = False
        provider.is_tracking = True

        emergency.status = "in_progress"

    # =====================================================
    # ARRIVED
    # =====================================================

    elif new_status == "arrived":

        if request.request_status not in {
            "on_the_way",
            "started",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provider must start the service "
                    "before marking arrived."
                ),
            )

        request.request_status = "arrived"

        if request.arrived_at is None:
            request.arrived_at = db_now()

        provider.is_tracking = False

        emergency.status = "in_progress"

    # =====================================================
    # SERVICE STARTED
    # =====================================================

    elif new_status == "in_progress":

        if request.request_status != "arrived":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provider must arrive before "
                    "starting service."
                ),
            )

        request.request_status = "in_progress"
        emergency.status = "in_progress"
        record_agent_event(
            db,
            "service_started",
            emergency_id=request.emergency_id,
            request_id=request.request_id,
            actor_user_id=current_user.user_id,
            provider_id=provider.provider_id,
        )

    # =====================================================
    # COMPLETED
    # =====================================================

    elif new_status == "completed":

        if request.request_status != "in_progress":
            raise HTTPException(
                status_code=400,
                detail=(
                "Request cannot be completed "
                "until service is in progress."
                ),
            )

        request.request_status = "completed"

        if request.completed_at is None:
            request.completed_at = db_now()

        provider.is_available = True
        provider.is_tracking = False

        emergency.status = "resolved"
        emergency.resolved_at = request.completed_at

    # =====================================================
    # CANCELLED
    # =====================================================

    elif new_status == "cancelled":

        if request.request_status == "completed":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Completed request cannot "
                    "be cancelled."
                ),
            )

        request.request_status = "cancelled"

        if request.cancelled_at is None:
            request.cancelled_at = db_now()

        provider.is_available = True
        provider.is_tracking = False

        emergency.status = "cancelled"

    # =====================================================
    # INVALID
    # =====================================================

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Allowed statuses: "
                "accepted, rejected, on_the_way, "
                "started, arrived, in_progress, completed, "
                "cancelled"
            ),
        )

    try:

        db.commit()

        db.refresh(request)
        db.refresh(provider)
        db.refresh(emergency)

    except Exception as error:

        db.rollback()

        print(
            "Provider dashboard status error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to update request status",
        )

    return {
        "message":
            "Status Updated",

        "request_id":
            request.request_id,

        "status":
            request.request_status,

        "provider_id":
            request.provider_id,
    }
