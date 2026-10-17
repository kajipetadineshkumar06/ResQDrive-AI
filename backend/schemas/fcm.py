from pydantic import BaseModel


class TokenCreate(BaseModel):
    token: str