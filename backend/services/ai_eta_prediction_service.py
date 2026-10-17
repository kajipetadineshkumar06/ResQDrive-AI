# =========================================================
# services/ai_eta_prediction_service.py
# ResQDrive AI - Adaptive ETA Prediction
# =========================================================

from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional


# =========================================================
# CONFIGURATION
# =========================================================

MIN_VALID_DISTANCE_METERS = 1.0
MIN_VALID_DURATION_SECONDS = 1.0

MIN_SPEED_KMH = 5.0
MAX_SPEED_KMH = 150.0

MIN_FACTOR = 0.70
MAX_FACTOR = 1.80

SMOOTHING_ALPHA = 0.35

STALE_SAMPLE_SECONDS = 300


# =========================================================
# PROVIDER ETA STATE
# =========================================================

_provider_state: Dict[int, Dict[str, Any]] = {}


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value: Any) -> Optional[float]:
    """
    Safely convert a value to float.
    """

    try:
        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except (TypeError, ValueError):
        return None


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(minimum, min(value, maximum))


def _duration_to_seconds(duration: Any) -> Optional[float]:
    """
    Convert Google duration such as:

        774s

    into:

        774.0
    """

    if duration is None:
        return None

    text = str(duration).strip()

    if not text:
        return None

    if text.endswith("s"):
        text = text[:-1]

    try:
        seconds = float(text)

        if not math.isfinite(seconds):
            return None

        if seconds <= 0:
            return None

        return seconds

    except (TypeError, ValueError):
        return None


def _seconds_to_duration(seconds: float) -> str:
    """
    Convert seconds to Google-style duration.
    """

    seconds = max(1.0, float(seconds))

    return f"{round(seconds)}s"


def _seconds_to_eta(seconds: float) -> str:
    """
    Convert seconds to human-readable ETA.
    """

    seconds = max(1.0, float(seconds))

    minutes = round(seconds / 60)

    if minutes <= 0:
        return "< 1 min"

    return f"{minutes} min"


# =========================================================
# INITIALIZE PROVIDER
# =========================================================

def _get_provider_state(
    provider_id: int,
) -> Dict[str, Any]:

    if provider_id not in _provider_state:

        _provider_state[provider_id] = {
            "last_latitude": None,
            "last_longitude": None,
            "last_timestamp": None,
            "speed_kmh": None,
            "eta_factor": 1.0,
            "samples": 0,
        }

    return _provider_state[provider_id]


# =========================================================
# HAVERSINE DISTANCE
# =========================================================

