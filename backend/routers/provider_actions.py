# ============================================================
# routers/provider_actions.py
# ResQDrive AI - Provider Actions
# ============================================================

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
from models.service_provider import ServiceProvider
from models.emergency import Emergency

from services.assignment_service import (
    release_provider_if_idle,
    reject_request,
)

from services.firebase_notification import (
    send_push_notification,
)
from services.agent_event_service import record_agent_event
from services.ai_eta_prediction_service import reset_provider_eta


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/provider",
    tags=["Provider Actions"],
)


# ============================================================
# TIMEZONE
# ============================================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


def db_now():
    """
    Return current India time as a naive datetime.

    The project database currently stores DateTime values
    without timezone information, so all application-side
    timestamps must use the same IST-naive format.
    """

    return datetime.now(
        INDIA_TIMEZONE
    ).replace(
        tzinfo=None
    )


# ============================================================
# HELPER
# ============================================================

def get_request_and_provider(
    request_id: int,
    db: Session,
    current_user: User,
):
    """
    Get the service request and verify that the currently
    logged-in user owns the assigned provider.
    """

    # --------------------------------------------------------
    # FIND REQUEST
    # --------------------------------------------------------

    request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request_id
        )
        .with_for_update()
        .first()
    )

    if request is None:

        raise HTTPException(
            status_code=404,
            detail="Request not found",
        )

    # --------------------------------------------------------
    # PROVIDER REQUIRED
    # --------------------------------------------------------

    if request.provider_id is None:

        raise HTTPException(
            status_code=400,
            detail="No provider is assigned",
        )

    # --------------------------------------------------------
    # FIND PROVIDER
    # --------------------------------------------------------

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id
            == request.provider_id
        )
        .first()
    )

    if provider is None:

        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    if provider.user_id != current_user.user_id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You are not the assigned "
                "provider for this request"
            ),
        )

    return request, provider


# ============================================================
# PROVIDER ACCEPT REQUEST
# ============================================================

