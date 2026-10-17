import os
import requests

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=False)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def get_route(
    origin_lat,
    origin_lng,
    destination_lat,
    destination_lng
):
    """
    Returns:
    {
        success: bool,
        distance_meters: int,
        duration: str,
        polyline: str
    }
    """

    if not GOOGLE_MAPS_API_KEY:
        return {
            "success": False,
            "error": "Google Maps API key not found."
        }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "routes.distanceMeters,"
            "routes.duration,"
            "routes.polyline.encodedPolyline"
        )
    }

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": float(origin_lat),
                    "longitude": float(origin_lng)
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": float(destination_lat),
                    "longitude": float(destination_lng)
                }
            }
        },
        "travelMode": "DRIVE"
    }

    try:

        response = requests.post(
            URL,
            headers=headers,
            json=body,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if "routes" not in data or len(data["routes"]) == 0:
            return {
                "success": False,
                "error": "No route found."
            }

        route = data["routes"][0]

        return {
            "success": True,
            "distance_meters": route["distanceMeters"],
            "duration": route["duration"],
            "polyline": route["polyline"]["encodedPolyline"]
        }

    except requests.exceptions.HTTPError as error:
        response = error.response
        status_code = response.status_code if response is not None else None
        message = (
            f"Google Routes API returned HTTP {status_code}."
            if status_code is not None
            else "Google Routes API request failed."
        )
        return {
            "success": False,
            "error": message,
        }

    except requests.exceptions.RequestException:
        return {
            "success": False,
            "error": "Google Routes API network request failed.",
        }
