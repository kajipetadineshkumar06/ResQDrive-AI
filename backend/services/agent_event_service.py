from typing import Any

from sqlalchemy.orm import Session

from models.agent_event import AgentEvent


def record_agent_event(
    db: Session,
    event_type: str,
    *,
    emergency_id: int | None = None,
    request_id: int | None = None,
    actor_user_id: int | None = None,
    provider_id: int | None = None,
    event_status: str = "recorded",
    details: dict[str, Any] | None = None,
) -> AgentEvent:
    """Add an audit event to the caller's transaction."""
    event = AgentEvent(
        emergency_id=emergency_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        provider_id=provider_id,
        event_type=event_type,
        event_status=event_status,
        details=details,
    )
    db.add(event)
    return event
