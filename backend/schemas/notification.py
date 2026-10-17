from pydantic import BaseModel
from datetime import datetime


class NotificationCreate(BaseModel):
    emergency_id: int
    provider_id: int
    title: str
    message: str


class NotificationResponse(BaseModel):
    notification_id: int
    emergency_id: int
    provider_id: int
    title: str
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True