from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db

from auth.oauth2 import get_current_user

from models.models import User
from models.vehicle import Vehicle
from models.emergency import Emergency
from models.service_request import ServiceRequest
from models.notification import Notification

from schemas.dashboard import DashboardResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/user",
    response_model=DashboardResponse
)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    total_vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == current_user.user_id
    ).count()

    active_emergencies = db.query(Emergency).filter(
        Emergency.user_id == current_user.user_id,
        Emergency.status != "resolved"
    ).count()

    total_requests = db.query(ServiceRequest).filter(
        ServiceRequest.user_id == current_user.user_id
    ).count()

    unread_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.status == "unread"
    ).count()

    return DashboardResponse(
        name=current_user.full_name,
        email=current_user.email,
        total_vehicles=total_vehicles,
        active_emergencies=active_emergencies,
        total_requests=total_requests,
        unread_notifications=unread_notifications
    )