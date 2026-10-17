from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session


from database import get_db


from auth.admin_oauth2 import get_current_admin
from auth.hashing import hash_password


from models.admin import Admin
from models.user import User
from models.service_provider import ServiceProvider
from models.emergency import Emergency
from models.service_request import ServiceRequest
from models.payment import Payment



from schemas.admin import (

    AdminCreate,
    AdminResponse,

    UserStatusUpdate,

    ProviderVerify,

    AdminStatistics,

    AdminDashboardResponse

)



router = APIRouter(

    prefix="/admin",

    tags=["Admin"]

)



# ==========================================
# CREATE ADMIN
# ==========================================

@router.post(
    "/create",
    response_model=AdminResponse
)
def create_admin(

    data: AdminCreate,

    admin: Admin = Depends(get_current_admin),

    db: Session = Depends(get_db)

):


    existing = db.query(Admin).filter(

        Admin.email == data.email

    ).first()



    if existing:

        raise HTTPException(

            status_code=400,

            detail="Admin already exists"

        )



    admin = Admin(

        name=data.name,

        email=data.email,

        password=hash_password(data.password)

    )


    db.add(admin)

    db.commit()

    db.refresh(admin)



    return admin





# ==========================================
# GET USERS
# ==========================================

@router.get("/users")
def get_users(

    db: Session = Depends(get_db),

    admin: Admin = Depends(get_current_admin)

):


    users = db.query(User).all()


    return {

        "count":len(users),

        "users":users

    }




# ==========================================
# UPDATE USER STATUS
# ==========================================

@router.put("/user/status/{user_id}")
def update_user_status(

    user_id:int,

    data:UserStatusUpdate,

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    user=db.query(User).filter(

        User.user_id==user_id

    ).first()



    if not user:

        raise HTTPException(

            status_code=404,

            detail="User not found"

        )



    user.is_active=data.is_active


    db.commit()



    return {

        "message":"User status updated",

        "user_id":user_id,

        "is_active":user.is_active

    }





# ==========================================
# GET PROVIDERS
# ==========================================

@router.get("/providers")
def get_providers(

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    providers=db.query(ServiceProvider).all()


    return {

        "count":len(providers),

        "providers":providers

    }




# ==========================================
# VERIFY PROVIDER
# ==========================================

@router.put("/provider/verify/{provider_id}")
def verify_provider(

    provider_id:int,

    data:ProviderVerify,

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    provider=db.query(ServiceProvider).filter(

        ServiceProvider.provider_id==provider_id

    ).with_for_update().first()



    if not provider:

        raise HTTPException(

            status_code=404,

            detail="Provider not found"

        )



    provider.verified = data.is_verified


    db.commit()



    return {

        "message":"Provider verification updated",

        "provider_id":provider_id,

        "is_verified":provider.verified

    }





# ==========================================
# GET EMERGENCIES
# ==========================================

@router.get("/emergencies")
def get_emergencies(

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    emergencies=db.query(Emergency).all()


    return {

        "count":len(emergencies),

        "emergencies":emergencies

    }





# ==========================================
# STATISTICS
# ==========================================

@router.get(
    "/statistics",
    response_model=AdminStatistics
)
def statistics(

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    payments=db.query(Payment).filter(

        Payment.payment_status=="success"

    ).all()



    return {

        "total_users":db.query(User).count(),

        "total_providers":db.query(ServiceProvider).count(),

        "total_emergencies":db.query(Emergency).count(),

        "total_requests":db.query(ServiceRequest).count(),

        "total_revenue":sum(

            float(p.amount)

            for p in payments

        )

    }





# ==========================================
# ADMIN DASHBOARD
# ==========================================

@router.get(

    "/dashboard",

    response_model=AdminDashboardResponse

)
def dashboard(

    db:Session=Depends(get_db),

    admin:Admin=Depends(get_current_admin)

):


    payments=db.query(Payment).filter(

        Payment.payment_status=="success"

    ).all()



    return {


        "total_users":

        db.query(User).count(),



        "total_providers":

        db.query(ServiceProvider).count(),



        "total_emergencies":

        db.query(Emergency).count(),



        "total_requests":

        db.query(ServiceRequest).count(),



        "pending_requests":

        db.query(ServiceRequest).filter(

            ServiceRequest.request_status=="pending"

        ).count(),



        "completed_requests":

        db.query(ServiceRequest).filter(

            ServiceRequest.request_status=="completed"

        ).count(),



        "total_revenue":

        sum(

            float(p.amount)

            for p in payments

        )

    }
