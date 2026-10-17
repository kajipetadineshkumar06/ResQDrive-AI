# ==========================================
# services/ai_provider_ranking_service.py
# ==========================================
#
# ResQDrive AI Provider Ranking Engine
#
# Purpose:
# Rank available service providers using:
# - Service compatibility
# - Distance
# - Rating
# - Experience
# - Verification
# - Availability
# - Emergency priority
#
# This service does NOT require a paid AI API.
# It uses a transparent weighted scoring model.
# ==========================================

from typing import Any, Dict, List, Optional


# ==========================================
# RANKING WEIGHTS
# ==========================================

WEIGHTS = {
    "service_compatibility": 30.0,
    "distance": 25.0,
    "availability": 15.0,
    "rating": 10.0,
    "experience": 10.0,
    "verified": 5.0,
    "priority": 5.0,
}


# ==========================================
# PRIORITY VALUES
# ==========================================

PRIORITY_VALUES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


# ==========================================
# SAFE NUMBER CONVERSION
# ==========================================

def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


# ==========================================
# SAFE INTEGER CONVERSION
# ==========================================

def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:
        if value is None:
            return default

        return int(value)

    except (TypeError, ValueError):
        return default


# ==========================================
# NORMALIZE TEXT
# ==========================================

def normalize_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


# ==========================================
# SERVICE COMPATIBILITY SCORE
# ==========================================

def calculate_service_score(
    provider_service: Any,
    required_service: Any
) -> float:

    provider_service = normalize_text(
        provider_service
    )

    required_service = normalize_text(
        required_service
    )

    if not provider_service or not required_service:
        return 0.0

    if provider_service == required_service:
        return 100.0

    return 0.0


# ==========================================
# DISTANCE SCORE
# ==========================================
#
# Closer providers receive higher scores.
#
# 0 km       -> 100
# 1 km       -> ~90
# 5 km       -> ~50
# 10+ km     -> low
#
# ==========================================

def calculate_distance_score(
    distance_km: float
) -> float:

    distance_km = max(
        0.0,
        safe_float(distance_km)
    )

    score = 100.0 / (
        1.0 + distance_km
    )

    return min(
        100.0,
        max(
            0.0,
            score * 100.0
        )
    )


# ==========================================
# RATING SCORE
# ==========================================
#
# Provider rating:
#
# 5.0 -> 100
# 4.0 -> 80
# 3.0 -> 60
# etc.
#
# ==========================================

def calculate_rating_score(
    rating: Any
) -> float:

    rating = safe_float(
        rating,
        0.0
    )

    rating = min(
        5.0,
        max(
            0.0,
            rating
        )
    )

    return (
        rating / 5.0
    ) * 100.0


# ==========================================
# EXPERIENCE SCORE
# ==========================================

def calculate_experience_score(
    experience_years: Any
) -> float:

    years = safe_int(
        experience_years,
        0
    )

    years = max(
        0,
        years
    )

    # 10+ years = maximum score
    score = min(
        years,
        10
    ) / 10.0 * 100.0

    return score


# ==========================================
# VERIFICATION SCORE
# ==========================================

def calculate_verified_score(
    verified: Any
) -> float:

    if verified is True:
        return 100.0

    if isinstance(
        verified,
        str
    ):
        return (
            100.0
            if verified.strip().lower()
            in {
                "true",
                "1",
                "yes",
                "verified",
            }
            else 0.0
        )

    if isinstance(
        verified,
        int
    ):
        return (
            100.0
            if verified == 1
            else 0.0
        )

    return 0.0


# ==========================================
# AVAILABILITY SCORE
# ==========================================

def calculate_availability_score(
    is_available: Any
) -> float:

    if is_available is True:
        return 100.0

    if isinstance(
        is_available,
        str
    ):
        return (
            100.0
            if is_available.strip().lower()
            in {
                "true",
                "1",
                "yes",
                "available",
            }
            else 0.0
        )

    if isinstance(
        is_available,
        int
    ):
        return (
            100.0
            if is_available == 1
            else 0.0
        )

    return 0.0


# ==========================================
# PRIORITY SCORE
# ==========================================
#
# Critical emergencies should favor:
# - verified providers
# - experienced providers
# - reliable providers
#
# ==========================================

def calculate_priority_score(
    priority: Optional[str],
    verified: Any,
    experience_years: Any
) -> float:

    normalized_priority = normalize_text(
        priority
    )

    priority_value = PRIORITY_VALUES.get(
        normalized_priority,
        2
    )

    verified_value = (
        1.0
        if calculate_verified_score(
            verified
        ) > 0
        else 0.0
    )

    experience = min(
        safe_int(
            experience_years,
            0
        ),
        10
    ) / 10.0

    # Critical = strongest reliability preference
    if priority_value >= 4:
        score = (
            verified_value * 60.0
            + experience * 40.0
        )

    elif priority_value == 3:
        score = (
            verified_value * 50.0
            + experience * 50.0
        )

    else:
        score = (
            verified_value * 40.0
            + experience * 60.0
        )

    return min(
        100.0,
        max(
            0.0,
            score
        )
    )


# ==========================================
# CALCULATE PROVIDER SCORE
# ==========================================

