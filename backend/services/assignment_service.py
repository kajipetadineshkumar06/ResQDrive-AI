# ==========================================
# services/assignment_service.py
# ==========================================

import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.notification import Notification
from models.emergency import Emergency
from services.nearby_service import calculate_distance
from services.agent_event_service import record_agent_event
from services.firebase_notification import send_push_notification
from services.maps._service import get_route
from services.ai_eta_prediction_service import predict_eta


# ==========================================
# DATABASE NOW (IST)
# ==========================================

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")

TERMINAL_REQUEST_STATUSES = (
    "completed",
    "cancelled",
    "canceled",
    "rejected",
    "timeout",
)

def utc_now():
    """
    Return current India/IST time as a naive datetime.

    The current MySQL setup stores naive DATETIME values
    representing IST, so request lifecycle timestamps must
    use the same clock as timeout_service.py.

    The function name is kept as utc_now() for compatibility
    with existing imports/call sites.
    """
    return datetime.now(INDIA_TIMEZONE).replace(tzinfo=None)


def release_provider_if_idle(
    db: Session,
    provider_id: int,
    *,
    excluding_request_id: int | None = None,
) -> bool:
    """Release a provider only when no other non-terminal request uses it."""

    provider = (
        db.query(ServiceProvider)
        .filter(ServiceProvider.provider_id == provider_id)
        .with_for_update()
        .first()
    )

    if provider is None:
        return False

    active_request_query = db.query(ServiceRequest.request_id).filter(
        ServiceRequest.provider_id == provider_id,
        ServiceRequest.request_status.notin_(TERMINAL_REQUEST_STATUSES),
    )

    if excluding_request_id is not None:
        active_request_query = active_request_query.filter(
            ServiceRequest.request_id != excluding_request_id
        )

    active_request = active_request_query.with_for_update().first()
    if active_request is not None:
        provider.is_available = False
        return False

    provider.is_available = True
    provider.is_tracking = False
    return True


# ==========================================
# REASSIGNMENT ROUTE / ETA
# ==========================================

def calculate_reassignment_eta_minutes(
    provider: ServiceProvider,
    emergency: Emergency,
) -> int | None:
    """Calculate a fresh route-based ETA for a newly assigned provider."""
    if (
        provider.location_lat is None
        or provider.location_lng is None
        or emergency.location_lat is None
        or emergency.location_lng is None
    ):
        return None

    try:
        route = get_route(
            origin_lat=float(provider.location_lat),
            origin_lng=float(provider.location_lng),
            dest_lat=float(emergency.location_lat),
            dest_lng=float(emergency.location_lng),
        )
        if not isinstance(route, dict):
            return None

        route_duration = route.get("duration")
        eta = predict_eta(
            provider_id=provider.provider_id,
            latitude=float(provider.location_lat),
            longitude=float(provider.location_lng),
            distance_meters=route.get("distance_meters"),
            duration=route_duration,
        )
        predicted_duration = (
            eta.get("predicted_duration")
            if isinstance(eta, dict)
            else None
        )
        duration = predicted_duration or route_duration
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)s\s*",
            str(duration or ""),
        )
        if match is None:
            return None

        seconds = float(match.group(1))
        if not math.isfinite(seconds) or seconds < 0:
            return None
        return max(1, math.ceil(seconds / 60))
    except Exception as error:
        print("Unable to calculate reassignment route/ETA.")
        return None


# ==========================================
# NORMALIZE EXCLUDED PROVIDERS
# ==========================================

def normalize_excluded_provider_ids(value):

    if value is None:
        return []

    # ======================================
    # PYTHON LIST
    # ======================================

    if isinstance(value, list):

        result = []

        for provider_id in value:

            try:

                result.append(
                    int(provider_id)
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        return list(
            dict.fromkeys(result)
        )

    # ======================================
    # JSON STRING
    # ======================================

    if isinstance(value, str):

        try:

            parsed = json.loads(value)

            if isinstance(parsed, list):

                result = []

                for provider_id in parsed:

                    try:

                        result.append(
                            int(provider_id)
                        )

                    except (
                        TypeError,
                        ValueError
                    ):

                        continue

                return list(
                    dict.fromkeys(result)
                )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError
        ):

            return []

    return []


