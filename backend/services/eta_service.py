from math import radians, sin, cos, sqrt, atan2

EARTH_RADIUS = 6371  # kilometers


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates using Haversine Formula.
    Returns distance in kilometers.
    """

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))

    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS * c


def calculate_eta(distance_km, speed_kmph=40):
    """
    Calculate ETA in minutes.

    Default mechanic speed = 40 km/h
    """

    if speed_kmph <= 0:
        return None

    hours = distance_km / speed_kmph

    return round(hours * 60)