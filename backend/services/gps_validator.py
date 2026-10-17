# services/gps_validator.py

ARRIVAL_RADIUS = 30  # meters


def is_valid_location(latitude, longitude):
    """
    Validate GPS coordinates.
    """

    if latitude is None or longitude is None:
        return False

    latitude = float(latitude)
    longitude = float(longitude)

    if latitude < -90 or latitude > 90:
        return False

    if longitude < -180 or longitude > 180:
        return False

    return True


def has_reached(distance):
    """
    Check whether provider has reached destination.
    """

    return float(distance) <= ARRIVAL_RADIUS