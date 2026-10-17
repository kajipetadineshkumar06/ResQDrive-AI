# ============================================================
# ResQDrive AI - Vehicle NLP / LLM Service
# ============================================================
#
# Purpose:
# Analyze a customer's natural-language vehicle problem
# using local Ollama + Qwen3 8B.
#
# Example:
# "My car is making a grinding noise when I press the brakes."
#
# Returns structured information:
# - vehicle_problem
# - component
# - symptoms
# - possible_causes
# - required_service
# - priority
# - safety_advice
# - confidence
# - source
#
# No paid API is required.
# ============================================================

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from deployment_config import get_ollama_settings


# ============================================================
# OLLAMA CONFIGURATION
# ============================================================

_OLLAMA_SETTINGS = get_ollama_settings()
OLLAMA_ENABLED = _OLLAMA_SETTINGS["enabled"]
OLLAMA_URL = _OLLAMA_SETTINGS["generate_url"]
OLLAMA_MODEL = _OLLAMA_SETTINGS["model"]
OLLAMA_TIMEOUT_SECONDS = _OLLAMA_SETTINGS["timeout_seconds"]
logger = logging.getLogger(__name__)


# ============================================================
# ALLOWED VALUES
# ============================================================

ALLOWED_SERVICES = {
    "mechanic",
    "battery",
    "tyre",
    "towing",
    "fuel",
    "ev_charging",
    "roadside_assistance",
    "other",
}

ALLOWED_PRIORITIES = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


# ============================================================
# DEFAULT RESPONSE
# ============================================================

def _fallback_result(
    problem: str,
    reason: str = "fallback",
) -> dict[str, Any]:

    return {
        "vehicle_problem": problem,
        "component": "unknown",
        "symptoms": [],
        "possible_causes": [],
        "required_service": "roadside_assistance",
        "priority": "MEDIUM",
        "safety_advice": (
            "Move to a safe location if possible. "
            "Avoid driving if the vehicle appears unsafe."
        ),
        "confidence": 0,
        "source": reason,
    }


# ============================================================
# EXTRACT JSON FROM MODEL RESPONSE
# ============================================================

def _extract_json(text: str) -> dict[str, Any] | None:

    if not text:
        return None

    cleaned = text.strip()

    # --------------------------------------------------------
    # Remove markdown code fences if the model adds them
    # --------------------------------------------------------

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    cleaned = cleaned.strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Find JSON object inside surrounding text
    # --------------------------------------------------------

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    candidate = cleaned[start:end + 1]

    try:

        parsed = json.loads(candidate)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        return None

    return None


# ============================================================
# NORMALIZE LIST VALUES
# ============================================================

def _normalize_list(value: Any) -> list[str]:

    if isinstance(value, list):

        result = []

        for item in value:

            if item is None:
                continue

            item_text = str(item).strip()

            if item_text:
                result.append(item_text)

        return result[:10]

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return []

        return [value]

    return []


# ============================================================
# NORMALIZE SERVICE
# ============================================================

def _normalize_service(value: Any) -> str:

    if not isinstance(value, str):
        return "roadside_assistance"

    value = value.strip().lower()

    aliases = {
        "mechanic": "mechanic",
        "mechanical": "mechanic",
        "engine": "mechanic",
        "car mechanic": "mechanic",

        "battery": "battery",
        "battery service": "battery",

        "tyre": "tyre",
        "tire": "tyre",
        "puncture": "tyre",

        "towing": "towing",
        "tow": "towing",

        "fuel": "fuel",
        "fuel delivery": "fuel",

        "ev": "ev_charging",
        "ev charging": "ev_charging",
        "electric vehicle charging": "ev_charging",

        "roadside": "roadside_assistance",
        "roadside assistance": "roadside_assistance",
    }

    normalized = aliases.get(
        value,
        value,
    )

    if normalized not in ALLOWED_SERVICES:
        return "other"

    return normalized


