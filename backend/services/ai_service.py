# ==========================================
# services/ai_service.py
# ==========================================


# ==========================================
# AI VEHICLE DIAGNOSIS
# ==========================================

def diagnose_vehicle(symptoms: str):
    """
    Analyze vehicle symptoms and provide:

    - Diagnosis
    - Possible causes
    - Recommended service
    - Priority
    - Confidence
    - Safety advice

    This is currently a rule-based diagnosis system.
    """

    # ------------------------------------------
    # CLEAN INPUT
    # ------------------------------------------

    symptoms = symptoms.lower().strip()

    # ==========================================
    # EV CHARGING / EV BATTERY
    # Check this BEFORE normal battery
    # ==========================================

    ev_words = [
        "ev battery",
        "electric car",
        "electric vehicle",
        "ev battery low",
        "ev not charging",
        "ev charging",
        "charging problem",
        "charging issue",
        "not charging",
        "charge problem",
        "charge issue",
        "charging",
        "charge",
        "battery percentage",
    ]

    if any(word in symptoms for word in ev_words):

        return {
            "diagnosis": "Possible EV charging or battery issue",

            "possible_causes": [
                "Low EV battery",
                "Charging cable problem",
                "Charging station issue",
                "Vehicle charging system problem",
            ],

            "recommended_service": "ev_charging",

            "priority": "high",

            "confidence": 82,

            "advice": (
                "If the EV battery is critically low, request "
                "EV charging assistance and avoid travelling "
                "long distances."
            ),
        }

    # ==========================================
    # BATTERY PROBLEM
    # ==========================================

    battery_words = [
        "battery",
        "clicking",
        "click",
        "no start",
        "won't start",
        "wont start",
        "dead battery",
        "battery dead",
        "weak battery",
        "dim lights",
        "battery problem",
        "starting problem",
    ]

    if any(word in symptoms for word in battery_words):

        return {
            "diagnosis": "Possible battery problem",

            "possible_causes": [
                "Weak or discharged battery",
                "Battery terminal problem",
                "Alternator charging problem",
                "Electrical system issue",
            ],

            "recommended_service": "battery",

            "priority": "high",

            "confidence": 85,

            "advice": (
                "Avoid repeatedly attempting to start the vehicle. "
                "A battery service provider should inspect the battery "
                "and charging system."
            ),
        }

    # ==========================================
    # FLAT TYRE
    # ==========================================

    tyre_words = [
        "flat tire",
        "flat tyre",
        "puncture",
        "punctured tire",
        "punctured tyre",
        "tyre problem",
        "tire problem",
        "tyre damaged",
        "tire damaged",
        "low tyre pressure",
        "low tire pressure",
    ]

    if any(word in symptoms for word in tyre_words):

        return {
            "diagnosis": "Possible flat or punctured tyre",

            "possible_causes": [
                "Tyre puncture",
                "Air pressure loss",
                "Damaged tyre valve",
                "Tyre damage",
            ],

            "recommended_service": "tire",

            "priority": "medium",

            "confidence": 90,

            "advice": (
                "Avoid driving on a severely damaged or flat tyre. "
                "Request roadside tyre or mechanic assistance."
            ),
        }

    # ==========================================
    # OVERHEATING
    # ==========================================

    overheating_words = [
        "overheating",
        "overheated",
        "engine hot",
        "engine temperature",
        "temperature warning",
        "hot engine",
        "coolant",
        "steam",
        "smoke from engine",
        "engine overheating",
        "temperature high",
    ]

    if any(word in symptoms for word in overheating_words):

        return {
            "diagnosis": "Possible engine overheating",

            "possible_causes": [
                "Low coolant",
                "Cooling system failure",
                "Radiator problem",
                "Thermostat problem",
                "Engine cooling fan failure",
            ],

            "recommended_service": "mechanic",

            "priority": "critical",

            "confidence": 90,

            "advice": (
                "Stop the vehicle in a safe location and switch off "
                "the engine. Do not open the radiator cap while the "
                "engine is hot."
            ),
        }

    # ==========================================
    # FUEL PROBLEM
    # ==========================================

    fuel_words = [
        "out of fuel",
        "out of petrol",
        "out of diesel",
        "no fuel",
        "empty tank",
        "fuel finished",
        "fuel empty",
        "petrol empty",
        "diesel empty",
        "ran out of fuel",
    ]

    if any(word in symptoms for word in fuel_words):

        return {
            "diagnosis": "Vehicle may be out of fuel",

            "possible_causes": [
                "Fuel tank empty",
                "Incorrect fuel level reading",
                "Fuel delivery problem",
            ],

            "recommended_service": "fuel_delivery",

            "priority": "high",

            "confidence": 95,

            "advice": (
                "Move the vehicle to a safe location if possible "
                "and request fuel delivery assistance."
            ),
        }

    # ==========================================
    # ENGINE FAILURE
    # ==========================================

    engine_words = [
        "engine stopped",
        "engine failure",
        "engine problem",
        "engine not working",
        "car stopped",
        "vehicle stopped",
        "breakdown",
        "vehicle breakdown",
        "engine failed",
        "mechanical failure",
        "car breakdown",
    ]

    if any(word in symptoms for word in engine_words):

        return {
            "diagnosis": "Possible engine or mechanical failure",

            "possible_causes": [
                "Engine malfunction",
                "Fuel system problem",
                "Electrical problem",
                "Mechanical component failure",
            ],

            "recommended_service": "mechanic",

            "priority": "high",

            "confidence": 75,

            "advice": (
                "Do not continue driving if the vehicle is unsafe. "
                "Request mechanic assistance for inspection."
            ),
        }

    # ==========================================
    # UNKNOWN PROBLEM
    # ==========================================

    return {
        "diagnosis": "Vehicle problem requires further inspection",

        "possible_causes": [
            "Mechanical problem",
            "Electrical problem",
            "Fuel system problem",
            "Unknown vehicle fault",
        ],

        "recommended_service": "mechanic",

        "priority": "medium",

        "confidence": 50,

        "advice": (
            "Provide more information about the warning lights, "
            "sounds, smells, and vehicle behaviour."
        ),
    }