# ==========================================
# PROVIDER ACCEPT REQUEST
# ==========================================

def accept_request(
    db: Session,
    request: ServiceRequest
):

    # ======================================
    # ONLY PENDING REQUEST
    # ======================================

    if request.request_status != "pending":

        return request

    # ======================================
    # PROVIDER REQUIRED
    # ======================================

    if request.provider_id is None:

        return request

    # ======================================
    # FIND PROVIDER
    # ======================================

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id
            == request.provider_id
        )
        .first()
    )

    if provider is None:

        return request

    # ======================================
    # ACCEPT
    # ======================================

    request.request_status = "accepted"

    request.accepted_at = utc_now()

    # ======================================
    # PROVIDER NOW BUSY
    # ======================================

    provider.is_available = False

    record_agent_event(
        db,
        "provider_accepted",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=provider.user_id,
        provider_id=provider.provider_id,
    )

    # ======================================
    # SAVE
    # ======================================

    db.commit()

    db.refresh(request)

    db.refresh(provider)

    return request


# ==========================================
# FIND NEXT PROVIDER
# ==========================================

def find_next_provider(
    db: Session,
    service_type: str,
    latitude: float,
    longitude: float,
    exclude_provider_id: int = None,
    excluded_provider_ids=None
):

    # ======================================
    # NORMALIZE SERVICE
    # ======================================

    required_service = (
        str(service_type)
        .strip()
        .lower()
    )

    # ======================================
    # BUILD EXCLUDED SET
    # ======================================

    excluded_ids = set()

    if exclude_provider_id is not None:

        try:

            excluded_ids.add(
                int(exclude_provider_id)
            )

        except (
            TypeError,
            ValueError
        ):

            pass

    normalized_excluded = (
        normalize_excluded_provider_ids(
            excluded_provider_ids
        )
    )

    for provider_id in normalized_excluded:

        excluded_ids.add(
            provider_id
        )

    print(
        f"🔎 Finding provider: "
        f"service={required_service}, "
        f"excluded={sorted(excluded_ids)}"
    )

    # ======================================
    # AVAILABLE PROVIDERS
    # ======================================

    providers = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.is_available.is_(True),
            ServiceProvider.verified.is_(True),
        )
        .all()
    )

    print(
        f"🔎 Available providers: "
        f"{len(providers)}"
    )

    # ======================================
    # PROVIDERS WITH ACTIVE REQUESTS
    # ======================================

    active_provider_ids = {

        row.provider_id

        for row in (

            db.query(
                ServiceRequest.provider_id
            )
            .filter(

                ServiceRequest.request_status.notin_(
                    TERMINAL_REQUEST_STATUSES
                ),

                ServiceRequest.provider_id
                .isnot(None)

            )
            .all()
        )

        if row.provider_id is not None
    }

    # ======================================
    # FIND NEAREST
    # ======================================

    nearest_provider = None

    minimum_distance = float("inf")

    # ======================================
    # CHECK PROVIDERS
    # ======================================

    for provider in providers:

        provider_id = provider.provider_id

        print(
            f"🔎 Checking Provider "
            f"{provider_id}: "
            f"{getattr(provider, 'name', '')}"
        )

        # ==================================
        # EXCLUDED
        # ==================================

        if provider_id in excluded_ids:

            print(
                f"🚫 Provider "
                f"{provider_id} excluded."
            )

            continue

        # ==================================
        # ACTIVE REQUEST
        # ==================================

        if provider_id in active_provider_ids:

            print(
                f"⏳ Provider "
                f"{provider_id} already has "
                f"an active request."
            )

            continue

        # ==================================
        # SERVICE TYPE
        # ==================================

        if provider.service_type is None:

            continue

        provider_service = (
            str(provider.service_type)
            .strip()
            .lower()
        )

        if provider_service != required_service:

            continue

        # ==================================
        # LOCATION
        # ==================================

        if (
            provider.location_lat is None
            or provider.location_lng is None
        ):

            continue

        # ==================================
        # DISTANCE
        # ==================================

        try:

            distance = calculate_distance(

                float(latitude),

                float(longitude),

                float(provider.location_lat),

                float(provider.location_lng)

            )

        except (
            TypeError,
            ValueError
        ) as error:

            print(
                f"⚠️ Distance calculation failed "
                f"for Provider "
                f"{provider_id}: "
                f"{error}"
            )

            continue

        print(
            f"📍 Provider "
            f"{provider_id} distance="
            f"{distance}"
        )

        # ==================================
        # NEAREST
        # ==================================

        if distance < minimum_distance:

            minimum_distance = distance

            nearest_provider = provider

    # ======================================
    # RESULT
    # ======================================

    if nearest_provider is None:

        print(
            "⚠️ No suitable alternate "
            "provider found."
        )

    else:

        print(
            f"✅ Next provider selected: "
            f"{nearest_provider.provider_id}"
        )

    return nearest_provider


