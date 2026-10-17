from pydantic import BaseModel


class DashboardResponse(BaseModel):
    name: str
    email: str
    total_vehicles: int
    active_emergencies: int
    total_requests: int
    unread_notifications: int