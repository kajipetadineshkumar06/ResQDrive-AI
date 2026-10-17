def recommend_service(emergency_type: str):

    mapping = {
        "breakdown": "mechanic",
        "accident": "towing",
        "fuel_out": "fuel_delivery",
        "flat_tyre": "tyre_repair",
        "battery": "battery",
        "medical": "ambulance"
    }

    return mapping.get(emergency_type, "mechanic")