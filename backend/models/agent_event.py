from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    text,
)

from database import Base


class AgentEvent(Base):
    """Durable, structured audit event for agent-assisted requests."""

    __tablename__ = "agent_events"
    __table_args__ = (
        Index("ix_agent_events_emergency_created", "emergency_id", "created_at"),
        Index("ix_agent_events_request_created", "request_id", "created_at"),
    )

    event_id = Column(Integer, primary_key=True)
    emergency_id = Column(
        Integer,
        ForeignKey("emergencies.emergency_id", ondelete="SET NULL"),
        nullable=True,
    )
    request_id = Column(
        Integer,
        ForeignKey("service_requests.request_id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_id = Column(
        Integer,
        ForeignKey("service_providers.provider_id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type = Column(String(80), nullable=False)
    event_status = Column(
        String(30),
        nullable=False,
        default="recorded",
        server_default=text("'recorded'"),
    )
    details = Column(JSON, nullable=True)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