@router.post(
    "/request/{request_id}/accept"
)
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provider accepts an assigned pending request.

    Flow:

        pending
           ↓
        accepted

    Once accepted, the timeout system will no longer
    reassign this request because the request is no longer
    in pending state.
    """

    # --------------------------------------------------------
    # GET REQUEST + PROVIDER
    # --------------------------------------------------------

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # ONLY PENDING REQUESTS CAN BE ACCEPTED
    # --------------------------------------------------------

    if request.request_status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                f"Request is already "
                f"{request.request_status}"
            ),
        )

    if not provider.verified:
        raise HTTPException(
            status_code=409,
            detail="Provider verification is required before accepting requests.",
        )

    # --------------------------------------------------------
    # ACCEPT
    # --------------------------------------------------------

    print(
        f"✅ Provider {provider.provider_id} "
        f"is accepting Request "
        f"{request.request_id}"
    )

    request.request_status = "accepted"

    # IMPORTANT:
    # Use IST instead of datetime.utcnow().
    request.accepted_at = db_now()

    # --------------------------------------------------------
    # PROVIDER BUSY
    # --------------------------------------------------------

    provider.is_available = False

    # --------------------------------------------------------
    # FIND EMERGENCY
    # --------------------------------------------------------

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id
        )
        .first()
    )

    # --------------------------------------------------------
    # UPDATE EMERGENCY
    # --------------------------------------------------------

    if emergency:

        emergency.status = "assigned"

    record_agent_event(
        db,
        "provider_accepted",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=current_user.user_id,
        provider_id=provider.provider_id,
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(request)

        db.refresh(provider)

        if emergency:

            db.refresh(emergency)

    except Exception as error:

        db.rollback()

        print(
            "❌ Accept request error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to accept request",
        )

    # --------------------------------------------------------
    # NOTIFY CUSTOMER
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Provider Accepted",
            body=(
                "Your provider has accepted "
                "your request."
            ),
            data={
                "request_id": str(
                    request.request_id
                ),
                "type": "provider_accepted",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Request Accepted",
        "request_id": request.request_id,
        "provider_id": provider.provider_id,
        "request_status": request.request_status,
        "accepted_at": request.accepted_at,
    }


# ============================================================
# PROVIDER REJECT REQUEST
# ============================================================

@router.post(
    "/request/{request_id}/reject"
)
def reject_provider_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provider manually rejects an assigned request.

    Flow:

        pending
           ↓
       provider rejects
           ↓
       old provider excluded
           ↓
       old provider released
           ↓
       nearest eligible provider selected
           ↓
       new provider receives request
           ↓
       new 30-second timeout starts

    If no provider is available:

        provider_id = None
        status = pending

    The customer request is NOT permanently cancelled
    simply because one provider rejected it.
    """

    # --------------------------------------------------------
    # GET REQUEST + PROVIDER
    # --------------------------------------------------------

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # ONLY PENDING REQUESTS CAN BE REJECTED
    # --------------------------------------------------------

    if request.request_status != "pending":

        raise HTTPException(
            status_code=400,
            detail=(
                "Only pending requests "
                "can be rejected."
            ),
        )

    old_provider_id = provider.provider_id

    print(
        f"🚫 Provider {old_provider_id} "
        f"is rejecting Request "
        f"{request.request_id}"
    )

    # --------------------------------------------------------
    # FIND EMERGENCY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # AUTOMATIC REASSIGNMENT
    # --------------------------------------------------------

    try:

        new_request = reject_request(
            db=db,
            request=request,
            emergency=emergency,
            reason="provider_rejected",
            actor_user_id=current_user.user_id,
        )

    except Exception as error:

        db.rollback()

        print(
            "❌ Reject/reassignment error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to reject and "
                "reassign request"
            ),
        )

    # --------------------------------------------------------
    # NO ALTERNATE PROVIDER
    # --------------------------------------------------------

    if new_request is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Request rejection could "
                "not be processed"
            ),
        )

    # --------------------------------------------------------
    # GET NEW PROVIDER
    # --------------------------------------------------------

    new_provider_id = (
        new_request.provider_id
    )

    # --------------------------------------------------------
    # NO PROVIDER AVAILABLE
    # --------------------------------------------------------

    if new_provider_id is None:

        try:

            send_push_notification(
                db=db,
                user_id=request.user_id,
                title="Finding Another Provider",
                body=(
                    "Your previous provider "
                    "was unavailable. "
                    "ResQDrive AI is finding "
                    "another provider."
                ),
                data={
                    "request_id": str(
                        request.request_id
                    ),
                    "type": "provider_rejected",
                },
            )

        except Exception as error:

            print(
                "⚠️ Customer notification error:",
                error,
            )

        print(
            f"⏳ Request "
            f"{request.request_id} "
            f"is waiting for another provider."
        )

        return {
            "message": (
                "Provider rejected. "
                "Request is waiting for "
                "another provider."
            ),
            "request_id": request.request_id,
            "old_provider_id": old_provider_id,
            "provider_id": None,
            "request_status": "pending",
        }

    # --------------------------------------------------------
    # SUCCESSFULLY REASSIGNED
    # --------------------------------------------------------

    print(
        f"🔄 Request "
        f"{request.request_id} "
        f"reassigned from Provider "
        f"{old_provider_id} "
        f"to Provider "
        f"{new_provider_id}"
    )

    # --------------------------------------------------------
    # CUSTOMER NOTIFICATION
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Finding Another Provider",
            body=(
                "Your previous provider "
                "was unavailable. "
                "A new provider has been "
                "assigned to your request."
            ),
            data={
                "request_id": str(
                    request.request_id
                ),
                "provider_id": str(
                    new_provider_id
                ),
                "type": "provider_reassigned",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": (
            "Request reassigned "
            "to next provider"
        ),
        "request_id": request.request_id,
        "old_provider_id": old_provider_id,
        "provider_id": new_provider_id,
        "request_status": (
            new_request.request_status
        ),
    }


# ============================================================
# PROVIDER START TRIP
# ============================================================

