# ============================================================
# routers/agent_assistance.py
# ResQDrive AI
#
# Agentic Emergency Assistance API
#
# Flow:
#
# Customer Emergency
#       ↓
# AI Orchestrator
#       ↓
# Provider Selection
#       ↓
# Google Route
#       ↓
# AI ETA
#       ↓
# Service Request Creation
#       ↓
# Provider Accepts
#       ↓
# Existing Provider Lifecycle
# ============================================================


from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict


from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)


from sqlalchemy.orm import Session


from database import get_db


from auth.oauth2 import get_current_user


from models.models import User
from models.emergency import Emergency
from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.notification import Notification
from models.agent_event import AgentEvent
from services.firebase_notification import send_push_notification
from services.agent_event_service import record_agent_event


from agents.orchestrator import create_orchestrator


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/agent",
    tags=["AI Agent Assistance"],
)


# ============================================================
# TIMEZONE
# ============================================================

INDIA_TIMEZONE = ZoneInfo(
    "Asia/Kolkata"
)


def db_now() -> datetime:
    """
    Return current India time as a naive datetime.

    The current project database uses timestamp/datetime
    values without timezone information.
    """

    return datetime.now(
        INDIA_TIMEZONE
    ).replace(
        tzinfo=None
    )


# ============================================================
# ETA PARSER
# ============================================================

def extract_eta_minutes(
    eta_prediction: Any,
) -> int | None:
    """
    Convert the orchestrator ETA value into minutes.

    Examples:

        "47 min" -> 47

        "1 min" -> 1

        None -> None

    This function deliberately does not invent an ETA.
    """

    if not eta_prediction:
        return None

    if isinstance(
        eta_prediction,
        dict,
    ):
        predicted_eta = (
            eta_prediction.get(
                "predicted_eta"
            )
        )
    else:
        predicted_eta = (
            str(eta_prediction)
        )

    if not predicted_eta:
        return None

    text = str(
        predicted_eta
    ).strip().lower()

    digits = ""

    for character in text:

        if character.isdigit():

            digits += character

        elif digits:

            break

    if not digits:
        return None

    try:

        return int(digits)

    except ValueError:

        return None


# ============================================================
# FIND EXISTING ACTIVE REQUEST
# ============================================================

def find_existing_active_request(
    db: Session,
    emergency_id: int,
):
    """
    Prevent duplicate active service requests
    for the same emergency.

    Return a request that is still part of the active lifecycle.
    Cancelled/rejected/timed-out requests may be retried according
    to the existing provider assignment flow.
    """

    return (
        db.query(
            ServiceRequest
        )
        .filter(
            ServiceRequest.emergency_id
            == emergency_id
        )
        .filter(
            ServiceRequest.request_status.notin_(
                [
                    "completed",
                    "cancelled",
                    "rejected",
                    "timeout",
                    "timed_out",
                ]
            )
        )
        .order_by(
            ServiceRequest.request_id.desc()
        )
        .first()
    )


# ============================================================
# RUN AI EMERGENCY ASSISTANCE
# ============================================================