def _haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate straight-line distance between
    two GPS coordinates.
    """

    earth_radius = 6371000.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius * c


# =========================================================
# UPDATE PROVIDER SPEED
# =========================================================

def _update_provider_speed(
    provider_id: int,
    latitude: float,
    longitude: float,
) -> Optional[float]:
    """
    Estimate provider speed from consecutive GPS samples.

    This does NOT replace Google Routes.

    It learns the provider's recent movement speed
    and uses it to adjust the route ETA.
    """

    state = _get_provider_state(provider_id)

    now = time.time()

    previous_latitude = state.get(
        "last_latitude"
    )

    previous_longitude = state.get(
        "last_longitude"
    )

    previous_timestamp = state.get(
        "last_timestamp"
    )

    state["last_latitude"] = latitude
    state["last_longitude"] = longitude
    state["last_timestamp"] = now

    if (
        previous_latitude is None
        or previous_longitude is None
        or previous_timestamp is None
    ):
        return state.get("speed_kmh")

    elapsed_seconds = now - previous_timestamp

    if (
        elapsed_seconds <= 0
        or elapsed_seconds > STALE_SAMPLE_SECONDS
    ):
        return state.get("speed_kmh")

    distance_meters = _haversine_distance_meters(
        previous_latitude,
        previous_longitude,
        latitude,
        longitude,
    )

    if distance_meters < MIN_VALID_DISTANCE_METERS:
        return state.get("speed_kmh")

    speed_kmh = (
        distance_meters
        / elapsed_seconds
        * 3.6
    )

    if (
        speed_kmh < MIN_SPEED_KMH
        or speed_kmh > MAX_SPEED_KMH
    ):
        return state.get("speed_kmh")

    previous_speed = state.get("speed_kmh")

    if previous_speed is None:

        smoothed_speed = speed_kmh

    else:

        smoothed_speed = (
            SMOOTHING_ALPHA * speed_kmh
            + (1 - SMOOTHING_ALPHA)
            * previous_speed
        )

    state["speed_kmh"] = smoothed_speed

    state["samples"] = (
        state.get("samples", 0) + 1
    )

    return smoothed_speed


# =========================================================
# ETA FACTOR
# =========================================================

def _calculate_eta_factor(
    provider_speed_kmh: Optional[float],
    route_distance_meters: float,
    route_duration_seconds: float,
) -> float:
    """
    Compare provider's observed movement speed with
    the effective speed implied by the Google route.

    Factor > 1:
        provider is moving slower than expected.

    Factor < 1:
        provider is moving faster than expected.
    """

    if (
        provider_speed_kmh is None
        or route_distance_meters <= 0
        or route_duration_seconds <= 0
    ):
        return 1.0

    route_speed_kmh = (
        route_distance_meters
        / route_duration_seconds
        * 3.6
    )

    if (
        route_speed_kmh <= 0
        or not math.isfinite(route_speed_kmh)
    ):
        return 1.0

    factor = (
        route_speed_kmh
        / provider_speed_kmh
    )

    return _clamp(
        factor,
        MIN_FACTOR,
        MAX_FACTOR,
    )


# =========================================================
# MAIN AI ETA PREDICTION
# =========================================================

def predict_eta(
    provider_id: int,
    latitude: float,
    longitude: float,
    distance_meters: Any,
    duration: Any,
) -> Dict[str, Any]:
    """
    Adaptive ResQDrive ETA prediction.

    Inputs:
        provider_id
        current provider GPS
        Google route distance
        Google route duration

    Returns:
        predicted_eta
        predicted_duration
        confidence
        observed_speed_kmh
        adjustment_factor
        samples
    """

    distance = _safe_float(
        distance_meters
    )

    route_seconds = _duration_to_seconds(
        duration
    )

    # -----------------------------------------------------
    # VALIDATE ROUTE DATA
    # -----------------------------------------------------
    if (
        distance is None
        or distance < MIN_VALID_DISTANCE_METERS
    ):
        return {
            "predicted_eta": None,
            "predicted_duration": None,
            "confidence": 0,
            "observed_speed_kmh": None,
            "adjustment_factor": 1.0,
            "samples": 0,
            "source": "ai_eta_unavailable",
        }

    # Always record the GPS sample before handling a very
    # short / zero-second route. This keeps the provider's
    # adaptive state consistent.
    observed_speed = _update_provider_speed(
        provider_id,
        latitude,
        longitude,
    )

    state = _get_provider_state(
        provider_id
    )

    # -----------------------------------------------------
    # PROVIDER IS AT / VERY CLOSE TO DESTINATION
    # -----------------------------------------------------
    # Google can legitimately return "0s" when the provider
    # is only a few meters from the emergency location.
    # This is not an AI failure. Treat it as an immediate
    # arrival instead of returning "AI unavailable".
    if route_seconds is None or route_seconds < MIN_VALID_DURATION_SECONDS:
        if distance <= 10.0:
            samples = int(state.get("samples", 0))

            return {
                "predicted_eta": "< 1 min",
                "predicted_duration": "1s",
                "confidence": 95,
                "observed_speed_kmh": (
                    round(observed_speed, 2)
                    if observed_speed is not None
                    else None
                ),
                "adjustment_factor": 1.0,
                "samples": samples,
                "source": "resqdrive_adaptive_eta",
            }

        # A zero/invalid duration for a meaningful route is
        # not enough information for an honest prediction.
        return {
            "predicted_eta": None,
            "predicted_duration": None,
            "confidence": 0,
            "observed_speed_kmh": (
                round(observed_speed, 2)
                if observed_speed is not None
                else None
            ),
            "adjustment_factor": 1.0,
            "samples": int(state.get("samples", 0)),
            "source": "ai_eta_unavailable",
        }

    raw_factor = _calculate_eta_factor(
        provider_speed_kmh=observed_speed,
        route_distance_meters=distance,
        route_duration_seconds=route_seconds,
    )

    previous_factor = state.get(
        "eta_factor",
        1.0,
    )

    adjusted_factor = (
        SMOOTHING_ALPHA * raw_factor
        + (1 - SMOOTHING_ALPHA)
        * previous_factor
    )

    adjusted_factor = _clamp(
        adjusted_factor,
        MIN_FACTOR,
        MAX_FACTOR,
    )

    state["eta_factor"] = adjusted_factor

    samples = int(
        state.get("samples", 0)
    )

    predicted_seconds = (
        route_seconds
        * adjusted_factor
    )

    predicted_eta = _seconds_to_eta(
        predicted_seconds
    )

    predicted_duration = _seconds_to_duration(
        predicted_seconds
    )

    # -----------------------------------------------------
    # CONFIDENCE
    # -----------------------------------------------------

    if samples <= 0:
        confidence = 55

    elif samples == 1:
        confidence = 65

    elif samples <= 3:
        confidence = 75

    elif samples <= 6:
        confidence = 85

    else:
        confidence = 92

    return {
        "predicted_eta": predicted_eta,
        "predicted_duration": predicted_duration,
        "confidence": confidence,
        "observed_speed_kmh": (
            round(observed_speed, 2)
            if observed_speed is not None
            else None
        ),
        "adjustment_factor": round(
            adjusted_factor,
            3,
        ),
        "samples": samples,
        "source": "resqdrive_adaptive_eta",
    }


# =========================================================
# RESET PROVIDER STATE
# =========================================================

def reset_provider_eta(
    provider_id: int,
) -> None:
    """
    Clear learned ETA state when a trip finishes.
    """

    _provider_state.pop(
        provider_id,
        None,
    )


# =========================================================
# DEBUG / TEST
# =========================================================

if __name__ == "__main__":

    result = predict_eta(
        provider_id=7,
        latitude=17.5015,
        longitude=78.4225,
        distance_meters=3287,
        duration="774s",
    )

    print()
    print("=" * 60)
    print("🤖 RESQDRIVE AI ETA PREDICTION")
    print("=" * 60)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("=" * 60)