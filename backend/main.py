# ==========================
# MODELS
# ==========================

import models.user
import models.vehicle
import models.service_request
import models.emergency
import models.service_provider
import models.rating
import models.payment
import models.coupon
import models.invoice
import models.provider_location
import models.notification
import models.admin
import models.fcm_token
import models.agent_event

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from deployment_config import (
    auto_create_tables_enabled,
    get_cors_origins,
    scheduler_enabled,
)
from tasks.scheduler import start_scheduler, stop_scheduler
from websocket.tracking import manager


# ==========================
# ROUTERS
# ==========================

from routers import admin
from routers import admin_auth
from routers import ai
from routers import ai_voice
from routers import auth
from routers import background_jobs
from routers import coupon
from routers import dashboard
from routers import emergencies
from routers import eta
from routers import fcm
from routers import history
from routers import invoice
from routers import jobs
from routers import location
from routers import nearby
from routers import notification
from routers import payment
from routers import provider_actions
from routers import provider_dashboard
from routers import provider_location
from routers import provider_tracking
from routers import providers
from routers import ratings
from routers import routes
from routers import service_requests
from routers import sos
from routers import tracking
from routers import user_dashboard
from routers import users
from routers import vehicles
from routers import websocket
from routers import diagnosis
from routers import agent_assistance

# ==========================
# DATABASE TABLE CREATION
# ==========================

if auto_create_tables_enabled():
    Base.metadata.create_all(bind=engine)

# ==========================
# FASTAPI APP
# ==========================

app = FastAPI(
    title="ResQDrive AI",
    version="1.0"
)




# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Requested-With"],
)


@app.get("/health", include_in_schema=False)
def health_check():
    """Non-sensitive liveness endpoint; it does not expose database state."""
    return {"status": "ok"}


# ==========================
# STARTUP / SHUTDOWN EVENTS
# ==========================

@app.on_event("startup")
def startup_event():
    if scheduler_enabled():
        start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()




# ==========================
# INCLUDE ROUTERS
# ==========================

app.include_router(users.router)
app.include_router(vehicles.router)
app.include_router(emergencies.router)
app.include_router(service_requests.router)
app.include_router(sos.router)
app.include_router(providers.router)
app.include_router(location.router)
app.include_router(ai_voice.router)
app.include_router(provider_location.router)
app.include_router(nearby.router)
app.include_router(user_dashboard.router)
app.include_router(tracking.router)
app.include_router(notification.router)
app.include_router(provider_dashboard.router)
app.include_router(eta.router)
app.include_router(ratings.router)
app.include_router(history.router)
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(dashboard.router)
app.include_router(payment.router)
app.include_router(coupon.router)
app.include_router(invoice.router)
app.include_router(admin.router)
app.include_router(admin_auth.router)
app.include_router(fcm.router)
app.include_router(provider_actions.router)
app.include_router(routes.router)
app.include_router(websocket.router)
app.include_router(provider_tracking.router)
app.include_router(jobs.router)
app.include_router(background_jobs.router)
app.include_router(diagnosis.router)
app.include_router(agent_assistance.router)

# =====================================
# REAL-TIME USER WEBSOCKET
# =====================================

@app.websocket("/ws/tracking/{user_id}")
async def websocket_tracking(
    websocket: WebSocket,
    user_id: int
):

    await manager.connect(
        user_id,
        websocket
    )

    try:

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect(user_id)

        print(
            f"User {user_id} disconnected"
        )


# ==========================
# HOME
# ==========================

@app.get("/")
def home():

    return {
        "message": "Welcome to ResQDrive AI"
    }
