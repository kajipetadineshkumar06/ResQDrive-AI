import re

from services.maps._service import get_route


# =========================================================
# CONVERT GOOGLE DURATION
# =========================================================

def duration_to_minutes(duration):
    """
    Convert Google duration such as:

        123s

    into:

        2 min
    """

    if not duration:

        return None

    try:

        match = re.match(
            r"([0-9]+(?:\.[0-9]+)?)s",
            str(duration)
        )

        if not match:

            return None

        seconds = float(
            match.group(1)
        )

        minutes = round(
            seconds / 60
        )

        if minutes <= 0:

            return "< 1 min"

        return f"{minutes} min"

    except Exception:

        return None


# =========================================================
# CALCULATE LIVE ETA
# =========================================================

def calculate_live_eta(
    provider_lat,
    provider_lng,
    emergency_lat,
    emergency_lng
):
    """
    Calculate:

    Provider → Emergency

    Returns:

        distance_meters
        eta
        duration
        polyline
    """

    route = get_route(

        origin_lat=provider_lat,

        origin_lng=provider_lng,

        dest_lat=emergency_lat,

        dest_lng=emergency_lng
    )

    # -----------------------------------------------------
    # ROUTE FAILED
    # -----------------------------------------------------

    if not route:

        print(
            "⚠️ Live route unavailable."
        )

        return {

            "distance_meters": None,

            "eta": None,

            "duration": None,

            "polyline": None
        }

    # -----------------------------------------------------
    # GET DATA
    # -----------------------------------------------------

    distance_meters = route.get(
        "distance_meters"
    )

    duration = route.get(
        "duration"
    )

    polyline = route.get(
        "polyline"
    )

    # -----------------------------------------------------
    # CONVERT ETA
    # -----------------------------------------------------

    eta = duration_to_minutes(
        duration
    )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {

        "distance_meters":
            distance_meters,

        "eta":
            eta,

        "duration":
            duration,

        "polyline":
            polyline
    }