# ==========================================
# PROVIDER REJECT / TIMEOUT
# ==========================================

def reject_request(
    db: Session,
    request: ServiceRequest,
    emergency,
    *,
    reason: str = "provider_timeout",
    actor_user_id: int | None = None,
):
    """
    Reject the current provider because of timeout
    and assign the next eligible provider.

    The request is reloaded with a database lock so
    concurrent scheduler operations do not overwrite
    the exclusion list.
    """

    # ======================================
    expected_provider_id = request.provider_id

    # RELOAD + LOCK REQUEST
    # ======================================

    locked_request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id
            == request.request_id
        )
        .with_for_update()
        .first()
    )

    if locked_request is None:

        print(
            f"⚠️ Request {request.request_id} "
            f"not found."
        )

        return None

    request = locked_request

    # The caller may have waited for another rejection or timeout to finish.
    # Never reject a provider assigned after the caller loaded this request.
    if (
        request.request_status != "pending"
        or expected_provider_id is None
        or request.provider_id != expected_provider_id
    ):
        print(f"↩️ Stale rejection ignored for Request {request.request_id}.")
        return None

    # ======================================
    # RELOAD EMERGENCY
    # ======================================

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == request.emergency_id
        )
        .first()
    )

    if emergency is None:

        print(
            f"⚠️ Emergency not found for "
            f"Request {request.request_id}."
        )

        return None

    # ======================================
    # OLD PROVIDER
    # ======================================

    old_provider_id = request.provider_id

    print(
        f"🔄 Rejecting Request "
        f"{request.request_id}; "
        f"old provider={old_provider_id}"
    )

    # ======================================
    # LOAD CURRENT EXCLUDED LIST
    # ======================================

    excluded_provider_ids = (
        normalize_excluded_provider_ids(
            request.excluded_provider_ids
        )
    )

    # ======================================
    # ADD OLD PROVIDER
    # ======================================

    if old_provider_id is not None:

        try:

            old_provider_id = int(
                old_provider_id
            )

        except (
            TypeError,
            ValueError
        ):

            old_provider_id = None

    if (
        old_provider_id is not None
        and old_provider_id
        not in excluded_provider_ids
    ):

        excluded_provider_ids.append(
            old_provider_id
        )

    # ======================================
    # SAVE EXCLUSION LIST
    # ======================================

    request.excluded_provider_ids = list(
        dict.fromkeys(
            excluded_provider_ids
        )
    )

    if reason == "provider_rejected":
        record_agent_event(
            db,
            "provider_rejected",
            emergency_id=request.emergency_id,
            request_id=request.request_id,
            actor_user_id=actor_user_id,
            provider_id=old_provider_id,
            event_status="rejected",
        )

    record_agent_event(
        db,
        "provider_fallback_triggered",
        emergency_id=request.emergency_id,
        request_id=request.request_id,
        actor_user_id=actor_user_id,
        provider_id=old_provider_id,
        details={"reason": reason},
    )

    print(
        f"🚫 Excluded providers: "
        f"{request.excluded_provider_ids}"
    )

    # ======================================
    # RELEASE OLD PROVIDER
    # ======================================

    old_provider = None

    if old_provider_id is not None:
        released = release_provider_if_idle(
            db,
            old_provider_id,
            excluding_request_id=request.request_id,
        )

        if released:
            print(
                f"🔓 Provider {old_provider_id} released."
            )
        else:
            print(
                f"🔒 Provider {old_provider_id} remains unavailable "
                "because another active request still uses it."
            )

    # ======================================
    # FLUSH EXCLUSION UPDATE
    # ======================================

    db.flush()

    # ======================================
    # FIND NEXT PROVIDER
    # ======================================

    new_provider = None

    # A provider can become unavailable after the search query. Lock the
    # selected row and recheck both availability and pending assignments
    # before associating this request with them.
    while True:
        candidate = find_next_provider(
            db=db,
            service_type=emergency.recommended_service,
            latitude=emergency.location_lat,
            longitude=emergency.location_lng,
            exclude_provider_id=old_provider_id,
            excluded_provider_ids=request.excluded_provider_ids,
        )

        if candidate is None:
            break

        locked_candidate = (
            db.query(ServiceProvider)
            .filter(
                ServiceProvider.provider_id
                == candidate.provider_id
            )
            .with_for_update()
            .first()
        )

        has_active_request = False
        if (
            locked_candidate is not None
            and locked_candidate.is_available
            and locked_candidate.verified
        ):
            has_active_request = (
                db.query(ServiceRequest.request_id)
                .filter(
                    ServiceRequest.provider_id
                    == locked_candidate.provider_id,
                    ServiceRequest.request_status.notin_(
                        TERMINAL_REQUEST_STATUSES
                    ),
                )
                .with_for_update()
                .first()
                is not None
            )

        if (
            locked_candidate is not None
            and locked_candidate.is_available
            and locked_candidate.verified
            and not has_active_request
        ):
            new_provider = locked_candidate
            break

        # Exclude this candidate for this emergency so a stale search result
        # cannot cause an infinite retry or a duplicate pending assignment.
        excluded_provider_ids = normalize_excluded_provider_ids(
            request.excluded_provider_ids
        )
        if candidate.provider_id not in excluded_provider_ids:
            excluded_provider_ids.append(candidate.provider_id)
        request.excluded_provider_ids = excluded_provider_ids
        db.flush()

    # ======================================
    # NO NEXT PROVIDER
    # ======================================

    if new_provider is None:

        request.provider_id = None
        request.estimated_arrival = None

        request.request_status = "pending"

        request.requested_at = utc_now()

        request.accepted_at = None
        request.started_at = None
        request.arrived_at = None
        request.completed_at = None
        request.cancelled_at = None

        emergency.status = "pending"

        record_agent_event(
            db,
            "provider_search_exhausted",
            emergency_id=emergency.emergency_id,
            request_id=request.request_id,
            actor_user_id=actor_user_id,
            provider_id=old_provider_id,
            event_status="waiting_for_provider",
            details={"reason": reason},
        )

        db.commit()

        db.refresh(request)
        db.refresh(emergency)

        print(
            f"⏳ Request "
            f"{request.request_id} "
            f"is waiting for a provider."
        )

        print(
            f"🚫 FINAL EXCLUDED PROVIDERS: "
            f"{request.excluded_provider_ids}"
        )

        return request

    # ======================================
    # ASSIGN NEW PROVIDER
    # ======================================

    request.provider_id = (
        new_provider.provider_id
    )
    request.estimated_arrival = None
    request.request_status = "pending"

    # Reserve the provider while the reassigned offer is pending.
    new_provider.is_available = False

    request.requested_at = utc_now()

    request.accepted_at = None
    request.started_at = None
    request.arrived_at = None
    request.completed_at = None
    request.cancelled_at = None

    emergency.status = "pending"

    record_agent_event(
        db,
        "provider_reassigned",
        emergency_id=emergency.emergency_id,
        request_id=request.request_id,
        actor_user_id=actor_user_id,
        provider_id=new_provider.provider_id,
        details={
            "previous_provider_id": old_provider_id,
            "reason": reason,
        },
    )

    # ======================================
    # NOTIFICATION
    # ======================================

    provider_notification = None
    if new_provider.user_id is not None:

        provider_notification = Notification(

            user_id=
                new_provider.user_id,

            emergency_id=
                emergency.emergency_id,

            provider_id=
                new_provider.provider_id,

            title=
                "New Emergency",

            message=
                "Emergency reassigned to you.",

            status=
                "unread"
        )

        db.add(provider_notification)

    # ======================================
    # SAVE EVERYTHING
    # ======================================

    db.commit()

    db.refresh(request)
    db.refresh(new_provider)
    db.refresh(emergency)

    # Push is best-effort; the assignment and inbox record have already
    # committed and are not rolled back when Firebase is unavailable.
    if provider_notification is not None:
        try:
            push_sent = send_push_notification(
                db=db,
                user_id=new_provider.user_id,
                title=provider_notification.title,
                body=provider_notification.message,
                data={
                    "type": "service_request_assigned",
                    "request_id": str(request.request_id),
                    "emergency_id": str(emergency.emergency_id),
                },
            )
            if not push_sent:
                print(
                    f"⚠️ Provider push was not delivered for "
                    f"Request {request.request_id}."
                )
        except Exception as error:
            print(
                f"⚠️ Provider push failed for Request "
                f"{request.request_id}: {error}"
            )

    # Calculate outside the assignment transaction so external route calls
    # cannot hold request/provider row locks. Apply it only to this assignment.
    estimated_arrival = calculate_reassignment_eta_minutes(
        new_provider,
        emergency,
    )
    if estimated_arrival is not None:
        try:
            current_request = (
                db.query(ServiceRequest)
                .filter(
                    ServiceRequest.request_id == request.request_id,
                    ServiceRequest.provider_id == new_provider.provider_id,
                    ServiceRequest.request_status.notin_(
                        TERMINAL_REQUEST_STATUSES
                    ),
                )
                .with_for_update()
                .first()
            )
            if current_request is not None:
                current_request.estimated_arrival = estimated_arrival
                db.commit()
                db.refresh(request)
            else:
                db.rollback()
        except Exception as error:
            db.rollback()
            print(
                f"⚠️ Unable to save reassignment ETA for Request "
                f"{request.request_id}: {error}"
            )

    # ======================================
    # LOG
    # ======================================

    print(
        f"🔄 Request "
        f"{request.request_id}: "
        f"reassigned to Provider "
        f"{new_provider.provider_id}."
    )

    print(
        f"🚫 FINAL EXCLUDED PROVIDERS: "
        f"{request.excluded_provider_ids}"
    )

    # ======================================
    # START NEW TIMEOUT
    # ======================================

    try:

        from services.timeout_service import (
            start_timeout
        )

        start_timeout(

            request_id=
                request.request_id,

            provider_id=
                new_provider.provider_id
        )

        print(
            f"⏱️ New timeout started "
            f"for Request "
            f"{request.request_id}."
        )

    except Exception as error:

        print(
            f"⚠️ Unable to start new "
            f"provider timeout: "
            f"{error}"
        )

    return request
