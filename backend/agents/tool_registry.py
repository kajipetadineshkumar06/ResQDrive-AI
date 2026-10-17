# ==========================================
# ResQDrive AI
# Agent Tool Registry
# Phase 3.1 - Agent Foundation
# ==========================================

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from models.emergency import Emergency
from models.service_provider import ServiceProvider
from models.service_request import ServiceRequest

from services.maps._service import get_route
from services.ai_eta_prediction_service import predict_eta


# =========================================================
# TOOL DEFINITION
# =========================================================

@dataclass
class AgentTool:
    """
    Definition of one controlled tool available to an agent.
    """

    name: str
    description: str
    handler: Callable[..., Any]


# =========================================================
# SERIALIZATION HELPER
# =========================================================

def _serialize_value(value: Any) -> Any:
    """
    Convert common database/Python values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, list):
        return [
            _serialize_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item)
            for key, item in value.items()
        }

    return str(value)


def _serialize_model(instance: Any) -> Dict[str, Any]:
    """
    Serialize SQLAlchemy model columns without exposing
    private SQLAlchemy state.
    """

    if instance is None:
        return {}

    result: Dict[str, Any] = {}

    mapper = instance.__mapper__

    for column in mapper.column_attrs:
        key = column.key

        try:
            value = getattr(instance, key)
        except Exception:
            continue

        result[key] = _serialize_value(value)

    return result


# =========================================================
# DATABASE TOOLS
# =========================================================

def _get_emergency(
    db: Session,
    emergency_id: int,
) -> Dict[str, Any]:
    """
    Get one emergency by ID.
    """

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id == emergency_id
        )
        .first()
    )

    if emergency is None:
        return {
            "found": False,
            "emergency_id": emergency_id,
            "message": "Emergency not found",
        }

    return {
        "found": True,
        "emergency": _serialize_model(emergency),
    }


def _get_service_request(
    db: Session,
    request_id: int,
) -> Dict[str, Any]:
    """
    Get one service request by ID.
    """

    request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.request_id == request_id
        )
        .first()
    )

    if request is None:
        return {
            "found": False,
            "request_id": request_id,
            "message": "Service request not found",
        }

    return {
        "found": True,
        "service_request": _serialize_model(request),
    }


def _get_provider(
    db: Session,
    provider_id: int,
) -> Dict[str, Any]:
    """
    Get one provider by ID.
    """

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id == provider_id
        )
        .first()
    )

    if provider is None:
        return {
            "found": False,
            "provider_id": provider_id,
            "message": "Provider not found",
        }

    return {
        "found": True,
        "provider": _serialize_model(provider),
    }


def _find_available_providers(
    db: Session,
    service_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find currently available providers.

    This is a READ-ONLY tool.

    Provider assignment/ranking will be handled by the
    Dispatch Agent in a later phase.
    """

    query = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.is_available.is_(True),
            ServiceProvider.verified.is_(True),
        )
    )

    if service_type:
        query = query.filter(
            ServiceProvider.service_type == service_type
        )

    providers = query.all()

    return {
        "count": len(providers),
        "service_type": service_type,
        "providers": [
            _serialize_model(provider)
            for provider in providers
        ],
    }


# =========================================================
# ROUTE / ETA TOOLS
# =========================================================

