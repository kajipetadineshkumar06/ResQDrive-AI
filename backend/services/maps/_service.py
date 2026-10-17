import os
import requests
from dotenv import load_dotenv
from pathlib import Path


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=False)


API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

ROUTES_URL = (
    "https://routes.googleapis.com/"
    "directions/v2:computeRoutes"
)


# =========================================================
# GOOGLE ROUTES API
# =========================================================

def get_route(
    origin_lat,
    origin_lng,
    dest_lat,
    dest_lng
):
    """
    Calculate driving route between two locations.

    Returns:
        {
            "distance_meters": int,
            "duration": "123s",
            "polyline": "encoded_polyline"
        }

    Returns None if Google Routes API fails.
    """

    # -----------------------------------------------------
    # CHECK API KEY
    # -----------------------------------------------------

    if not API_KEY:

        print(
            "❌ GOOGLE_MAPS_API_KEY is not configured."
        )

        return None

    # -----------------------------------------------------
    # CONVERT COORDINATES
    # -----------------------------------------------------

    try:

        origin_lat = float(origin_lat)
        origin_lng = float(origin_lng)

        dest_lat = float(dest_lat)
        dest_lng = float(dest_lng)

    except (TypeError, ValueError):

        print(
            "❌ Invalid coordinates supplied to get_route()"
        )

        return None

    # -----------------------------------------------------
    # VALIDATE COORDINATES
    # -----------------------------------------------------

    if not -90 <= origin_lat <= 90:

        print(
            "❌ Invalid origin latitude"
        )

        return None

    if not -90 <= dest_lat <= 90:

        print(
            "❌ Invalid destination latitude"
        )

        return None

    if not -180 <= origin_lng <= 180:

        print(
            "❌ Invalid origin longitude"
        )

        return None

    if not -180 <= dest_lng <= 180:

        print(
            "❌ Invalid destination longitude"
        )

        return None

    # -----------------------------------------------------
    # HEADERS
    # -----------------------------------------------------

    headers = {

        "Content-Type": "application/json",

        "X-Goog-Api-Key": API_KEY,

        "X-Goog-FieldMask": (
            "routes.distanceMeters,"
            "routes.duration,"
            "routes.polyline.encodedPolyline"
        )
    }

    # -----------------------------------------------------
    # REQUEST BODY
    # -----------------------------------------------------

    body = {

        "origin": {

            "location": {

                "latLng": {

                    "latitude": origin_lat,

                    "longitude": origin_lng
                }
            }
        },

        "destination": {

            "location": {

                "latLng": {

                    "latitude": dest_lat,

                    "longitude": dest_lng
                }
            }
        },

        "travelMode": "DRIVE",

        "routingPreference": "TRAFFIC_AWARE",

        "computeAlternativeRoutes": False,

        "routeModifiers": {

            "avoidTolls": False,

            "avoidHighways": False,

            "avoidFerries": False
        },

        "languageCode": "en-US",

        "units": "METRIC"
    }

    # -----------------------------------------------------
    # SEND REQUEST
    # -----------------------------------------------------

    try:

        response = requests.post(

            ROUTES_URL,

            json=body,

            headers=headers,

            timeout=10
        )

    except requests.exceptions.Timeout:

        print(
            "❌ Google Routes API request timed out."
        )

        return None

    except requests.exceptions.RequestException:
        print("Google Routes API network request failed.")
        return None

    # GOOGLE ERROR
    # -----------------------------------------------------

    if response.status_code != 200:
        print(f"Google Routes API returned HTTP {response.status_code}.")
        return None

    # PARSE JSON
    # -----------------------------------------------------

    try:

        data = response.json()

    except ValueError:
        print("Google Routes API returned invalid JSON.")
        return None

    # CHECK ROUTES
    # -----------------------------------------------------

    routes = data.get("routes")

    if not routes:
        print("Google Routes API returned no routes.")
        return None

    # GET FIRST ROUTE
    # -----------------------------------------------------

    route = routes[0]

    # -----------------------------------------------------
    # DISTANCE
    # -----------------------------------------------------

    distance_meters = route.get(
        "distanceMeters"
    )

    # -----------------------------------------------------
    # DURATION
    # -----------------------------------------------------

    duration = route.get(
        "duration"
    )

    # -----------------------------------------------------
    # POLYLINE
    # -----------------------------------------------------

    polyline_data = route.get(
        "polyline",
        {}
    )

    polyline = polyline_data.get(
        "encodedPolyline"
    )

    # -----------------------------------------------------
    # CHECK REQUIRED VALUES
    # -----------------------------------------------------

    if distance_meters is None:

        print(
            "⚠️ Google route did not contain distance."
        )

        return None

    if duration is None:

        print(
            "⚠️ Google route did not contain duration."
        )

        return None

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    print(
        "✅ Google route calculated successfully."
    )

    print(
        f"📏 Distance: {distance_meters} meters"
    )

    print(
        f"⏱️ Duration: {duration}"
    )

    return {

        "distance_meters":
            int(distance_meters),

        "duration":
            duration,

        "polyline":
            polyline
    }