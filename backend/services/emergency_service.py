# ==========================================
# services/emergency_service.py
# ==========================================

import logging

from sqlalchemy.orm import Session

from models.emergency import Emergency
from models.service_request import ServiceRequest
from models.service_provider import ServiceProvider
from models.notification import Notification

from services.ai_service import recommend_provider_type
from services.ollama_emergency_service import OLLAMA_ENABLED, classify_emergency
from services.vehicle_ai_service import analyze_vehicle_problem
from services.nearby_service import find_nearest_provider
from services.timeout_service import start_timeout
from services.firebase_notification import send_push_notification

logger = logging.getLogger(__name__)


# ==========================================
# EMERGENCY TYPE NORMALIZATION
# ==========================================

def normalize_emergency_type(
    emergency_type: str
) -> str:

    if not emergency_type:
        return "other"

    value = (
        emergency_type
        .strip()
        .lower()
    )

    emergency_type_map = {

        # ======================================
        # BREAKDOWN
        # ======================================

        "breakdown": "breakdown",
        "vehicle breakdown": "breakdown",

        # ======================================
        # ACCIDENT
        # ======================================

        "accident": "accident",
        "road accident": "accident",

        # ======================================
        # FUEL
        # ======================================

        "fuel": "fuel_out",
        "fuel out": "fuel_out",
        "fuel_out": "fuel_out",
        "fuel empty": "fuel_out",
        "out of fuel": "fuel_out",
        "out of petrol": "fuel_out",
        "out of diesel": "fuel_out",

        # ======================================
        # FLAT TYRE
        # ======================================

        "flat tyre": "flat_tyre",
        "flat tire": "flat_tyre",
        "flat_tyre": "flat_tyre",
        "flat_tire": "flat_tyre",
        "puncture": "flat_tyre",
        "punctured tyre": "flat_tyre",
        "punctured tire": "flat_tyre",

        # ======================================
        # BATTERY
        # ======================================

        "battery": "battery",
        "battery problem": "battery",
        "dead battery": "battery",
        "battery dead": "battery",

        # ======================================
        # ENGINE
        # ======================================

        "engine": "engine",
        "engine problem": "engine",
        "engine failure": "engine",
        "engine stopped": "engine",
        "mechanical failure": "engine",

        # ======================================
        # OVERHEATING
        # ======================================

        "overheating": "overheating",
        "overheated": "overheating",
        "engine overheating": "overheating",
        "engine hot": "overheating",

        # ======================================
        # LOCKOUT
        # ======================================

        "lockout": "lockout",
        "vehicle lockout": "lockout",

        # ======================================
        # MEDICAL
        # ======================================

        "medical": "medical",
        "medical emergency": "medical",
        "injury": "medical",

        # ======================================
        # TOWING
        # ======================================

        "towing": "towing",
        "tow": "towing",
        "vehicle stuck": "vehicle_stuck",
        "stuck vehicle": "vehicle_stuck",

        # ======================================
        # EV
        # ======================================

        "ev": "ev_charging",
        "ev charging": "ev_charging",
        "ev_charging": "ev_charging",
        "charging": "ev_charging",

        # ======================================
        # OTHER
        # ======================================

        "other": "other",
    }

    return emergency_type_map.get(
        value,
        "other"
    )


# ==========================================
# CREATE EMERGENCY SERVICE
# ==========================================

