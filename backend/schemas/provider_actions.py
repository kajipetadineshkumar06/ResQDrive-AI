from pydantic import BaseModel


class ProviderActionResponse(BaseModel):

    message: str

    request_id: int

    status: str