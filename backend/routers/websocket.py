from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect
)

from sqlalchemy.orm import Session

from database import SessionLocal

from auth.jwt_handler import decode_access_token

from models.user import User
from models.emergency import Emergency
from models.service_request import ServiceRequest

from websocket.tracking import manager


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    tags=["WebSocket"]
)


# =========================================================
# SECURE LIVE TRACKING WEBSOCKET
#
# Customer connects using:
#
# ws://127.0.0.1:8000/ws/live-tracking/{emergency_id}?token=JWT
#
# =========================================================

@router.websocket(
    "/ws/live-tracking/{emergency_id}"
)
async def live_tracking_websocket(
    websocket: WebSocket,
    emergency_id: int
):

    db: Session = SessionLocal()

    user_id = None

    try:

        # -------------------------------------------------
        # Read JWT token from query string
        # -------------------------------------------------

        token = websocket.query_params.get(
            "token"
        )

        if not token:

            await websocket.close(
                code=1008,
                reason="Authentication token required"
            )

            return

        # -------------------------------------------------
        # Decode JWT
        # -------------------------------------------------

        payload = decode_access_token(
            token
        )

        if payload is None:

            await websocket.close(
                code=1008,
                reason="Invalid or expired token"
            )

            return

        # -------------------------------------------------
        # Get user ID
        # -------------------------------------------------

        token_user_id = payload.get(
            "sub"
        )

        if token_user_id is None:

            await websocket.close(
                code=1008,
                reason="Invalid token"
            )

            return

        try:

            user_id = int(
                token_user_id
            )

        except (
            TypeError,
            ValueError
        ):

            await websocket.close(
                code=1008,
                reason="Invalid user ID"
            )

            return

        # -------------------------------------------------
        # Verify user exists
        # -------------------------------------------------

        user = db.query(
            User
        ).filter(
            User.user_id == user_id
        ).first()

        if not user:

            await websocket.close(
                code=1008,
                reason="User not found"
            )

            return

        # -------------------------------------------------
        # Verify emergency belongs to user
        # -------------------------------------------------

        emergency = db.query(
            Emergency
        ).filter(
            Emergency.emergency_id == emergency_id,
            Emergency.user_id == user_id
        ).first()

        if not emergency:

            await websocket.close(
                code=1008,
                reason="Emergency access denied"
            )

            return

        # -------------------------------------------------
        # Find service request
        # -------------------------------------------------

        request = db.query(
            ServiceRequest
        ).filter(
            ServiceRequest.emergency_id == emergency_id,
            ServiceRequest.user_id == user_id
        ).order_by(
            ServiceRequest.request_id.desc()
        ).first()

        if not request:

            await websocket.close(
                code=1008,
                reason="Service request not found"
            )

            return

        # -------------------------------------------------
        # Require an active service
        # -------------------------------------------------

        if request.request_status not in [
            "accepted",
            "on_the_way",
            "arrived",
            "in_progress"
        ]:

            await websocket.close(
                code=1008,
                reason="Live tracking is not active"
            )

            return

        # -------------------------------------------------
        # Connect customer
        # -------------------------------------------------

        await manager.connect(
            user_id,
            websocket
        )

        # -------------------------------------------------
        # Send connection confirmation
        # -------------------------------------------------

        await websocket.send_json({

            "event": "tracking_connected",

            "emergency_id": emergency_id,

            "request_id": request.request_id,

            "provider_id": request.provider_id,

            "status": request.request_status,

            "message": "Live tracking connected"
        })

        print(
            f"📍 Live tracking connected: "
            f"User {user_id}, "
            f"Emergency {emergency_id}"
        )

        # -------------------------------------------------
        # Keep connection alive
        # -------------------------------------------------

        while True:

            await websocket.receive_text()

    except WebSocketDisconnect:

        if user_id is not None:

            manager.disconnect(
                user_id,
                websocket
            )

        print(
            f"📍 Live tracking disconnected: "
            f"User {user_id}"
        )

    except Exception as error:

        print(
            f"❌ Live tracking WebSocket error: {error}"
        )

        if user_id is not None:

            manager.disconnect(
                user_id,
                websocket
            )

    finally:

        db.close()
