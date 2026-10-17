# ==========================================
# ResQDrive AI
# Qwen3 Agent Planner
# Phase 3.3
# ==========================================

import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


# =========================================================
# OLLAMA CONFIGURATION
# =========================================================

OLLAMA_URL = "http://localhost:11434/api/generate"

OLLAMA_MODEL = "qwen3:8b"

OLLAMA_TIMEOUT_SECONDS = 180


# =========================================================
# ALLOWED ACTIONS
# =========================================================

ALLOWED_ACTIONS = {
    "get_emergency",
    "get_service_request",
    "get_provider",
    "find_available_providers",
    "calculate_route",
    "predict_eta",
    "none",
}


# =========================================================
# JSON EXTRACTION
# =========================================================

def _extract_json(
    text: str,
) -> Optional[Dict[str, Any]]:
    """
    Extract a JSON object from Qwen3 output.
    """

    if not text:
        return None

    cleaned = text.strip()

    # Remove markdown code fences.
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

    # Direct JSON.
    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # JSON inside surrounding text.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        return None

    if end <= start:
        return None

    candidate = cleaned[start:end + 1]

    try:
        parsed = json.loads(candidate)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        return None

    return None


# =========================================================
# NORMALIZE ACTION
# =========================================================

def _normalize_action(
    value: Any,
) -> str:
    """
    Normalize and validate the action returned by Qwen3.
    """

    if not isinstance(value, str):
        return "none"

    action = value.strip().lower()

    if action in ALLOWED_ACTIONS:
        return action

    return "none"


# =========================================================
# NORMALIZE ARGUMENTS
# =========================================================

def _normalize_arguments(
    value: Any,
) -> Dict[str, Any]:
    """
    Ensure tool arguments are always a dictionary.
    """

    if not isinstance(value, dict):
        return {}

    return value


# =========================================================
# BUILD PROMPT
# =========================================================

def _build_prompt(
    task: str,
    tools: List[Dict[str, str]],
) -> str:
    """
    Build a restricted tool-selection prompt.
    """

    tool_text = "\n".join(
        f"- {tool['name']}: {tool['description']}"
        for tool in tools
    )

    return f"""
You are the ResQDrive AI Agent Planner.

Your job is ONLY to decide which one controlled tool
should be used for the customer's task.

You are NOT allowed to:
- directly access the database
- invent emergency information
- invent provider information
- invent route information
- execute tools yourself
- create or modify records
- perform unsafe actions

You may select ONLY one of these tools:

{tool_text}

If the task cannot be handled by one of the available
tools, return action "none".

Return ONLY valid JSON.

Required format:

{{
  "action": "tool_name",
  "arguments": {{}},
  "reason": "short explanation",
  "confidence": 0
}}

Rules:

1. action MUST be one of the listed tool names or "none".
2. arguments MUST be a JSON object.
3. Do not invent IDs.
4. If an ID is explicitly present in the task, use it.
5. If a required ID is missing, use "none".
6. Keep reason short.
7. confidence must be an integer from 0 to 95.
8. Return JSON only.

Customer task:

{task}
"""


# =========================================================
# CALL OLLAMA
# =========================================================

def _call_ollama(
    prompt: str,
) -> Optional[str]:
    """
    Call local Ollama + Qwen3.

    Uses:
    - think=False
    - JSON format
    - low temperature
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "5m",
        "options": {
            "temperature": 0.1,
        },
    }

    body = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=body,
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

        if isinstance(result, str):
            return result

        print(
            "⚠️ Qwen3 planner response "
            "did not contain text."
        )

        return None

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:

        print(
            f"❌ Qwen3 planner Ollama error: "
            f"{error}"
        )

        return None

    except Exception as error:

        print(
            f"❌ Qwen3 planner unexpected error: "
            f"{error}"
        )

        return None


# =========================================================
# FALLBACK
# =========================================================

def _fallback_plan(
    task: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Safe fallback when Qwen3 is unavailable or
    returns invalid output.
    """

    return {
        "success": False,
        "action": "none",
        "arguments": {},
        "reason": reason,
        "confidence": 0,
        "source": "qwen3_planner_fallback",
        "task": task,
    }


# =========================================================
# MAIN PLANNER
# =========================================================

def plan_agent_action(
    task: str,
    tools: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Ask Qwen3 to select one controlled ResQDrive tool.

    This function ONLY plans.

    It does NOT execute the selected tool.
    """

    if not isinstance(
        task,
        str,
    ):
        return _fallback_plan(
            "unknown",
            "Invalid task input.",
        )

    task = task.strip()

    if not task:
        return _fallback_plan(
            task,
            "Task is empty.",
        )

    if not isinstance(
        tools,
        list,
    ) or not tools:

        return _fallback_plan(
            task,
            "No tools are available.",
        )

    prompt = _build_prompt(
        task,
        tools,
    )

    response = _call_ollama(
        prompt
    )

    if response is None:
        return _fallback_plan(
            task,
            "Qwen3 planner unavailable.",
        )

    parsed = _extract_json(
        response
    )

    if parsed is None:
        return _fallback_plan(
            task,
            "Qwen3 returned invalid JSON.",
        )

    action = _normalize_action(
        parsed.get("action")
    )

    arguments = _normalize_arguments(
        parsed.get("arguments")
    )

    reason = parsed.get(
        "reason",
        "",
    )

    if not isinstance(
        reason,
        str,
    ):
        reason = ""

    reason = reason.strip()

    confidence = parsed.get(
        "confidence",
        0,
    )

    try:
        confidence = int(
            confidence
        )
    except (
        TypeError,
        ValueError,
    ):
        confidence = 0

    confidence = max(
        0,
        min(
            confidence,
            95,
        ),
    )

    # -----------------------------------------------------
    # Verify the action actually exists in the supplied
    # tool registry.
    # -----------------------------------------------------

    available_names = {
        str(tool.get("name", ""))
        for tool in tools
        if isinstance(tool, dict)
    }

    if (
        action != "none"
        and action not in available_names
    ):
        return _fallback_plan(
            task,
            "Qwen3 selected an unavailable tool.",
        )

    # -----------------------------------------------------
    # Return plan only.
    # -----------------------------------------------------

    return {
        "success": action != "none",
        "action": action,
        "arguments": arguments,
        "reason": reason,
        "confidence": confidence,
        "source": "ollama_qwen3",
        "task": task,
    }