@router.post(
    "/request/{request_id}/start"
)
def start_trip(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provider starts travelling to customer.

    accepted
       ↓
    on_the_way
    """

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # ONLY ACCEPTED REQUEST CAN START
    # --------------------------------------------------------

    if request.request_status != "accepted":

        raise HTTPException(
            status_code=400,
            detail=(
                "Request must be accepted "
                "before starting"
            ),
        )

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    # Adaptive speed samples belong to one trip; do not carry them over.
    reset_provider_eta(provider.provider_id)

    request.request_status = "on_the_way"

    request.started_at = db_now()

    record_agent_event(
        db,
        "provider_started_trip",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=current_user.user_id,
        provider_id=provider.provider_id,
    )

    # --------------------------------------------------------
    # ENABLE LIVE GPS TRACKING
    # --------------------------------------------------------
    # Start Trip must activate provider tracking. The secure
    # provider-location endpoint checks this flag before
    # accepting GPS updates.
    provider.is_tracking = True

    # --------------------------------------------------------
    # EMERGENCY
    # --------------------------------------------------------

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id
        )
        .first()
    )

    if emergency:

        emergency.status = "in_progress"

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(request)

        if emergency:

            db.refresh(emergency)

    except Exception as error:

        db.rollback()

        print(
            "❌ Start trip error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to start trip",
        )

    # --------------------------------------------------------
    # CUSTOMER NOTIFICATION
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Provider Started",
            body="Provider is on the way.",
            data={
                "request_id": str(
                    request.request_id
                ),
                "type": "provider_started",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Trip Started",
        "request_id": request.request_id,
        "request_status": request.request_status,
        "started_at": request.started_at,
    }


# ============================================================
# PROVIDER ARRIVED
# ============================================================

@router.post(
    "/request/{request_id}/arrived"
)
def arrived(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provider has arrived at customer's location.

    on_the_way
         ↓
       arrived
    """

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # ONLY ON_THE_WAY CAN ARRIVE
    # --------------------------------------------------------

    if request.request_status != "on_the_way":

        raise HTTPException(
            status_code=400,
            detail=(
                "Provider must start "
                "the trip first"
            ),
        )

    # --------------------------------------------------------
    # ARRIVED
    # --------------------------------------------------------

    request.request_status = "arrived"

    request.arrived_at = db_now()

    # Stop sending movement updates after reaching the customer.
    provider.is_tracking = False

    record_agent_event(
        db,
        "provider_arrived",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=current_user.user_id,
        provider_id=provider.provider_id,
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(request)

    except Exception as error:

        db.rollback()

        print(
            "❌ Arrived error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to mark provider "
                "as arrived"
            ),
        )

    # --------------------------------------------------------
    # CUSTOMER NOTIFICATION
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Provider Arrived",
            body="Your provider has arrived.",
            data={
                "request_id": str(
                    request.request_id
                ),
                "type": "provider_arrived",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Provider Arrived",
        "request_id": request.request_id,
        "request_status": request.request_status,
        "arrived_at": request.arrived_at,
    }


# ============================================================
# COMPLETE SERVICE REQUEST
# ============================================================

@router.post(
    "/request/{request_id}/start-service"
)
def start_service(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record the provider beginning work after arrival."""
    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    if request.request_status != "arrived":
        raise HTTPException(
            status_code=400,
            detail="Provider must arrive before starting service",
        )

    request.request_status = "in_progress"
    record_agent_event(
        db,
        "service_started",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=current_user.user_id,
        provider_id=provider.provider_id,
    )

    try:
        db.commit()
        db.refresh(request)
    except Exception as error:
        db.rollback()
        print("Start service request failed.")
        raise HTTPException(
            status_code=500,
            detail="Failed to start service",
        )

    try:
        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Service Started",
            body="Your provider has started the service.",
            data={
                "request_id": str(request.request_id),
                "type": "service_started",
            },
        )
    except Exception as error:
        print("Customer notification failed.")

    return {
        "message": "Service Started",
        "request_id": request.request_id,
        "request_status": request.request_status,
    }


# ============================================================
# COMPLETE SERVICE REQUEST
# ============================================================

@router.post(
    "/request/{request_id}/complete"
)
def complete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Complete the roadside service.

    in_progress
       ↓
    completed
    """

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # SERVICE MUST HAVE STARTED BEFORE IT CAN COMPLETE
    # --------------------------------------------------------

    if request.request_status != "in_progress":

        raise HTTPException(
            status_code=400,
            detail=(
                "Service must be in progress before completion"
            ),
        )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    request.request_status = "completed"

    request.completed_at = db_now()

    record_agent_event(
        db,
        "service_completed",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=current_user.user_id,
        provider_id=provider.provider_id,
    )

    # --------------------------------------------------------
    # RELEASE ONLY WHEN THIS PROVIDER HAS NO OTHER ACTIVE REQUEST
    # --------------------------------------------------------

    release_provider_if_idle(
        db,
        provider.provider_id,
        excluding_request_id=request.request_id,
    )

    # --------------------------------------------------------
    # EMERGENCY
    # --------------------------------------------------------

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id
        )
        .first()
    )

    if emergency:

        emergency.status = "resolved"

        emergency.resolved_at = db_now()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(request)

        db.refresh(provider)

        if emergency:

            db.refresh(emergency)

    except Exception as error:

        db.rollback()

        print(
            "❌ Complete request error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to complete "
                "service request"
            ),
        )

    # --------------------------------------------------------
    # CUSTOMER NOTIFICATION
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Service Completed",
            body=(
                "Your roadside service "
                "has been completed."
            ),
            data={
                "request_id": str(
                    request.request_id
                ),
                "type": "service_completed",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Service Completed",
        "request_id": request.request_id,
        "request_status": request.request_status,
        "completed_at": request.completed_at,
    }


    # ============================================================
