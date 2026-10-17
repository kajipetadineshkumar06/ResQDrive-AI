from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.user import User
from models.provider_location import ProviderLocation
from models.agent_event import AgentEvent
from services.agent_event_service import record_agent_event
from models.service_provider import ServiceProvider
from models.service_request import ServiceRequest
from models.emergency import Emergency

from schemas.provider_location import ProviderLocationCreate

from services.gps_validator import is_valid_location
from services.live_eta_service import calculate_live_eta
from services.ai_eta_prediction_service import predict_eta

from websocket.tracking import manager


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/provider-location",
    tags=["Provider Location"],
)


# =========================================================
# GET LOGGED-IN PROVIDER
# =========================================================

def get_logged_in_provider(
    current_user: User,
    db: Session,
):

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.user_id
            == current_user.user_id
        )
        .first()
    )

    if not provider:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not registered "
                "as a service provider"
            ),
        )

    return provider


# =========================================================
# UPDATE PROVIDER GPS LOCATION
# =========================================================

@router.post("/update")
async def update_location(

    data: ProviderLocationCreate,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):

    # -----------------------------------------------------
    # FIND PROVIDER
    # -----------------------------------------------------

    provider = get_logged_in_provider(
        current_user,
        db,
    )

    provider_id = provider.provider_id

    # -----------------------------------------------------
    # VALIDATE GPS
    # -----------------------------------------------------

    if not is_valid_location(
        data.latitude,
        data.longitude,
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GPS coordinates",
        )

    latitude = float(
        data.latitude
    )

    longitude = float(
        data.longitude
    )

    # -----------------------------------------------------
    # CHECK TRACKING
    # -----------------------------------------------------

    if not provider.is_tracking:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPS tracking is not active",
        )

    # -----------------------------------------------------
    # FIND ACTIVE REQUEST
    # -----------------------------------------------------

    active_request = (
        db.query(ServiceRequest)
        .filter(
            ServiceRequest.provider_id
            == provider_id,

            ServiceRequest.request_status.in_(
                [
                    "on_the_way",
                    "started",
                ]
            ),
        )
        .order_by(
            ServiceRequest.request_id.desc()
        )
        .first()
    )

    if not active_request:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active trip found for this provider",
        )

    # -----------------------------------------------------
    # FIND EMERGENCY
    # -----------------------------------------------------

    emergency = (
        db.query(Emergency)
        .filter(
            Emergency.emergency_id
            == active_request.emergency_id
        )
        .first()
    )

    if not emergency:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency not found",
        )

    # -----------------------------------------------------
    # ETA DATA
    # -----------------------------------------------------

    eta = {
        "distance_meters": None,
        "eta": None,
        "duration": None,
        "polyline": None,

        "ai_eta": None,
        "ai_predicted_duration": None,
        "ai_eta_confidence": None,
        "ai_eta_source": None,
    }

    # -----------------------------------------------------
    # CHECK DESTINATION COORDINATES
    # -----------------------------------------------------

    if (
        emergency.location_lat is None
        or emergency.location_lng is None
    ):

        print(
            "⚠️ Emergency location is not available."
        )

    else:

        # -------------------------------------------------
        # CALCULATE LIVE ETA
        # -------------------------------------------------

        try:

            live_eta = calculate_live_eta(

                provider_lat=latitude,

                provider_lng=longitude,

                emergency_lat=float(
                    emergency.location_lat
                ),

                emergency_lng=float(
                    emergency.location_lng
                ),
            )

            if live_eta:

                eta.update(
                    live_eta
                )

        except Exception as error:

            print(
                "⚠️ Live ETA calculation failed:"
            )

            print(
                repr(error)
            )

        # -------------------------------------------------
        # AI ETA PREDICTION
        # -------------------------------------------------

        try:

            ai_eta = predict_eta(

                provider_id=provider_id,

                latitude=latitude,

                longitude=longitude,

                distance_meters=eta.get(
                    "distance_meters"
                ),

                duration=eta.get(
                    "duration"
                ),
            )

            # ---------------------------------------------
            # STORE AI ETA
            # ---------------------------------------------

            eta["ai_eta"] = ai_eta.get(
                "predicted_eta"
            )

            eta["ai_predicted_duration"] = (
                ai_eta.get(
                    "predicted_duration"
                )
            )

            eta["ai_eta_confidence"] = (
                ai_eta.get(
                    "confidence"
                )
            )

            eta["ai_eta_source"] = (
                ai_eta.get(
                    "source"
                )
            )

            # ---------------------------------------------
            # LOG AI ETA
            # ---------------------------------------------

            if ai_eta.get(
                "predicted_eta"
            ) is not None:

                print("")
                print(
                    "🤖 ResQDrive AI ETA:"
                )

                print(
                    f"   Predicted ETA: "
                    f"{ai_eta.get('predicted_eta')}"
                )

                print(
                    f"   Confidence: "
                    f"{ai_eta.get('confidence')}%"
                )

                print(
                    f"   Observed speed: "
                    f"{ai_eta.get('observed_speed_kmh')} km/h"
                )

                print(
                    f"   Adjustment factor: "
                    f"{ai_eta.get('adjustment_factor')}"
                )

                print(
                    f"   GPS samples: "
                    f"{ai_eta.get('samples')}"
                )

                print(
                    f"   Source: "
                    f"{ai_eta.get('source')}"
                )

            else:

                print(
                    "⚠️ AI ETA prediction "
                    "is currently unavailable."
                )

        except Exception as error:

            print(
                "⚠️ AI ETA prediction failed:"
            )

            print(
                repr(error)
            )

    # -----------------------------------------------------
    # SAVE PROVIDER LOCATION
    # -----------------------------------------------------

    location = (
        db.query(ProviderLocation)
        .filter(
            ProviderLocation.provider_id
            == provider_id
        )
        .first()
    )

    if location:

        location.latitude = latitude

        location.longitude = longitude

    else:

        location = ProviderLocation(

            provider_id=provider_id,

            latitude=latitude,

            longitude=longitude,
        )

        db.add(location)

    first_location_event = (
        db.query(AgentEvent)
        .filter(
            AgentEvent.request_id == active_request.request_id,
            AgentEvent.event_type == "provider_location_updated",
        )
        .first()
    )
    if first_location_event is None:
        record_agent_event(
            db,
            "provider_location_updated",
            emergency_id=emergency.emergency_id,
            request_id=active_request.request_id,
            actor_user_id=current_user.user_id,
            provider_id=provider_id,
            details={"source": "provider_gps", "sample": "first_update"},
        )

    db.commit()

    db.refresh(location)

    # -----------------------------------------------------
    # BUILD WEBSOCKET MESSAGE
    # -----------------------------------------------------

    message = {

        "event":
            "provider_location",

        "request_id":
            active_request.request_id,

        "emergency_id":
            emergency.emergency_id,

        "provider_id":
            provider_id,

        "latitude":
            latitude,

        "longitude":
            longitude,

        # ---------------------------------------------
        # GOOGLE ROUTES DATA
        # ---------------------------------------------

        "distance_meters":
            eta.get(
                "distance_meters"
            ),

        "eta":
            eta.get(
                "eta"
            ),

        "duration":
            eta.get(
                "duration"
            ),

        "polyline":
            eta.get(
                "polyline"
            ),

        # ---------------------------------------------
        # AI ETA DATA
        # ---------------------------------------------

        "ai_eta":
            eta.get(
                "ai_eta"
            ),

        "ai_predicted_duration":
            eta.get(
                "ai_predicted_duration"
            ),

        "ai_eta_confidence":
            eta.get(
                "ai_eta_confidence"
            ),

        "ai_eta_source":
            eta.get(
                "ai_eta_source"
            ),

        # ---------------------------------------------
        # REQUEST STATUS
        # ---------------------------------------------

        "status":
            active_request.request_status,
    }

    # -----------------------------------------------------
    # SEND TO CUSTOMER
    # -----------------------------------------------------

    await manager.send_to_user(

        active_request.user_id,

        message,
    )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {

        "success":
            True,

        "message":
            "Live GPS location updated",

        "request_id":
            active_request.request_id,

        "emergency_id":
            emergency.emergency_id,

        "provider_id":
            provider_id,

        "latitude":
            latitude,

        "longitude":
            longitude,

        # ---------------------------------------------
        # GOOGLE ROUTES DATA
        # ---------------------------------------------

        "distance_meters":
            eta.get(
                "distance_meters"
            ),

        "eta":
            eta.get(
                "eta"
            ),

        "duration":
            eta.get(
                "duration"
            ),

        "polyline":
            eta.get(
                "polyline"
            ),

        # ---------------------------------------------
        # AI ETA DATA
        # ---------------------------------------------

        "ai_eta":
            eta.get(
                "ai_eta"
            ),

        "ai_predicted_duration":
            eta.get(
                "ai_predicted_duration"
            ),

        "ai_eta_confidence":
            eta.get(
                "ai_eta_confidence"
            ),

        "ai_eta_source":
            eta.get(
                "ai_eta_source"
            ),

        "status":
            active_request.request_status,
    }


