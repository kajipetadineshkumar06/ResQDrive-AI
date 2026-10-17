# ==========================================
# schemas/auth.py
# ==========================================

from pydantic import BaseModel


# ==========================================
# REGISTER REQUEST
# ==========================================

class RegisterRequest(BaseModel):

    full_name: str
    email: str
    password: str
    phone: str | None = None


# ==========================================
# LOGIN TOKEN RESPONSE
# ==========================================

class TokenResponse(BaseModel):

    access_token: str
    token_type: str


# ==========================================
# USER PROFILE
# ==========================================

class UserProfile(BaseModel):

    user_id: int
    full_name: str
    email: str
    phone: str | None = None

    class Config:
        from_attributes = True