# PROVIDER CANCEL REQUEST
# ============================================================

@router.post(
    "/request/{request_id}/cancel"
)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provider cancels an active service request.

    Allowed flow:

        accepted
            ↓
        cancelled

        on_the_way
            ↓
        cancelled

        arrived
            ↓
        cancelled

    Once cancelled:

        - Request becomes cancelled
        - Provider becomes available again
        - Emergency becomes cancelled
        - Customer receives notification

    A completed request cannot be cancelled.
    """

    # --------------------------------------------------------
    # GET REQUEST + PROVIDER
    # --------------------------------------------------------

    request, provider = get_request_and_provider(
        request_id=request_id,
        db=db,
        current_user=current_user,
    )

    # --------------------------------------------------------
    # CHECK REQUEST STATUS
    # --------------------------------------------------------

    allowed_statuses = {
        "accepted",
        "on_the_way",
        "arrived",
    }

    if request.request_status not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only accepted, on_the_way, "
                "or arrived requests can be cancelled."
            ),
        )

    # --------------------------------------------------------
    # FIND EMERGENCY
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CURRENT STATUS
    # --------------------------------------------------------

    previous_status = request.request_status

    print(
        f"⚠️ Provider {provider.provider_id} "
        f"is cancelling Request "
        f"{request.request_id}"
    )

    # --------------------------------------------------------
    # CANCEL REQUEST
    # --------------------------------------------------------

    request.request_status = "cancelled"

    # --------------------------------------------------------
    # RELEASE ONLY WHEN THIS PROVIDER HAS NO OTHER ACTIVE REQUEST
    # --------------------------------------------------------

    release_provider_if_idle(
        db,
        provider.provider_id,
        excluding_request_id=request.request_id,
    )

    # --------------------------------------------------------
    # EMERGENCY CANCELLED
    # --------------------------------------------------------

    emergency.status = "cancelled"

    # --------------------------------------------------------
    # SAVE DATABASE
    # --------------------------------------------------------

    try:

        db.commit()

        db.refresh(request)

        db.refresh(provider)

        db.refresh(emergency)

    except Exception as error:

        db.rollback()

        print(
            "❌ Provider cancellation error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to cancel "
                "service request"
            ),
        )

    # --------------------------------------------------------
    # CUSTOMER NOTIFICATION
    # --------------------------------------------------------

    try:

        send_push_notification(
            db=db,
            user_id=request.user_id,
            title="Provider Cancelled",
            body=(
                "Your assigned provider "
                "cancelled the service request. "
                "ResQDrive AI will help find "
                "another provider."
            ),
            data={
                "request_id": str(
                    request.request_id
                ),
                "previous_status": str(
                    previous_status
                ),
                "type": "provider_cancelled",
            },
        )

    except Exception as error:

        print(
            "⚠️ Customer notification error:",
            error,
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "message": "Service Request Cancelled",
        "request_id": request.request_id,
        "provider_id": provider.provider_id,
        "previous_status": previous_status,
        "request_status": request.request_status,
        "provider_available": provider.is_available,
        "emergency_status": emergency.status,
    }