def _calculate_route(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> Dict[str, Any]:
    """
    Calculate a real route using the existing Google Routes
    service.
    """

    result = get_route(
        origin_latitude,
        origin_longitude,
        destination_latitude,
        destination_longitude,
    )

    if result is None:
        return {
            "success": False,
            "message": "Route could not be calculated",
        }

    return {
        "success": True,
        "route": _serialize_value(result),
    }


def _predict_eta(
    provider_id: int,
    latitude: float,
    longitude: float,
    distance_meters: float,
    duration: str,
) -> Dict[str, Any]:
    """
    Predict ETA using the existing ResQDrive adaptive
    ETA service.
    """

    result = predict_eta(
        provider_id=provider_id,
        latitude=latitude,
        longitude=longitude,
        distance_meters=distance_meters,
        duration=duration,
    )

    return {
        "success": True,
        "eta_prediction": _serialize_value(result),
    }


# =========================================================
# TOOL REGISTRY
# =========================================================

class AgentToolRegistry:
    """
    Central registry for controlled ResQDrive AI tools.
    """

    def __init__(self, db: Session):
        self.db = db
        self._tools: Dict[str, AgentTool] = {}

        self._register_default_tools()

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
    ) -> None:
        """
        Register one tool.
        """

        if not name:
            raise ValueError(
                "Tool name cannot be empty"
            )

        if name in self._tools:
            raise ValueError(
                f"Tool already registered: {name}"
            )

        self._tools[name] = AgentTool(
            name=name,
            description=description,
            handler=handler,
        )

    # -----------------------------------------------------
    # DEFAULT TOOLS
    # -----------------------------------------------------

    def _register_default_tools(self) -> None:
        """
        Register the first ResQDrive agent tools.
        """

        self.register(
            name="get_emergency",
            description=(
                "Get emergency details by emergency ID. "
                "Read-only operation."
            ),
            handler=self._get_emergency_tool,
        )

        self.register(
            name="get_service_request",
            description=(
                "Get service request details by request ID. "
                "Read-only operation."
            ),
            handler=self._get_service_request_tool,
        )

        self.register(
            name="get_provider",
            description=(
                "Get provider details by provider ID. "
                "Read-only operation."
            ),
            handler=self._get_provider_tool,
        )

        self.register(
            name="find_available_providers",
            description=(
                "Find currently available roadside assistance "
                "providers, optionally filtered by service type."
            ),
            handler=self._find_available_providers_tool,
        )

        self.register(
            name="calculate_route",
            description=(
                "Calculate a real road route between two "
                "latitude/longitude coordinates using the "
                "existing Google Routes integration."
            ),
            handler=self._calculate_route_tool,
        )

        self.register(
            name="predict_eta",
            description=(
                "Predict provider ETA using the existing "
                "ResQDrive adaptive ETA service."
            ),
            handler=self._predict_eta_tool,
        )

    # -----------------------------------------------------
    # TOOL HANDLERS
    # -----------------------------------------------------

    def _get_emergency_tool(
        self,
        emergency_id: int,
    ) -> Dict[str, Any]:
        return _get_emergency(
            self.db,
            emergency_id,
        )

    def _get_service_request_tool(
        self,
        request_id: int,
    ) -> Dict[str, Any]:
        return _get_service_request(
            self.db,
            request_id,
        )

    def _get_provider_tool(
        self,
        provider_id: int,
    ) -> Dict[str, Any]:
        return _get_provider(
            self.db,
            provider_id,
        )

    def _find_available_providers_tool(
        self,
        service_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _find_available_providers(
            self.db,
            service_type,
        )

    def _calculate_route_tool(
        self,
        origin_latitude: float,
        origin_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> Dict[str, Any]:
        return _calculate_route(
            origin_latitude,
            origin_longitude,
            destination_latitude,
            destination_longitude,
        )

    def _predict_eta_tool(
        self,
        provider_id: int,
        latitude: float,
        longitude: float,
        distance_meters: float,
        duration: str,
    ) -> Dict[str, Any]:
        return _predict_eta(
            provider_id,
            latitude,
            longitude,
            distance_meters,
            duration,
        )

    # =====================================================
    # DISCOVERY
    # =====================================================

    def get(
        self,
        name: str,
    ) -> Optional[AgentTool]:
        """
        Get a registered tool.
        """

        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """
        Return tool names and descriptions.

        This is what the future orchestrator can expose
        to the LLM.
        """

        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]

    # =====================================================
    # SAFE INVOCATION
    # =====================================================

    def invoke(
        self,
        name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Safely execute one registered tool.

        Agents must use this method rather than calling
        database/service functions directly.
        """

        tool = self.get(name)

        if tool is None:
            return {
                "success": False,
                "tool": name,
                "error": (
                    f"Unknown agent tool: {name}"
                ),
            }

        try:
            result = tool.handler(**kwargs)

            return {
                "success": True,
                "tool": name,
                "result": _serialize_value(result),
            }

        except Exception as error:
            return {
                "success": False,
                "tool": name,
                "error": str(error),
            }


# =========================================================
# FACTORY
# =========================================================

def create_agent_tool_registry(
    db: Session,
) -> AgentToolRegistry:
    """
    Create a ResQDrive agent tool registry for one
    database session.
    """

    return AgentToolRegistry(db)
