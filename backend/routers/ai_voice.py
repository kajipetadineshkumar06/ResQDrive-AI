from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas.ai_voice import VoiceCommand
from ai.voice_ai import analyze_voice

from models.emergency import Emergency
from models.service_provider import ServiceProvider
from models.service_request import ServiceRequest
from models.notification import Notification


router = APIRouter(
    prefix="/ai",
    tags=["AI Voice Assistant"]
)


@router.post("/voice-command")
def voice_command(
    data: VoiceCommand,
    db: Session = Depends(get_db)
):

    # AI analysis
    result = analyze_voice(data.voice_text)

    # Create emergency
    emergency = Emergency(
        user_id=data.user_id,
        emergency_type=result["issue"],
        description=data.voice_text,
        location_lat=17.3850000,
        location_lng=78.4867000,
        priority=result["priority"],
        recommended_service=result["service"]
    )

    db.add(emergency)
    db.commit()
    db.refresh(emergency)

    # Map AI service to database service type
    service_map = {
        "Battery": "battery",
        "Fuel Delivery": "fuel_delivery",
        "Tyre Repair": "tyre_repair",
        "Tow Truck": "towing",
        "Mechanic": "mechanic"
    }

    service_type = service_map.get(result["service"])

    # Find available provider
    provider = db.query(ServiceProvider).filter(
        ServiceProvider.service_type == service_type,
        ServiceProvider.is_available.is_(True),
        ServiceProvider.verified.is_(True),
    ).with_for_update().first()

    if provider is not None:
        active_request = db.query(ServiceRequest.request_id).filter(
            ServiceRequest.provider_id == provider.provider_id,
            ServiceRequest.request_status.notin_(
                (
                    "completed",
                    "cancelled",
                    "canceled",
                    "rejected",
                    "timeout",
                    "timed_out",
                )
            ),
        ).with_for_update().first()
        if active_request is not None:
            provider = None

    request = None

    if provider:

        # Create service request
        request = ServiceRequest(
            emergency_id=emergency.emergency_id,
            provider_id=provider.provider_id,
            user_id=data.user_id,
            request_status="pending",
        )

        db.add(request)
        provider.is_available = False

        # Create notification
        if provider.user_id is not None:
            notification = Notification(
                user_id=provider.user_id,
                emergency_id=emergency.emergency_id,
                provider_id=provider.provider_id,
                title="New Emergency Assigned",
                message=f"You have a new {result['issue']} emergency.",
                status="unread",
            )
            db.add(notification)

        db.commit()
        db.refresh(request)

    return {
        "message": "Emergency created from AI voice",
        "emergency_id": emergency.emergency_id,
        "issue": result["issue"],
        "service": result["service"],
        "priority": result["priority"],
        "provider_assigned": provider.name if provider else None
    }