# ============================================================
# NORMALIZE PRIORITY
# ============================================================

def _normalize_priority(value: Any) -> str:

    if not isinstance(value, str):
        return "MEDIUM"

    value = value.strip().upper()

    aliases = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "MODERATE": "MEDIUM",
        "HIGH": "HIGH",
        "URGENT": "HIGH",
        "CRITICAL": "CRITICAL",
        "EMERGENCY": "CRITICAL",
    }

    normalized = aliases.get(
        value,
        "MEDIUM",
    )

    if normalized not in ALLOWED_PRIORITIES:
        return "MEDIUM"

    return normalized


# ============================================================
# NORMALIZE CONFIDENCE
# ============================================================

def _normalize_confidence(value: Any) -> int:

    try:

        confidence = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return 0

    # Handle values such as 0.91
    if 0 < confidence <= 1:
        confidence *= 100

    confidence = max(
        0,
        min(
            95,
            confidence,
        ),
    )

    return int(round(confidence))


# ============================================================
# BUILD SAFE RESULT
# ============================================================

def _normalize_result(
    problem: str,
    data: dict[str, Any],
) -> dict[str, Any]:

    vehicle_problem = data.get(
        "vehicle_problem"
    )

    if not isinstance(
        vehicle_problem,
        str,
    ) or not vehicle_problem.strip():

        vehicle_problem = problem

    component = data.get(
        "component",
        "unknown",
    )

    if not isinstance(
        component,
        str,
    ) or not component.strip():

        component = "unknown"

    safety_advice = data.get(
        "safety_advice",
        (
            "Move to a safe location if possible. "
            "Avoid driving if the vehicle appears unsafe."
        ),
    )

    if not isinstance(
        safety_advice,
        str,
    ) or not safety_advice.strip():

        safety_advice = (
            "Move to a safe location if possible. "
            "Avoid driving if the vehicle appears unsafe."
        )

    return {
        "vehicle_problem": vehicle_problem.strip(),

        "component": component.strip(),

        "symptoms": _normalize_list(
            data.get("symptoms")
        ),

        "possible_causes": _normalize_list(
            data.get("possible_causes")
        ),

        "required_service": _normalize_service(
            data.get("required_service")
        ),

        "priority": _normalize_priority(
            data.get("priority")
        ),

        "safety_advice": safety_advice.strip(),

        "confidence": _normalize_confidence(
            data.get("confidence")
        ),

        "source": "ollama_qwen3",
    }


# ============================================================
# OLLAMA REQUEST
# ============================================================

def _call_ollama(
    prompt: str,
) -> str | None:

    if not OLLAMA_ENABLED:
        return None

    payload = {
        "model": OLLAMA_MODEL,

        "prompt": prompt,

        # Qwen3 can spend a long time in thinking mode.
        # This task is structured extraction/classification,
        # so disable thinking for a faster response.
        "think": False,

        # Force Ollama to return JSON.
        "format": "json",

        "stream": False,

        # Keep the model loaded briefly between requests.
        "keep_alive": "5m",

        "options": {
            "temperature": 0.1,
        },
    }

    request_data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=request_data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        ) as response:

            response_body = response.read()

        decoded = json.loads(
            response_body.decode("utf-8")
        )

        result = decoded.get(
            "response"
        )

        if isinstance(
            result,
            str,
        ):

            return result

        print(
            "⚠️ Vehicle AI Ollama response did not contain text."
        )

        return None

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:

        logger.warning("Vehicle AI request failed; using fallback (%s).", type(error).__name__)

        return None

    except Exception as error:

        logger.warning("Vehicle AI request failed; using fallback (%s).", type(error).__name__)

        return None


# ============================================================
# MAIN VEHICLE AI FUNCTION
# ============================================================

