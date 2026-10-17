from pydantic import BaseModel


class VoiceCommand(BaseModel):
    user_id: int
    voice_text: str