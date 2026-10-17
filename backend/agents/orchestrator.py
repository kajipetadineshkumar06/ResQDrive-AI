# ==========================================
# ResQDrive AI
# Emergency Assistance Orchestrator
# ==========================================

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from agents.tool_registry import create_agent_tool_registry


# =========================================================
# ORCHESTRATOR
# =========================================================

class ResQDriveOrchestrator:
    """
    Central AI orchestrator for ResQDrive AI.

    Current workflow:

        User Task
            ↓
        AI Planner
            ↓
        Tool Registry
            ↓
        Emergency
            ↓
        Service Type
            ↓
        Available Providers
            ↓
        Provider Selection
            ↓
        Google Route
            ↓
        Route Normalization
            ↓
        ETA Prediction
            ↓
        Assistance Plan

    The orchestrator does not directly access database/service
    functions. All operational calls go through the AgentToolRegistry.
    """

    def __init__(self, db: Session):
        self.db = db

        self.tool_registry = create_agent_tool_registry(
            db
        )

    # =====================================================
    # TOOL DISCOVERY
    # =====================================================

    def available_tools(self) -> List[Dict[str, str]]:
        """
        Return all tools available to the orchestrator.
        """

        return self.tool_registry.list_tools()

    # =====================================================
    # TOOL EXECUTION
    # =====================================================

    def execute_tool(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Safely execute a registered agent tool.

        This is the single entry point used by the
        orchestrator for backend tools.
        """

        print(
            f"🔧 Executing tool: {tool_name}"
        )

        print(
            f"📦 Arguments: {kwargs}"
        )

        result = self.tool_registry.invoke(
            tool_name,
            **kwargs,
        )

        if not result.get("success"):
            print(
                f"❌ Tool failed: {tool_name}"
            )

            print(
                f"   Error: {result.get('error')}"
            )

        return result

    # =====================================================
    # INTEGER CONVERSION
    # =====================================================

    @staticmethod
    def _to_int(
        value: Any,
    ) -> Optional[int]:
        """
        Convert a value to integer safely.
        """

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # =====================================================
    # FLOAT CONVERSION
    # =====================================================

    @staticmethod
    def _to_float(
        value: Any,
    ) -> Optional[float]:
        """
        Convert a value to float safely.
        """

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # =====================================================
    # DURATION NORMALIZATION
    # =====================================================

    @classmethod
    def _normalize_duration_seconds(
        cls,
        duration_value: Any,
    ) -> Optional[float]:
        """
        Normalize Google Routes duration into seconds.

        Supported examples:

            2912
            2912.0
            "2912"
            "2912s"
            "2912.0s"
        """

        if duration_value is None:
            return None

        if isinstance(
            duration_value,
            (
                int,
                float,
            ),
        ):
            return float(
                duration_value
            )

        if not isinstance(
            duration_value,
            str,
        ):
            return None

        text = duration_value.strip()

        if not text:
            return None

        # Google Routes format:
        #
        # "2912s"

        if text.endswith("s"):
            text = text[:-1].strip()

        try:
            return float(text)
        except (
            TypeError,
            ValueError,
        ):
            return None

    # =====================================================
    # ROUTE EXTRACTION
    # =====================================================

    @classmethod
    def _extract_route_data(
        cls,
        route_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract and normalize route information from
        the calculate_route tool response.
        """

        if not route_result.get(
            "success"
        ):
            return {
                "success": False,
                "distance_meters": None,
                "duration_seconds": None,
                "polyline": None,
                "error": route_result.get(
                    "error",
                    "Route calculation failed.",
                ),
            }

        result = route_result.get(
            "result",
            {},
        )

        if not isinstance(
            result,
            dict,
        ):
            return {
                "success": False,
                "distance_meters": None,
                "duration_seconds": None,
                "polyline": None,
                "error": "Invalid route result.",
            }

        route = result.get(
            "route",
            {},
        )

        if not isinstance(
            route,
            dict,
        ):
            route = {}

        distance_meters = cls._to_float(
            route.get(
                "distance_meters"
            )
        )

        duration_seconds = cls._normalize_duration_seconds(
            route.get(
                "duration_seconds"
            )
        )

        if duration_seconds is None:
            duration_seconds = cls._normalize_duration_seconds(
                route.get(
                    "duration"
                )
            )

        polyline = route.get(
            "polyline"
        )

        return {
            "success": (
                distance_meters is not None
                and duration_seconds is not None
            ),
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "polyline": polyline,
            "error": (
                None
                if (
                    distance_meters is not None
                    and duration_seconds is not None
                )
                else "Route did not return valid distance and duration."
            ),
        }

    # =====================================================
    # EMERGENCY ASSISTANCE WORKFLOW
    # =====================================================

    def run_emergency_assistance(
        self,
        emergency_id: int,
    ) -> Dict[str, Any]:
        """
        Run the complete ResQDrive AI emergency-assistance workflow.

        Flow:

            Emergency
                ↓
            Determine required service
                ↓
            Find available providers
                ↓
            Select provider
                ↓
            Calculate Google route
                ↓
            Normalize route distance/duration
                ↓
            Predict ETA
                ↓
            Return complete assistance plan
        """

        print(
            f"🚨 Starting emergency assistance: {emergency_id}"
        )

        # =================================================
        # STEP 1: GET EMERGENCY
        # =================================================

        emergency_result = self.execute_tool(
            "get_emergency",
            emergency_id=emergency_id,
        )

        if not emergency_result.get(
            "success"
        ):
            return {
                "success": False,
                "status": "emergency_lookup_failed",
                "message": "Unable to retrieve emergency.",
                "details": emergency_result,
            }

        emergency_result_data = (
            emergency_result.get(
                "result",
                {},
            )
        )

        if not isinstance(
            emergency_result_data,
            dict,
        ):
            return {
                "success": False,
                "status": "invalid_emergency_response",
                "message": "Emergency tool returned an invalid response.",
                "details": emergency_result,
            }

        emergency = emergency_result_data.get(
            "emergency"
        )

        if not emergency:
            return {
                "success": False,
                "status": "emergency_not_found",
                "message": "Emergency not found.",
            }

        # =================================================
        # STEP 2: DETERMINE SERVICE TYPE
        # =================================================

        service_type = emergency.get(
            "recommended_service"
        )

        if not service_type:
            return {
                "success": False,
                "status": "service_type_missing",
                "emergency": emergency,
                "message": (
                    "No recommended service was found "
                    "for this emergency."
                ),
            }

        print(
            f"🔎 Finding providers for: {service_type}"
        )

        # =================================================
        # STEP 3: FIND AVAILABLE PROVIDERS
        # =================================================

        providers_result = self.execute_tool(
            "find_available_providers",
            service_type=service_type,
        )

        if not providers_result.get(
            "success"
        ):
            return {
                "success": False,
                "status": "provider_search_failed",
                "emergency": emergency,
                "service_type": service_type,
                "message": (
                    "Unable to find available providers."
                ),
                "details": providers_result,
            }

        provider_data = (
            providers_result.get(
                "result",
                {},
            )
        )

        if not isinstance(
            provider_data,
            dict,
        ):
            provider_data = {}

        providers = provider_data.get(
            "providers",
            [],
        )

        if not isinstance(
            providers,
            list,
        ):
            providers = []

        # =================================================
        # NO PROVIDER
        # =================================================

        if not providers:
            return {
                "success": True,
                "status": "no_provider_found",
                "emergency": emergency,
                "service_type": service_type,
                "provider_count": 0,
                "providers": [],
                "selected_provider": None,
                "route": None,
                "route_summary": None,
                "eta": None,
                "message": (
                    "Emergency analyzed, but no "
                    "available provider was found."
                ),
            }

        # =================================================
        # STEP 4: SELECT PROVIDER
        # =================================================

        selected_provider = providers[0]

        provider_id = selected_provider.get(
            "provider_id"
        )

        print(
            f"👤 Selected provider: {provider_id}"
        )

        provider_lat = self._to_float(
            selected_provider.get(
                "location_lat"
            )
        )

        provider_lng = self._to_float(
            selected_provider.get(
                "location_lng"
            )
        )

        emergency_lat = self._to_float(
            emergency.get(
                "location_lat"
            )
        )

        emergency_lng = self._to_float(
            emergency.get(
                "location_lng"
            )
        )

        # =================================================
        # LOCATION VALIDATION
        # =================================================

        if (
            provider_lat is None
            or provider_lng is None
            or emergency_lat is None
            or emergency_lng is None
        ):
            return {
                "success": True,
                "status": "provider_found",
                "emergency": emergency,
                "service_type": service_type,
                "provider_count": len(
                    providers
                ),
                "selected_provider": selected_provider,
                "providers": providers,
                "route": None,
                "route_summary": None,
                "eta": None,
                "message": (
                    "Provider found, but valid locations "
                    "are required for route calculation."
                ),
            }

        # =================================================
        # STEP 5: CALCULATE ROUTE
        # =================================================

        print(
            f"🗺️ Calculating route to provider {provider_id}"
        )

        route_result = self.execute_tool(
            "calculate_route",
            origin_latitude=provider_lat,
            origin_longitude=provider_lng,
            destination_latitude=emergency_lat,
            destination_longitude=emergency_lng,
        )

        if not route_result.get(
            "success"
        ):
            return {
                "success": True,
                "status": "route_calculation_failed",
                "emergency": emergency,
                "service_type": service_type,
                "provider_count": len(
                    providers
                ),
                "selected_provider": selected_provider,
                "providers": providers,
                "route": route_result,
                "route_summary": None,
                "eta": None,
                "message": (
                    "Provider found, but route calculation failed."
                ),
            }

        # =================================================
        # STEP 6: NORMALIZE ROUTE
        # =================================================

        normalized_route = (
            self._extract_route_data(
                route_result
            )
        )

        distance_meters = (
            normalized_route.get(
                "distance_meters"
            )
        )

        duration_seconds = (
            normalized_route.get(
                "duration_seconds"
            )
        )

        polyline = (
            normalized_route.get(
                "polyline"
            )
        )

        print(
            f"📏 Normalized distance: "
            f"{distance_meters} meters"
        )

        print(
            f"⏱️ Normalized duration: "
            f"{duration_seconds} seconds"
        )

        route_summary = {
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "polyline": polyline,
        }

        # =================================================
        # STEP 7: PREDICT ETA
        # =================================================

        eta_result = None

        if (
            distance_meters is not None
            and duration_seconds is not None
        ):
            print(
                "🤖 Predicting emergency ETA"
            )

            duration_for_eta = (
                f"{duration_seconds:g}s"
            )

            eta_result = self.execute_tool(
                "predict_eta",
                provider_id=provider_id,
                latitude=provider_lat,
                longitude=provider_lng,
                distance_meters=distance_meters,
                duration=duration_for_eta,
            )

        else:
            eta_result = {
                "success": False,
                "error": "route_data_missing",
                "message": (
                    "Route did not return valid "
                    "distance and duration."
                ),
            }

        # =================================================
        # STEP 8: ETA EXTRACTION
        # =================================================

        eta_prediction = None

        if eta_result.get(
            "success"
        ):
            eta_result_data = (
                eta_result.get(
                    "result",
                    {},
                )
            )

            if isinstance(
                eta_result_data,
                dict,
            ):
                eta_prediction = (
                    eta_result_data.get(
                        "eta_prediction"
                    )
                )

        # =================================================
        # STEP 9: FINAL ASSISTANCE PLAN
        # =================================================

        return {
            "success": True,
            "status": "assistance_plan_ready",

            "emergency": emergency,

            "service_type": service_type,

            "provider_count": len(
                providers
            ),

            "selected_provider": selected_provider,

            "providers": providers,

            "route": route_result,

            "route_summary": route_summary,

            "eta": eta_result,

            "eta_prediction": eta_prediction,

            "message": (
                "Emergency analyzed, provider selected, "
                "route calculated and ETA prepared."
            ),
        }

    # =====================================================
    # SIMPLE TASK RUNNER
    # =====================================================

    def run_task(
        self,
        task: str,
    ) -> Dict[str, Any]:
        """
        Execute a simple natural-language task.

        This method currently supports direct lookup of:

            Check emergency 91
            Get emergency 91
            Emergency 91

        More advanced AI planning can be added without
        changing the emergency-assistance workflow.
        """

        if not task:
            return {
                "success": False,
                "message": "Task cannot be empty.",
            }

        task_text = str(
            task
        ).strip()

        # =================================================
        # EXTRACT EMERGENCY ID
        # =================================================

        emergency_match = re.search(
            r"(?:emergency|incident)\s*#?\s*(\d+)",
            task_text,
            re.IGNORECASE,
        )

        if emergency_match:
            emergency_id = self._to_int(
                emergency_match.group(
                    1
                )
            )

            if emergency_id is not None:
                tool_result = self.execute_tool(
                    "get_emergency",
                    emergency_id=emergency_id,
                )

                return {
                    "success": tool_result.get(
                        "success",
                        False,
                    ),
                    "task": task_text,
                    "source": "resqdrive_orchestrator",
                    "action": "get_emergency",
                    "arguments": {
                        "emergency_id": emergency_id,
                    },
                    "tool_result": tool_result,
                }

        return {
            "success": False,
            "task": task_text,
            "message": (
                "I could not determine a supported "
                "ResQDrive action from the task."
            ),
            "available_actions": [
                "Check emergency <id>",
                "Get emergency <id>",
                "Emergency <id>",
            ],
        }


# =========================================================
# FACTORY
# =========================================================

def create_orchestrator(
    db: Session,
) -> ResQDriveOrchestrator:
    """
    Create a ResQDrive AI orchestrator.
    """

    return ResQDriveOrchestrator(
        db
    )


# =========================================================
# DIRECT TEST
# =========================================================

if __name__ == "__main__":

    print(
        "ResQDrive AI Orchestrator module"
    )

    print(
        "Use create_orchestrator(db) "
        "from the application."
    )