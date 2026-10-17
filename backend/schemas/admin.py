from pydantic import BaseModel, EmailStr
from datetime import datetime



# ==========================================
# ADMIN CREATE
# ==========================================

class AdminCreate(BaseModel):

    name: str

    email: EmailStr

    password: str



# ==========================================
# ADMIN LOGIN
# ==========================================

class AdminLogin(BaseModel):

    email: EmailStr

    password: str



# ==========================================
# ADMIN RESPONSE
# ==========================================

class AdminResponse(BaseModel):

    admin_id: int

    name: str

    email: EmailStr

    is_active: bool

    created_at: datetime


    class Config:

        from_attributes = True



# ==========================================
# USER STATUS UPDATE
# ==========================================

class UserStatusUpdate(BaseModel):

    is_active: bool



# ==========================================
# PROVIDER VERIFY
# ==========================================

class ProviderVerify(BaseModel):

    is_verified: bool



# ==========================================
# ADMIN STATISTICS
# ==========================================

class AdminStatistics(BaseModel):

    total_users: int

    total_providers: int

    total_emergencies: int

    total_requests: int

    total_revenue: float



# ==========================================
# ADMIN DASHBOARD RESPONSE
# ==========================================

class AdminDashboardResponse(BaseModel):

    total_users: int

    total_providers: int

    total_emergencies: int

    total_requests: int

    pending_requests: int

    completed_requests: int

    total_revenue: float