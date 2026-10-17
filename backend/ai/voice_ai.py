def analyze_voice(text):

    text = text.lower()


    if "battery" in text or "not starting" in text:
        return {
            "issue":"battery",
            "service":"Battery",
            "priority":"high"
        }


    elif "fuel" in text or "petrol" in text:
        return {
            "issue":"fuel_out",
            "service":"Fuel Delivery",
            "priority":"medium"
        }


    elif "accident" in text or "crash" in text:
        return {
            "issue":"accident",
            "service":"Ambulance",
            "priority":"critical"
        }


    elif "tyre" in text or "puncture" in text:
        return {
            "issue":"flat_tyre",
            "service":"Tyre Repair",
            "priority":"medium"
        }


    else:
        return {
            "issue":"breakdown",
            "service":"Mechanic",
            "priority":"medium"
        }