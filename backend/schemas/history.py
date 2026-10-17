from pydantic import BaseModel


class HistoryResponse(BaseModel):
    emergency_id: int
    emergency_type: str
    description: str
    priority: str
    status: str

    class Config:
        from_attributes = True