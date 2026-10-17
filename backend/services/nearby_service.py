# ==========================================
# services/nearby_service.py
# ==========================================
#
# ResQDrive AI Provider Discovery + Ranking
# ==========================================

from math import (
    radians,
    sin,
    cos,
    sqrt,
    atan2,
)

from sqlalchemy.orm import Session

from models.service_provider import ServiceProvider
from models.service_request import ServiceRequest

from services.ai_provider_ranking_service import (
    get_best_provider,
    print_ranking,
)


# ==========================================
# CALCULATE DISTANCE
# ==========================================

def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
):

    R = 6371.0

    lat1 = radians(
        float(lat1)
    )

    lon1 = radians(
        float(lon1)
    )

    lat2 = radians(
        float(lat2)
    )

    lon2 = radians(
        float(lon2)
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return R * c


# ==========================================
# FIND NEAREST / BEST AVAILABLE PROVIDER
# ==========================================
#
# Backward-compatible function.
#
# Existing callers can continue using:
#
# find_nearest_provider(
#     db=db,
#     service_type="mechanic",
#     latitude=...,
#     longitude=...
# )
#
# The function now uses the AI ranking engine
# instead of simply choosing the nearest provider.
# ==========================================

def find_nearest_provider(
    db: Session,
    service_type: str,
    latitude: float,
    longitude: float,
    emergency_priority: str = "medium",
):

    required_service = (
        str(service_type)
        .strip()
        .lower()
    )

    # ==========================================
    # GET AVAILABLE PROVIDERS
    # ==========================================

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

    if not providers:

        print(
            "⚠️ No available providers."
        )

        return None

    # ==========================================
    # GET PROVIDERS ALREADY HAVING PENDING REQUEST
    # ==========================================

    pending_provider_ids = {
        row.provider_id
        for row in (
            db.query(
                ServiceRequest.provider_id
            )
            .filter(
                ServiceRequest.request_status
                == "pending",
                ServiceRequest.provider_id.isnot(None),
            )
            .all()
        )
    }

    # ==========================================
    # PREPARE RANKING CANDIDATES
    # ==========================================

    candidates = []

    distance_map = {}

    for provider in providers:

        print(
            f"🔎 Checking Provider "
            f"{provider.provider_id}: "
            f"{provider.name}"
        )

        # ======================================
        # SERVICE TYPE
        # ======================================

        if provider.service_type is None:

            print(
                "   🚫 No service type."
            )

            continue

        provider_service = (
            str(provider.service_type)
            .strip()
            .lower()
        )

        if provider_service != required_service:

            print(
                f"   🚫 Service mismatch: "
                f"{provider_service}"
            )

            continue

        # ======================================
        # PENDING REQUEST
        # ======================================

        if provider.provider_id in (
            pending_provider_ids
        ):

            print(
                "   ⏳ Provider already has "
                "a pending request."
            )

            continue

        # ======================================
        # LOCATION
        # ======================================

        if (
            provider.location_lat is None
            or provider.location_lng is None
        ):

            print(
                "   🚫 Provider location missing."
            )

            continue

        # ======================================
        # CALCULATE DISTANCE
        # ======================================

        distance_km = calculate_distance(
            latitude,
            longitude,
            float(provider.location_lat),
            float(provider.location_lng),
        )

        distance_map[
            provider.provider_id
        ] = distance_km

        candidates.append(
            provider
        )

        print(
            f"   📍 Distance: "
            f"{distance_km:.2f} km"
        )

    # ==========================================
    # NO CANDIDATES
    # ==========================================

    if not candidates:

        print(
            "⚠️ No suitable provider candidates."
        )

        return None

    # ==========================================
    # AI PROVIDER RANKING
    # ==========================================

    best_provider, ranked = (
        get_best_provider(
            providers=candidates,
            required_service=required_service,
            distance_map=distance_map,
            emergency_priority=emergency_priority,
        )
    )

    # ==========================================
    # PRINT AI RANKING
    # ==========================================

    print_ranking(
        ranked_providers=ranked,
        required_service=required_service,
        emergency_priority=emergency_priority,
    )

    # ==========================================
    # RETURN BEST PROVIDER
    # ==========================================

    if best_provider is None:

        print(
            "⚠️ AI ranking could not select "
            "a provider."
        )

        return None

    print(
        f"🏆 Selected Provider "
        f"{best_provider.provider_id}: "
        f"{best_provider.name}"
    )

    return best_provider
