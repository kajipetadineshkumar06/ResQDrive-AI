from passlib.context import CryptContext

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from database import get_db

from models.admin import Admin
from auth.admin_jwt import create_admin_token, decode_admin_token



# ==========================================
# PASSWORD HASHING
# ==========================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)



# ==========================================
# PASSWORD FUNCTIONS
# ==========================================

def verify_password(
    plain_password,
    hashed_password
):

    return pwd_context.verify(
        plain_password,
        hashed_password
    )



def hash_password(password):

    return pwd_context.hash(password)




# ==========================================
# TOKEN READER
# ==========================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/admin/login"
)



# ==========================================
# GET CURRENT ADMIN
# ==========================================

def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin token",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )


    payload = decode_admin_token(token)
    if payload is None:
        raise credentials_exception

    admin_id = payload.get("sub")
    if admin_id is None:
        raise credentials_exception


    admin = db.query(Admin).filter(
        Admin.admin_id == int(admin_id)
    ).first()



    if admin is None or not admin.is_active:

        raise credentials_exception



    return admin