# =========================================================
# GET PROVIDER LOCATION
# =========================================================

@router.get("/{provider_id}")
def get_provider_location(

    provider_id: int,

    current_user: User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    ),
):

    # -----------------------------------------------------
    # FIND PROVIDER
    # -----------------------------------------------------

    provider = (
        db.query(ServiceProvider)
        .filter(
            ServiceProvider.provider_id
            == provider_id
        )
        .first()
    )

    if not provider:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # -----------------------------------------------------
    # CHECK PROVIDER ACCESS
    # -----------------------------------------------------

    is_own_provider = (

        provider.user_id
        == current_user.user_id
    )

    if not is_own_provider:

        active_request = (
            db.query(ServiceRequest)
            .filter(

                ServiceRequest.provider_id
                == provider_id,

                ServiceRequest.user_id
                == current_user.user_id,

                ServiceRequest.request_status.in_(
                    [
                        "accepted",
                        "on_the_way",
                        "arrived",
                        "in_progress",
                    ]
                ),
            )
            .first()
        )

        if not active_request:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have access "
                    "to this provider location"
                ),
            )

    # Customer views receive a location only during an active trip.
    # This prevents returning a provider's last-known coordinates from an old trip.
    if not is_own_provider and not provider.is_tracking:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Live provider location is not available",
        )

    # -----------------------------------------------------
    # GET LOCATION
    # -----------------------------------------------------

    location = (
        db.query(ProviderLocation)
        .filter(
            ProviderLocation.provider_id
            == provider_id
        )
        .first()
    )

    if not location:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Provider location "
                "not available yet"
            ),
        )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {

        "success":
            True,

        "provider_id":
            provider_id,

        "latitude":
            float(
                location.latitude
            ),

        "longitude":
            float(
                location.longitude
            ),

        "updated_at":
            location.updated_at,

        "tracking":
            bool(
                provider.is_tracking
            ),
    }