def create_emergency_service(
    db: Session,
    current_user,
    data
):
    """
    Complete Emergency Workflow

    1. Normalize emergency type
    2. Run local Qwen3 emergency classification
    3. Create emergency
    4. Recommend provider type
    5. Find nearest provider
    6. Create pending service request
    7. Notify provider
    8. Start timeout
    9. Return result

    The existing provider matching and emergency
    workflow are preserved.
    """

    # ==========================================
    # 1. NORMALIZE USER EMERGENCY TYPE
    # ==========================================

    normalized_emergency_type = (
        normalize_emergency_type(
            getattr(
                data,
                "emergency_type",
                None
            )
        )
    )

    # ==========================================
    # 2. LOCAL AI CLASSIFICATION
    # ==========================================

    description = getattr(
        data,
        "description",
        None
    )

    priority_rank = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    fallback_priority = str(
        getattr(data, "priority", "MEDIUM")
    ).strip().lower()
    if fallback_priority not in priority_rank:
        fallback_priority = "medium"

    # Persist the customer request before any optional AI work. If the AI
    # provider is unavailable or times out, the emergency remains recorded.
    emergency = Emergency(
        user_id=current_user.user_id,
        vehicle_id=data.vehicle_id,
        emergency_type=normalized_emergency_type,
        description=data.description,
        location_lat=data.location_lat,
        location_lng=data.location_lng,
        priority=fallback_priority,
        status="pending",
    )
    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    ai_result = {
        "emergency_type": normalized_emergency_type,
        "priority": fallback_priority,
        "confidence": 0,
        "source": "user_input",
    }

    vehicle_ai_result = None

    if description and description.strip():

        # ==========================================
        # 2A. VEHICLE NLP / LLM ANALYSIS
        # ==========================================
        # Qwen3 analyzes the customer's natural-language
        # vehicle problem. It is advisory and does not
        # replace a professional mechanical diagnosis.
        try:
            vehicle_ai_result = analyze_vehicle_problem(description)

            logger.info("Vehicle AI analysis completed.")

        except Exception as error:
            logger.warning("Vehicle AI failed; continuing with request data (%s).", type(error).__name__)
            vehicle_ai_result = None

        # ==========================================
        # 2B. EMERGENCY CLASSIFICATION
        # ==========================================
        if OLLAMA_ENABLED:
            try:
                classified_result = classify_emergency(description)
                if classified_result.get("source") == "ollama_qwen3":
                    ai_result = classified_result
                    normalized_emergency_type = normalize_emergency_type(
                        classified_result.get(
                            "emergency_type",
                            normalized_emergency_type,
                        )
                    )
                    logger.info("Emergency classification completed.")
                else:
                    logger.warning("Emergency classification unavailable; keeping customer input.")

            except Exception as error:
                logger.warning("Emergency classification failed; keeping customer input (%s).", type(error).__name__)
    # 2C. COMBINE AI PRIORITY SAFELY
    # ==========================================
    selected_priority = str(
        ai_result.get("priority", getattr(data, "priority", "MEDIUM"))
    ).strip().lower()

    vehicle_priority = None
    if vehicle_ai_result:
        vehicle_priority = str(
            vehicle_ai_result.get("priority", "")
        ).strip().lower()

    if vehicle_priority in priority_rank and (
        selected_priority not in priority_rank
        or priority_rank[vehicle_priority] > priority_rank[selected_priority]
    ):
        selected_priority = vehicle_priority

    if selected_priority not in priority_rank:
        selected_priority = "medium"

    # ==========================================
    # 3. CREATE EMERGENCY
    # ==========================================

    emergency.emergency_type = normalized_emergency_type
    emergency.priority = selected_priority
    db.commit()
    db.refresh(emergency)

    # ==========================================
    # 4. RECOMMEND PROVIDER TYPE
    # ==========================================

    service_type = (
        recommend_provider_type(
            emergency.emergency_type
        )
    )

    emergency.recommended_service = (
        service_type
    )

    db.commit()

    db.refresh(emergency)

    # ==========================================
    # 5. FIND NEAREST PROVIDER
    # ==========================================

    provider = find_nearest_provider(
        db=db,
        service_type=service_type,
        latitude=emergency.location_lat,
        longitude=emergency.location_lng,
        emergency_priority=emergency.priority,
    )

    if provider is not None:
        # Revalidate the discovery result under a row lock. Verification or
        # availability can change after the candidate query returns.
        provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.provider_id == provider.provider_id)
            .with_for_update()
            .first()
        )
        if provider is not None and (
            not provider.verified or not provider.is_available
        ):
            provider = None

        if provider is not None:
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
                provider = None

    # ==========================================
    # NO PROVIDER AVAILABLE
    # ==========================================

    if provider is None:

        return {
            "message": (
                "Emergency Created. "
                "No Provider Available."
            ),

            "emergency": emergency,

            "provider": None,

            "request": None
        }

    # ==========================================
    # 6. CREATE SERVICE REQUEST
    # ==========================================

    request = ServiceRequest(
        emergency_id=(
            emergency.emergency_id
        ),

        provider_id=(
            provider.provider_id
        ),

        user_id=(
            current_user.user_id
        ),

        request_status="pending"
    )

    db.add(request)

    # ==========================================
    # RESERVE THE PROVIDER WHILE THE OFFER IS PENDING
    # ==========================================
    # The provider has a pending assignment and must not be selected for
    # another request while deciding whether to accept it.
    provider.is_available = False

    # ==========================================
    # 7. CREATE PROVIDER NOTIFICATION
    # ==========================================

    if provider.user_id is not None:

        notification = Notification(
            user_id=provider.user_id,

            emergency_id=(
                emergency.emergency_id
            ),

            provider_id=(
                provider.provider_id
            ),

            title="New Emergency",

            message=(
                f"{emergency.emergency_type} "
                f"request assigned"
            ),

            status="unread"
        )

        db.add(notification)

    # ==========================================
    # 8. SAVE
    # ==========================================

    db.commit()

    db.refresh(emergency)

    db.refresh(request)

    db.refresh(provider)

    # ==========================================
    # 9. START TIMEOUT
    # ==========================================

    start_timeout(
        request.request_id
    )

    # ==========================================
    # 10. PUSH NOTIFICATION
    # ==========================================

    if provider.user_id is not None:

        try:

            send_push_notification(
                db=db,

                user_id=(
                    provider.user_id
                ),

                title="New Emergency",

                body=(
                    f"{emergency.emergency_type} "
                    f"request assigned."
                ),

                data={
                    "request_id": str(
                        request.request_id
                    ),

                    "type": "new_request"
                }
            )

        except Exception as error:
            logger.warning("Provider push notification failed (%s).", type(error).__name__)

    # ==========================================
    # 11. FINAL RESPONSE
    # ==========================================

    return {
        "message": (
            "Provider Assigned Successfully"
        ),

        "emergency": emergency,

        "provider": provider,

        "request": request,

        # Vehicle AI result is returned to the API response
        # without requiring a database schema change.
        "vehicle_ai_analysis": vehicle_ai_result
    }