def analyze_vehicle_problem(
    problem: str,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(
        problem,
        str,
    ):

        return _fallback_result(
            "Unknown vehicle problem",
            "vehicle_ai_invalid_input",
        )

    problem = problem.strip()

    if not problem:

        return _fallback_result(
            "Unknown vehicle problem",
            "vehicle_ai_empty_input",
        )

    # --------------------------------------------------------
    # Limit input size
    # --------------------------------------------------------

    problem = problem[:2000]

    # --------------------------------------------------------
    # LLM prompt
    # --------------------------------------------------------

    prompt = f"""
You are the ResQDrive AI Vehicle Assistance Analyzer.

Analyze the customer's vehicle problem.

Your job is NOT to provide a guaranteed mechanical diagnosis.
Identify likely symptoms and possible causes only.

Never invent a specific vehicle component if the customer's
description does not provide enough evidence.

Return ONLY valid JSON.

Required JSON format:

{{
  "vehicle_problem": "short description",
  "component": "likely vehicle component or unknown",
  "symptoms": [
    "symptom 1",
    "symptom 2"
  ],
  "possible_causes": [
    "possible cause 1",
    "possible cause 2"
  ],
  "required_service": "mechanic | battery | tyre | towing | fuel | ev_charging | roadside_assistance | other",
  "priority": "LOW | MEDIUM | HIGH | CRITICAL",
  "safety_advice": "short practical safety advice",
  "confidence": 0
}}

Rules:

1. Do not claim certainty.
2. Do not invent symptoms.
3. Do not invent vehicle details.
4. If the information is insufficient, use "unknown".
5. If there may be immediate danger such as smoke,
   fire, serious accident, severe overheating, brake failure,
   or another dangerous condition, use CRITICAL.
6. Use HIGH for serious problems that may become dangerous.
7. Use MEDIUM for normal roadside problems.
8. Use LOW only for minor/non-urgent problems.
9. Confidence must be an integer from 50 to 95 when
   there is enough information to analyze the problem.
10. Use confidence 0 only when the problem is too vague or
    insufficient information prevents a meaningful analysis.
11. Confidence is an estimate of how well the supplied symptoms
    support the extracted problem/service; do not use 100.
12. Keep the response concise.
13. Return JSON only.

Customer problem:

{problem}
"""

    # --------------------------------------------------------
    # Call local Qwen3
    # --------------------------------------------------------

    response = _call_ollama(
        prompt
    )

    if response is None:

        return _fallback_result(
            problem,
            "vehicle_ai_ollama_unavailable",
        )

    # --------------------------------------------------------
    # Parse model response
    # --------------------------------------------------------

    parsed = _extract_json(
        response
    )

    if parsed is None:

        print(
            "⚠️ Vehicle AI returned invalid JSON."
        )

        return _fallback_result(
            problem,
            "vehicle_ai_invalid_model_response",
        )

    # --------------------------------------------------------
    # Normalize and validate
    # --------------------------------------------------------

    return _normalize_result(
        problem,
        parsed,
    )


# ============================================================
# SIMPLE TEST HELPER
# ============================================================

def test_vehicle_ai() -> None:

    test_cases = [
        "My car is making a grinding noise when I press the brakes.",

        "My bike is not starting and I hear clicking sounds.",

        "My car engine is overheating and there is smoke.",

        "My tyre is completely flat.",

        "I ran out of fuel.",

        "My EV battery is low and I need charging.",

        "There is a warning light on my dashboard but I don't know what it means.",
    ]

    print(
        "\n"
        + "=" * 60
    )

    print(
        "RESQDRIVE AI - VEHICLE NLP TEST"
    )

    print(
        "=" * 60
    )

    for index, problem in enumerate(
        test_cases,
        start=1,
    ):

        print(
            f"\nTest {index}:"
        )

        print(
            f"Customer: {problem}"
        )

        result = analyze_vehicle_problem(
            problem
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

    print(
        "\n"
        + "=" * 60
    )


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    test_vehicle_ai()