@router.post(
    "/emergency/{emergency_id}/assist"
)
def run_agent_emergency_assistance(
    emergency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
) -> Dict[str, Any]:

    # ========================================================
    # STEP 1 — VERIFY EMERGENCY
    # ========================================================

    emergency = (
        db.query(
            Emergency
        )
        .filter(
            Emergency.emergency_id
            == emergency_id
        )
        .filter(
            Emergency.user_id
            == current_user.user_id
        )
        .with_for_update()
        .first()
    )

    if emergency is None:

        raise HTTPException(
            status_code=404,
            detail="Emergency not found",
        )

    # ========================================================
    # STEP 2 — CHECK EMERGENCY STATUS
    # ========================================================

    if str(emergency.status or "").strip().lower() in {
        "resolved",
        "completed",
        "cancelled",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "This emergency is already "
                f"{emergency.status}."
            ),
        )

    # ========================================================
    # STEP 3 — CHECK FOR EXISTING REQUEST
    # ========================================================

    existing_request = (
        find_existing_active_request(
            db=db,
            emergency_id=emergency_id,
        )
    )

    # An already assigned/accepted request is idempotently returned.
    # A pending request without a provider continues through provider
    # selection below and is assigned in place.
    if existing_request and (
        existing_request.request_status != "pending"
        or existing_request.provider_id is not None
    ):
        return {
            "success": True,
            "status": "existing_service_request",
            "emergency_id": emergency_id,
            "request_id": existing_request.request_id,
            "provider_id": existing_request.provider_id,
            "request_status": existing_request.request_status,
            "estimated_arrival": existing_request.estimated_arrival,
            "message": "An active service request already exists for this emergency.",
        }

    # ========================================================
    # STEP 4 — RUN AI ORCHESTRATOR
    # ========================================================

    orchestrator = create_orchestrator(
        db
    )

    result = (
        orchestrator.run_emergency_assistance(
            emergency_id
        )
    )

    if not result.get("success"):

        return {
            "success": False,
            "status": "agent_assistance_failed",
            "emergency_id": emergency_id,
            "agent_result": result,
        }

    plan_emergency = result.get("emergency")
    if not isinstance(plan_emergency, dict):
        plan_emergency = {
            "emergency_type": emergency.emergency_type,
            "priority": emergency.priority,
            "recommended_service": emergency.recommended_service,
        }
    plan_provider_count = result.get("provider_count")
    if plan_provider_count is None:
        plan_provider_count = len(result.get("providers") or [])

    record_agent_event(
        db,
        "emergency_analyzed",
        emergency_id=emergency_id,
        actor_user_id=current_user.user_id,
        details={
            "emergency_type": plan_emergency.get("emergency_type"),
            "priority": plan_emergency.get("priority"),
            "recommended_service": plan_emergency.get("recommended_service"),
        },
    )
    record_agent_event(
        db,
        "provider_search_completed",
        emergency_id=emergency_id,
        actor_user_id=current_user.user_id,
        details={"provider_count": plan_provider_count},
    )

    planned_provider = result.get("selected_provider")
    if planned_provider:
        record_agent_event(
            db,
            "provider_selected",
            emergency_id=emergency_id,
            actor_user_id=current_user.user_id,
            provider_id=planned_provider.get("provider_id"),
        )

    planned_route = result.get("route_summary")
    if isinstance(planned_route, dict):
        record_agent_event(
            db,
            "route_calculated",
            emergency_id=emergency_id,
            actor_user_id=current_user.user_id,
            provider_id=(planned_provider or {}).get("provider_id"),
            details={
                "distance_meters": planned_route.get("distance_meters"),
                "duration_seconds": planned_route.get("duration_seconds"),
            },
        )

    planned_eta = result.get("eta_prediction")
    if planned_eta is not None:
        record_agent_event(
            db,
            "eta_predicted",
            emergency_id=emergency_id,
            actor_user_id=current_user.user_id,
            provider_id=(planned_provider or {}).get("provider_id"),
            details={
                "predicted_eta": (
                    planned_eta.get("predicted_eta")
                    if isinstance(planned_eta, dict)
                    else str(planned_eta)
                ),
                "confidence": (
                    planned_eta.get("confidence")
                    if isinstance(planned_eta, dict)
                    else None
                ),
            },
        )

    # ========================================================
    # STEP 5 — CHECK PROVIDER
    # ========================================================

    selected_provider = (
        result.get(
            "selected_provider"
        )
    )

    if not selected_provider:

        try:
            db.commit()
        except Exception as error:
            db.rollback()
            print("Unable to persist agent planning events.")
            raise HTTPException(
                status_code=500,
                detail="Unable to save emergency planning history.",
            )

        return {
            "success": True,
            "status": result.get(
                "status",
                "no_provider_found",
            ),
            "emergency_id": emergency_id,
            "agent_result": result,
            "message": (
                "AI analyzed the emergency "
                "but no provider was selected."
            ),
        }

    provider_id = (
        selected_provider.get(
            "provider_id"
        )
    )

    if provider_id is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "AI selected a provider "
                "without a provider_id."
            ),
        )

    # ========================================================
    # STEP 6 — VERIFY PROVIDER IN DATABASE
    # ========================================================

    provider = (
        db.query(
            ServiceProvider
        )
        .filter(
            ServiceProvider.provider_id
            == provider_id
        )
        .with_for_update()
        .first()
    )

    if provider is None:

        raise HTTPException(
            status_code=404,
            detail=(
                "Selected provider was "
                "not found in the database."
            ),
        )

    if not provider.verified:
        return {
            "success": False,
            "status": "provider_unverified",
            "emergency_id": emergency_id,
            "provider_id": provider_id,
            "message": "The selected provider is not verified and cannot be assigned.",
        }

    # ========================================================
    # STEP 7 — VERIFY PROVIDER AVAILABILITY
    # ========================================================

    if not provider.is_available:

        return {
            "success": False,
            "status": "provider_unavailable",
            "emergency_id": emergency_id,
            "provider_id": provider_id,
            "message": (
                "The provider selected by the "
                "agent is no longer available."
            ),
        }

    # Providers remain marked available until they accept a request.
    # The provider row lock serializes assignment decisions; this query
    # catches an already-pending request committed by an earlier caller.
    pending_request_query = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.provider_id == provider_id,
            ServiceRequest.request_status == "pending",
        )
    )
    if existing_request is not None:
        pending_request_query = pending_request_query.filter(
            ServiceRequest.request_id != existing_request.request_id
        )
    pending_request = (
        pending_request_query
        .with_for_update()
        .first()
    )
    if pending_request is not None:
        return {
            "success": False,
            "status": "provider_unavailable",
            "emergency_id": emergency_id,
            "provider_id": provider_id,
            "message": (
                "The provider already has a pending request "
                "and cannot be assigned another one yet."
            ),
        }

    # ========================================================
    # STEP 8 — EXTRACT ETA
    # ========================================================

    eta_prediction = result.get(
        "eta_prediction"
    )

    if eta_prediction is None:

        eta_result = result.get(
            "eta"
        )

        if isinstance(
            eta_result,
            dict,
        ):

            eta_result_data = (
                eta_result.get(
                    "result",
                    {},
                )
            )

            if isinstance(
                eta_result_data,
                dict,
            ):

                eta_prediction = (
                    eta_result_data.get(
                        "eta_prediction"
                    )
                )

    estimated_arrival = (
        extract_eta_minutes(
            eta_prediction
        )
    )

    # ========================================================
    # STEP 9 — BUILD NOTES
    # ========================================================

    route_summary = result.get(
        "route_summary"
    )

    route_distance = None
    route_duration = None

    if isinstance(
        route_summary,
        dict,
    ):

        route_distance = (
            route_summary.get(
                "distance_meters"
            )
        )

        route_duration = (
            route_summary.get(
                "duration_seconds"
            )
        )

    notes = (
        "Assigned by ResQDrive AI agent. "
        f"Emergency type: "
        f"{emergency.emergency_type}. "
        f"Recommended service: "
        f"{emergency.recommended_service}."
    )

    if route_distance is not None:

        notes += (
            f" Route distance: "
            f"{route_distance} meters."
        )

    if route_duration is not None:

        notes += (
            f" Google route duration: "
            f"{route_duration} seconds."
        )

    if eta_prediction:

        notes += (
            f" AI ETA: "
            f"{eta_prediction.get('predicted_eta')}"
            if isinstance(
                eta_prediction,
                dict,
            )
            else (
                f" AI ETA: "
                f"{eta_prediction}."
            )
        )

    # ========================================================
    # STEP 10 — CREATE SERVICE REQUEST
    # ========================================================

    request = existing_request or ServiceRequest(
        emergency_id=emergency_id,
        user_id=current_user.user_id,
        request_status="pending",
        requested_at=db_now(),
    )
    request.provider_id = provider_id
    request.estimated_arrival = estimated_arrival
    request.notes = notes
    request.request_status = "pending"
    request.requested_at = db_now()

    # ========================================================
    # STEP 11 — UPDATE EMERGENCY
    # ========================================================

    # Mark the emergency assigned while leaving the provider request
    # pending until the provider explicitly accepts it.
    emergency.status = "assigned"
    notification = None
    if provider.user_id is not None:
        notification = Notification(
            user_id=provider.user_id,
            emergency_id=emergency.emergency_id,
            provider_id=provider.provider_id,
            title="New Emergency Request",
            message=(
                f"A {emergency.emergency_type} emergency needs "
                f"{emergency.recommended_service} assistance."
            ),
            status="unread",
        )

    try:

        if existing_request is None:
            db.add(request)
        db.flush()
        if notification is not None:
            db.add(notification)

        record_agent_event(
            db,
            "provider_request_sent",
            emergency_id=emergency.emergency_id,
            request_id=request.request_id,
            actor_user_id=current_user.user_id,
            provider_id=provider.provider_id,
            details={
                "estimated_arrival_minutes": estimated_arrival,
                "route_distance_meters": route_distance,
                "route_duration_seconds": route_duration,
            },
        )

        db.commit()

        db.refresh(
            request
        )

    except Exception as error:

        db.rollback()

        print(
            "AI service request creation error:",
            error,
        )

        raise HTTPException(status_code=500, detail="AI assistance could not assign the provider to the service request.")

    # Notify the provider only after the assignment transaction commits.
    # The durable in-app notification above remains available if FCM fails.
    push_sent = False
    if provider.user_id is not None:
        try:
            push_sent = bool(send_push_notification(
                db=db,
                user_id=provider.user_id,
                title="New Emergency Request",
                body=(
                    f"A {emergency.emergency_type} emergency needs "
                    f"{emergency.recommended_service} assistance."
                ),
                data={
                    "request_id": str(request.request_id),
                    "emergency_id": str(emergency_id),
                    "type": "new_service_request",
                },
            ))
        except Exception as error:
            print("Provider push notification failed.")

    # This second event distinguishes successful push delivery from the
    # durable in-app request notification committed above.
    if provider.user_id is not None:
        record_agent_event(
            db,
            "provider_push_notification_attempted",
            emergency_id=emergency.emergency_id,
            request_id=request.request_id,
            actor_user_id=current_user.user_id,
            provider_id=provider.provider_id,
            event_status="sent" if push_sent else "not_sent",
        )
        try:
            db.commit()
        except Exception as error:
            db.rollback()
            print("Unable to record provider push attempt.")

    # Preserve the current pending/accept/reassign lifecycle timeout.
    try:
        from services.timeout_service import start_timeout

        start_timeout(
            request_id=request.request_id,
            provider_id=provider.provider_id,
        )
    except Exception as error:
        print("Unable to start provider response timeout.")

    # ========================================================
    # STEP 13 — FINAL RESPONSE
    # ========================================================

    return {
        "success": True,
        "status": "provider_request_sent",

        "emergency": {
            "emergency_id": (
                emergency.emergency_id
            ),
            "emergency_type": (
                emergency.emergency_type
            ),
            "priority": (
                emergency.priority
            ),
            "status": (
                emergency.status
            ),
            "recommended_service": (
                emergency.recommended_service
            ),
        },

        "service_request": {
            "request_id": request.request_id,
            "provider_id": request.provider_id,
            "request_status": request.request_status,
            "estimated_arrival": request.estimated_arrival,
            "requested_at": request.requested_at,
        },

        "provider": {
            "provider_id": (
                provider.provider_id
            ),
            "name": (
                provider.name
            ),
            "service_type": (
                provider.service_type
            ),
            "phone": (
                provider.phone
            ),
            "is_available": (
                provider.is_available
            ),
        },

        "route": result.get(
            "route_summary"
        ),

        "eta_prediction": (
            eta_prediction
        ),

        "agent_result": result,

        "message": (
            "ResQDrive AI analyzed the emergency, "
            "selected an available provider, "
            "calculated the route, predicted ETA, "
            "and created a service request."
        ),
    }


@router.get("/emergency/{emergency_id}/events")
def get_agent_emergency_events(
    emergency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Dict[str, Any]]:
    """Return recent agent lifecycle events to the emergency owner."""
    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id == emergency_id,
            Emergency.user_id == current_user.user_id,
        )
        .first()
    )
    if emergency is None:
        raise HTTPException(status_code=404, detail="Emergency not found")

    events = (
        db.query(AgentEvent)
        .filter(AgentEvent.emergency_id == emergency_id)
        .order_by(AgentEvent.created_at.desc(), AgentEvent.event_id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_status": event.event_status,
            "request_id": event.request_id,
            "provider_id": event.provider_id,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event in reversed(events)
    ]
