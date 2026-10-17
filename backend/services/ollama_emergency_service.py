# ==========================================
# ResQDrive AI - Local Ollama Emergency AI
# ==========================================

import json
import logging
import urllib.request
import urllib.error

from deployment_config import get_ollama_settings


# ------------------------------------------
# OLLAMA CONFIGURATION
# ------------------------------------------

_OLLAMA_SETTINGS = get_ollama_settings()
OLLAMA_ENABLED = _OLLAMA_SETTINGS["enabled"]
OLLAMA_URL = _OLLAMA_SETTINGS["generate_url"]
OLLAMA_TAGS_URL = _OLLAMA_SETTINGS["tags_url"]
OLLAMA_MODEL = _OLLAMA_SETTINGS["model"]
OLLAMA_TIMEOUT_SECONDS = _OLLAMA_SETTINGS["timeout_seconds"]
logger = logging.getLogger(__name__)


# ------------------------------------------
# ALLOWED VALUES
# ------------------------------------------

ALLOWED_EMERGENCY_TYPES = {
    "flat_tire",
    "battery",
    "engine_failure",
    "overheating",
    "fuel_empty",
    "accident",
    "towing",
    "ev_charging",
    "medical",
    "other",
}

ALLOWED_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


# ------------------------------------------
# EMERGENCY CLASSIFICATION
# ------------------------------------------

def classify_emergency(description: str) -> dict:
    """
    Classify a roadside emergency using
    the local Ollama Qwen3 model.

    Returns:
        {
            "emergency_type": "...",
            "priority": "...",
            "confidence": 0,
            "source": "ollama_qwen3"
        }
    """

    # --------------------------------------
    # Validate input
    # --------------------------------------

    if not OLLAMA_ENABLED:
        return {
            "emergency_type": "other",
            "priority": "MEDIUM",
            "confidence": 0,
            "source": "ollama_disabled",
        }

    if not description or not description.strip():
        return {
            "emergency_type": "other",
            "priority": "MEDIUM",
            "confidence": 0,
            "source": "fallback",
        }

    # --------------------------------------
    # Prompt
    # --------------------------------------

    prompt = f"""
You are the emergency classification AI
for a roadside assistance application called
ResQDrive AI.

Analyze this emergency description:

"{description.strip()}"

Choose exactly ONE emergency_type:

flat_tire
battery
engine_failure
overheating
fuel_empty
accident
towing
ev_charging
medical
other

Choose exactly ONE priority:

LOW
MEDIUM
HIGH
CRITICAL

Rules:

- CRITICAL:
  Immediate danger, accident with injuries,
  fire, severe overheating, or medical emergency.

- HIGH:
  Vehicle cannot continue safely, engine failure,
  dead battery, fuel problem, serious breakdown.

- MEDIUM:
  Flat tyre, minor vehicle issue, towing request
  without immediate danger.

- LOW:
  Minor issue that does not prevent safe travel.

Return ONLY valid JSON.

Do not return markdown.
Do not return explanations.
Do not use code fences.

Required format:

{{
    "emergency_type": "flat_tire",
    "priority": "MEDIUM",
    "confidence": 95
}}

Confidence must be an integer between 0 and 100.
"""

    # --------------------------------------
    # Ollama request
    # --------------------------------------

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:

        request_data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            OLLAMA_URL,
            data=request_data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        # ----------------------------------
        # Call local Ollama server
        # ----------------------------------

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS
        ) as response:

            response_data = response.read().decode("utf-8")

        result = json.loads(response_data)

        # ----------------------------------
        # Extract model response
        # ----------------------------------

        ai_response = result.get(
            "response",
            ""
        ).strip()

        if not ai_response:
            raise ValueError(
                "Ollama returned an empty response"
            )

        parsed = json.loads(ai_response)

        # ----------------------------------
        # Extract values
        # ----------------------------------

        emergency_type = str(
            parsed.get(
                "emergency_type",
                "other"
            )
        ).lower().strip()

        priority = str(
            parsed.get(
                "priority",
                "MEDIUM"
            )
        ).upper().strip()

        confidence_value = parsed.get(
            "confidence",
            50
        )

        try:
            confidence = int(
                float(confidence_value)
            )
        except (
            ValueError,
            TypeError
        ):
            confidence = 50

        # ----------------------------------
        # Validate emergency type
        # ----------------------------------

        if emergency_type not in ALLOWED_EMERGENCY_TYPES:
            emergency_type = "other"

        # ----------------------------------
        # Validate priority
        # ----------------------------------

        if priority not in ALLOWED_PRIORITIES:
            priority = "MEDIUM"

        # ----------------------------------
        # Limit confidence
        # ----------------------------------

        confidence = max(
            0,
            min(
                100,
                confidence
            )
        )

        # ----------------------------------
        # Successful result
        # ----------------------------------

        return {
            "emergency_type": emergency_type,
            "priority": priority,
            "confidence": confidence,
            "source": "ollama_qwen3",
        }

    # --------------------------------------
    # Ollama connection error
    # --------------------------------------

    except urllib.error.URLError as error:

        logger.warning("Ollama emergency request failed; using fallback (%s).", type(error).__name__)

        return {
            "emergency_type": "other",
            "priority": "MEDIUM",
            "confidence": 0,
            "source": "ollama_unavailable",
        }

    # --------------------------------------
    # Timeout
    # --------------------------------------

    except TimeoutError:

        logger.warning("Ollama emergency request timed out; using fallback.")

        return {
            "emergency_type": "other",
            "priority": "MEDIUM",
            "confidence": 0,
            "source": "ollama_timeout",
        }

    # --------------------------------------
    # Invalid JSON / other error
    # --------------------------------------

    except Exception as error:

        logger.warning("Ollama emergency classification failed; using fallback (%s).", type(error).__name__)

        return {
            "emergency_type": "other",
            "priority": "MEDIUM",
            "confidence": 0,
            "source": "ollama_error",
        }


