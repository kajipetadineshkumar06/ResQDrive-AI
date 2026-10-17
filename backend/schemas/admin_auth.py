from pydantic import BaseModel, EmailStr
from datetime import datetime


# ==========================================
# ADMIN LOGIN REQUEST
# ==========================================

class AdminLogin(BaseModel):

    email: EmailStr

    password: str



# ==========================================
# ADMIN TOKEN RESPONSE
# ==========================================

class AdminTokenResponse(BaseModel):

    access_token: str

    token_type: str



# ==========================================
# ADMIN PROFILE RESPONSE
# ==========================================

class AdminProfileResponse(BaseModel):

    admin_id: int

    name: str

    email: EmailStr

    is_active: bool

    created_at: datetime


    class Config:

        from_attributes = True