def calculate_provider_score(
    provider: Any,
    required_service: str,
    distance_km: float,
    emergency_priority: Optional[str] = None,
) -> Dict[str, Any]:

    service_score = calculate_service_score(
        provider.service_type,
        required_service
    )

    distance_score = calculate_distance_score(
        distance_km
    )

    availability_score = calculate_availability_score(
        provider.is_available
    )

    rating_score = calculate_rating_score(
        provider.rating_avg
    )

    experience_score = calculate_experience_score(
        provider.experience_years
    )

    verified_score = calculate_verified_score(
        provider.verified
    )

    priority_score = calculate_priority_score(
        emergency_priority,
        provider.verified,
        provider.experience_years
    )

    # ======================================
    # WEIGHTED FINAL SCORE
    # ======================================

    final_score = (
        service_score
        * WEIGHTS["service_compatibility"]
        / 100.0
        +
        distance_score
        * WEIGHTS["distance"]
        / 100.0
        +
        availability_score
        * WEIGHTS["availability"]
        / 100.0
        +
        rating_score
        * WEIGHTS["rating"]
        / 100.0
        +
        experience_score
        * WEIGHTS["experience"]
        / 100.0
        +
        verified_score
        * WEIGHTS["verified"]
        / 100.0
        +
        priority_score
        * WEIGHTS["priority"]
        / 100.0
    )

    return {
        "provider_id": provider.provider_id,
        "provider_name": provider.name,
        "service_type": provider.service_type,

        "distance_km": round(
            distance_km,
            2
        ),

        "rating": round(
            safe_float(
                provider.rating_avg,
                0.0
            ),
            2
        ),

        "experience_years": safe_int(
            provider.experience_years,
            0
        ),

        "verified": bool(
            provider.verified
        ),

        "available": bool(
            provider.is_available
        ),

        "service_score": round(
            service_score,
            2
        ),

        "distance_score": round(
            distance_score,
            2
        ),

        "availability_score": round(
            availability_score,
            2
        ),

        "rating_score": round(
            rating_score,
            2
        ),

        "experience_score": round(
            experience_score,
            2
        ),

        "verified_score": round(
            verified_score,
            2
        ),

        "priority_score": round(
            priority_score,
            2
        ),

        "final_score": round(
            final_score,
            2
        ),
    }


# ==========================================
# RANK PROVIDERS
# ==========================================

def rank_providers(
    providers: List[Any],
    required_service: str,
    distance_map: Dict[int, float],
    emergency_priority: Optional[str] = None,
) -> List[Dict[str, Any]]:

    ranked_providers = []

    for provider in providers:

        provider_id = provider.provider_id

        distance_km = safe_float(
            distance_map.get(
                provider_id,
                float("inf")
            )
        )

        # Ignore invalid distance values
        if distance_km == float("inf"):
            continue

        result = calculate_provider_score(
            provider=provider,
            required_service=required_service,
            distance_km=distance_km,
            emergency_priority=emergency_priority,
        )

        # Only compatible providers
        if result["service_score"] <= 0:
            continue

        # Only available providers
        if result["availability_score"] <= 0:
            continue

        ranked_providers.append(
            result
        )

    # ======================================
    # SORT
    # ======================================
    #
    # Highest score first.
    #
    # If scores are equal:
    # nearest provider first.
    #
    # ======================================

    ranked_providers.sort(
        key=lambda item: (
            -item["final_score"],
            item["distance_km"],
        )
    )

    return ranked_providers


# ==========================================
# GET BEST PROVIDER
# ==========================================

def get_best_provider(
    providers: List[Any],
    required_service: str,
    distance_map: Dict[int, float],
    emergency_priority: Optional[str] = None,
):
    ranked = rank_providers(
        providers=providers,
        required_service=required_service,
        distance_map=distance_map,
        emergency_priority=emergency_priority,
    )

    if not ranked:
        return None, []

    best_provider_id = ranked[0][
        "provider_id"
    ]

    best_provider = None

    for provider in providers:

        if provider.provider_id == best_provider_id:
            best_provider = provider
            break

    return best_provider, ranked


# ==========================================
# DEBUG PRINT
# ==========================================

def print_ranking(
    ranked_providers: List[Dict[str, Any]],
    required_service: str,
    emergency_priority: Optional[str] = None,
) -> None:

    print("")
    print("=" * 60)
    print("🤖 RESQDRIVE AI PROVIDER RANKING")
    print("=" * 60)

    print(
        f"Required service: {required_service}"
    )

    print(
        f"Emergency priority: "
        f"{emergency_priority or 'MEDIUM'}"
    )

    print("")

    if not ranked_providers:

        print(
            "⚠️ No suitable providers found."
        )

        print("=" * 60)

        return

    for index, provider in enumerate(
        ranked_providers,
        start=1
    ):

        print(
            f"#{index} "
            f"Provider {provider['provider_id']} "
            f"- {provider['provider_name']}"
        )

        print(
            f"   Service: "
            f"{provider['service_type']}"
        )

        print(
            f"   Distance: "
            f"{provider['distance_km']} km"
        )

        print(
            f"   Rating: "
            f"{provider['rating']}"
        )

        print(
            f"   Experience: "
            f"{provider['experience_years']} years"
        )

        print(
            f"   Verified: "
            f"{'YES' if provider['verified'] else 'NO'}"
        )

        print(
            f"   Final Score: "
            f"{provider['final_score']}"
        )

        print("")

    print(
        "🏆 Best Provider: "
        f"{ranked_providers[0]['provider_id']} "
        f"- "
        f"{ranked_providers[0]['provider_name']}"
    )

    print(
        f"🏆 Score: "
        f"{ranked_providers[0]['final_score']}"
    )

    print("=" * 60)