# ------------------------------------------
# SIMPLE HEALTH CHECK
# ------------------------------------------

def ollama_available() -> bool:
    """
    Check whether the local Ollama server
    is available.
    """

    if not OLLAMA_ENABLED:
        return False

    try:

        request = urllib.request.Request(
            OLLAMA_TAGS_URL,
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS
        ) as response:

            if response.status == 200:
                data = json.loads(
                    response.read().decode("utf-8")
                )

                models = data.get(
                    "models",
                    []
                )

                for model in models:

                    if model.get(
                        "name"
                    ) == OLLAMA_MODEL:

                        return True

        return False

    except Exception as error:

        logger.warning("Ollama health check failed (%s).", type(error).__name__)

        return False


# ------------------------------------------
# LOCAL TEST
# ------------------------------------------

if __name__ == "__main__":

    print("=" * 50)
    print("ResQDrive AI - Ollama Test")
    print("=" * 50)

    print()

    print(
        f"Model: {OLLAMA_MODEL}"
    )

    print(
        f"Ollama URL: {OLLAMA_URL}"
    )

    print()

    # Check Ollama
    if ollama_available():

        print(
            "✅ Ollama is available"
        )

    else:

        print(
            "❌ Ollama is not available"
        )

        print(
            "Make sure Ollama is running."
        )

        raise SystemExit(1)

    print()

    # Test emergency
    test_description = (
        "My car has a flat tyre and "
        "I cannot continue driving."
    )

    print(
        "Test description:"
    )

    print(
        test_description
    )

    print()

    result = classify_emergency(
        test_description
    )

    print(
        "AI Result:"
    )

    print(
        json.dumps(
            result,
            indent=4
        )
    )

    print()

    print("=" * 50)
    print("Test completed")
    print("=" * 50)