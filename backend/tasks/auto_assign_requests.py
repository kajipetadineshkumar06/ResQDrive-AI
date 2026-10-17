# ==========================================
# tasks/auto_assign_requests.py
# ==========================================

import json

from database import SessionLocal

from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.emergency import Emergency
from models.notification import Notification

from services.nearby_service import calculate_distance
from services.firebase_notification import send_push_notification


# ==========================================
# GET EXCLUDED PROVIDER IDS
# ==========================================

def get_excluded_provider_ids(request):
    """
    Safely convert excluded_provider_ids
    into a Python set.
    """

    excluded = request.excluded_provider_ids

    if excluded is None:
        return set()

    # ======================================
    # PYTHON LIST
    # ======================================

    if isinstance(excluded, list):

        result = set()

        for provider_id in excluded:

            try:
                result.add(int(provider_id))

            except (TypeError, ValueError):
                continue

        return result

    # ======================================
    # JSON STRING
    # ======================================

    if isinstance(excluded, str):

        try:

            parsed = json.loads(excluded)

            if isinstance(parsed, list):

                result = set()

                for provider_id in parsed:

                    try:
                        result.add(int(provider_id))

                    except (TypeError, ValueError):
                        continue

                return result

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError
        ):
            pass

    return set()


# ==========================================
# FIND NEAREST AVAILABLE PROVIDER
# ==========================================