# ==========================================
# PROVIDER TYPE RECOMMENDATION
# ==========================================

def recommend_provider_type(emergency_type: str):
    """
    Decide which type of roadside provider
    should handle the emergency.

    This function receives the normalized
    emergency type from emergency_service.py.
    """

    # ==========================================
    # EMPTY INPUT
    # ==========================================

    if not emergency_type:
        return "mechanic"

    emergency_type = emergency_type.strip().lower()

    # ==========================================
    # PROVIDER MAPPING
    # ==========================================

    mapping = {

        # --------------------------------------
        # BATTERY
        # --------------------------------------

        "battery": "battery",

        "dead_battery": "battery",

        "battery_problem": "battery",


        # --------------------------------------
        # FLAT TYRE / TIRE
        # --------------------------------------

        "flat_tyre": "tire",

        "flat_tire": "tire",

        "tyre": "tire",

        "tire": "tire",

        "puncture": "tire",


        # --------------------------------------
        # BREAKDOWN
        # --------------------------------------

        "breakdown": "mechanic",

        "vehicle_breakdown": "mechanic",

        "engine": "mechanic",

        "engine_problem": "mechanic",

        "engine_failure": "mechanic",

        "mechanical": "mechanic",

        "mechanical_problem": "mechanic",

        "overheating": "mechanic",

        "vehicle_problem": "mechanic",


        # --------------------------------------
        # FUEL
        # --------------------------------------

        "fuel": "fuel_delivery",

        "fuel_out": "fuel_delivery",

        "fuel_shortage": "fuel_delivery",

        "fuel_empty": "fuel_delivery",

        "fuel_delivery": "fuel_delivery",


        # --------------------------------------
        # EV CHARGING
        # --------------------------------------

        "ev": "ev_charging",

        "charging": "ev_charging",

        "ev_charging": "ev_charging",

        "ev_battery": "ev_charging",


        # --------------------------------------
        # ACCIDENT
        # --------------------------------------

        "accident": "towing",

        "road_accident": "towing",


        # --------------------------------------
        # MEDICAL
        # --------------------------------------

        "medical": "ambulance",

        "medical_emergency": "ambulance",

        "ambulance": "ambulance",

        "injury": "ambulance",

        "accident_injury": "ambulance",


        # --------------------------------------
        # TOWING
        # --------------------------------------

        "towing": "towing",

        "tow": "towing",

        "vehicle_stuck": "towing",

        "stuck_vehicle": "towing",

        "lockout": "towing",

        "vehicle_lockout": "towing",


        # --------------------------------------
        # OTHER
        # --------------------------------------

        "other": "mechanic",
    }

    # ==========================================
    # RETURN PROVIDER TYPE
    # ==========================================

    return mapping.get(
        emergency_type,
        "mechanic"
    )