def find_nearest_provider(
    db,
    service_type,
    latitude,
    longitude,
    excluded_provider_ids=None
):
    """
    Find nearest suitable provider.

    Excluded providers will never be selected.
    """

    # ======================================
    # NORMALIZE SERVICE
    # ======================================

    required_service = (
        str(service_type)
        .strip()
        .lower()
    )

    # ======================================
    # NORMALIZE EXCLUDED
    # ======================================

    excluded_ids = set()

    if excluded_provider_ids:

        for provider_id in excluded_provider_ids:

            try:
                excluded_ids.add(int(provider_id))

            except (
                TypeError,
                ValueError
            ):
                continue

    # ======================================
    # GET AVAILABLE PROVIDERS
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
    # PROVIDERS ALREADY HAVING
    # PENDING REQUESTS
    # ======================================

    pending_provider_ids = {

        row.provider_id

        for row in (

            db.query(
                ServiceRequest.provider_id
            )
            .filter(

                ServiceRequest.request_status
                == "pending",

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
            f"{provider_id}"
        )

        # ==================================
        # EXCLUDED
        # ==================================

        if provider_id in excluded_ids:

            print(
                f"🚫 Provider "
                f"{provider_id} "
                f"excluded."
            )

            continue

        # ==================================
        # ALREADY HAS PENDING REQUEST
        # ==================================

        if provider_id in pending_provider_ids:

            print(
                f"⏳ Provider "
                f"{provider_id} already has "
                f"a pending request."
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
        ):

            continue

        print(
            f"📍 Provider "
            f"{provider_id} "
            f"distance={distance}"
        )

        # ==================================
        # NEAREST
        # ==================================

        if distance < minimum_distance:

            minimum_distance = distance

            nearest_provider = provider

    return nearest_provider


# ==========================================
# AUTO ASSIGN REQUESTS
# ==========================================

def auto_assign_requests():

    db = SessionLocal()

    try:

        # ==================================
        # GET PENDING REQUESTS
        # ==================================

        pending_requests = (

            db.query(ServiceRequest)

            .filter(
                ServiceRequest.request_status
                == "pending"
            )

            .all()

        )

        # ==================================
        # PROCESS REQUESTS
        # ==================================

        for request in pending_requests:

            # ==================================
            # ALREADY ASSIGNED
            # ==================================

            if request.provider_id is not None:

                print(
                    f"ℹ️ Request "
                    f"{request.request_id} "
                    f"already assigned to "
                    f"Provider "
                    f"{request.provider_id} "
                    f"(pending)."
                )

                continue

            # ==================================
            # GET EMERGENCY
            # ==================================

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
                    f"⚠️ Request "
                    f"{request.request_id}: "
                    f"Emergency "
                    f"{request.emergency_id} "
                    f"not found."
                )

                continue

            # ==================================
            # REQUIRED SERVICE
            # ==================================

            required_service = (

                str(
                    emergency.recommended_service
                ).strip()

                if emergency.recommended_service

                else None

            )

            if not required_service:

                print(
                    f"⚠️ Request "
                    f"{request.request_id}: "
                    f"Emergency has no "
                    f"recommended service."
                )

                continue

            # ==================================
            # LOCATION
            # ==================================

            latitude = getattr(
                emergency,
                "location_lat",
                None
            )

            longitude = getattr(
                emergency,
                "location_lng",
                None
            )

            if (
                latitude is None
                or longitude is None
            ):

                print(
                    f"⚠️ Request "
                    f"{request.request_id}: "
                    f"Emergency location "
                    f"unavailable."
                )

                continue

            # ==================================
            # EXCLUDED PROVIDERS
            # ==================================

            excluded_provider_ids = (

                get_excluded_provider_ids(
                    request
                )

            )

            print(
                f"🔎 Request "
                f"{request.request_id}: "
                f"Excluded providers: "
                f"{sorted(excluded_provider_ids)}"
            )

            # ==================================
            # FIND PROVIDER
            # ==================================

            provider = find_nearest_provider(

                db=db,

                service_type=
                    required_service,

                latitude=
                    latitude,

                longitude=
                    longitude,

                excluded_provider_ids=
                    excluded_provider_ids

            )

            # ==================================
            # NO PROVIDER
            # ==================================

            if provider is None:

                # --------------------------------
                # IMPORTANT
                #
                # Keep request pending.
                # Keep provider_id NULL.
                #
                # It means:
                #
                # "Waiting for a provider."
                # --------------------------------

                request.provider_id = None

                request.request_status = "pending"

                emergency.status = "pending"

                db.commit()

                print(
                    f"⏳ Request "
                    f"{request.request_id}: "
                    f"No provider currently "
                    f"available."
                )

                print(
                    f"⏳ Request "
                    f"{request.request_id} "
                    f"is waiting for a provider."
                )

                continue

            # Re-read and lock the selected provider before assignment so
            # a concurrent verification revocation or reservation cannot
            # slip through the discovery query.
            provider = (
                db.query(ServiceProvider)
                .filter(
                    ServiceProvider.provider_id == provider.provider_id
                )
                .with_for_update()
                .first()
            )
            if (
                provider is None
                or not provider.verified
                or not provider.is_available
            ):
                print("Skipping provider that is no longer eligible.")
                db.rollback()
                continue

            active_request = (
                db.query(ServiceRequest.request_id)
                .filter(
                    ServiceRequest.provider_id == provider.provider_id,
                    ServiceRequest.request_status.notin_(
                        (
                            "completed",
                            "cancelled",
                            "canceled",
                            "rejected",
                            "timeout",
                            "timed_out",
                        )
                    ),
                )
                .with_for_update()
                .first()
            )
            if active_request is not None:
                print("Skipping provider with another active request.")
                db.rollback()
                continue

            # ==================================
            # ASSIGN PROVIDER
            # ==================================

            request.provider_id = (
                provider.provider_id
            )

            request.request_status = "pending"

            emergency.status = "pending"

            # A pending offer reserves this provider until it is accepted,
            # rejected, or times out. Discovery also checks active requests,
            # but the provider's availability flag must match that state.
            provider.is_available = False

            # Persist an in-app notification in the same transaction
            # as the assignment, so the provider can still see the job
            # when push delivery is unavailable.
            provider_notification = None
            if provider.user_id is not None:
                emergency_label = (
                    str(emergency.emergency_type).strip()
                    if emergency.emergency_type
                    else "roadside assistance"
                )
                provider_notification = Notification(
                    user_id=provider.user_id,
                    emergency_id=emergency.emergency_id,
                    provider_id=provider.provider_id,
                    title="New service request",
                    message=(
                        f"A {emergency_label} request "
                        f"(#{request.request_id}) needs your response."
                    ),
                    status="unread",
                )
                db.add(provider_notification)

            # ==================================
            # SAVE
            # ==================================

            db.commit()

            db.refresh(request)

            db.refresh(provider)

            db.refresh(emergency)

            # Push delivery is best-effort and happens only after the
            # durable assignment and inbox notification have committed.
            # A missing Firebase setup/token must not undo an assignment.
            if provider_notification is not None:
                try:
                    send_push_notification(
                        db=db,
                        user_id=provider.user_id,
                        title=provider_notification.title,
                        body=provider_notification.message,
                        data={
                            "type": "service_request_assigned",
                            "request_id": str(request.request_id),
                            "emergency_id": str(emergency.emergency_id),
                        },
                    )
                except Exception as notification_error:
                    print(
                        "⚠️ Provider push notification failed for "
                        f"Request {request.request_id}: "
                        f"{notification_error}"
                    )

            # ==================================
            # PROVIDER NAME
            # ==================================

            provider_name = getattr(
                provider,
                "business_name",
                None
            )

            if not provider_name:

                provider_name = getattr(
                    provider,
                    "name",
                    None
                )

            if not provider_name:

                provider_name = (
                    f"Provider "
                    f"{provider.provider_id}"
                )

            # ==================================
            # LOG
            # ==================================

            print(
                f"✅ Request "
                f"{request.request_id} "
                f"assigned to Provider "
                f"{provider.provider_id} "
                f"({provider_name}) "
                f"as PENDING."
            )

    except Exception as error:

        db.rollback()

        print(
            f"❌ Auto assignment error: "
            f"{error}"
        )

    finally:

        db.close()
