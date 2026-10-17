# ==========================================
# routers/auth.py
# ==========================================

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from database import get_db

from models.models import User

from schemas.auth import (
    RegisterRequest,
    TokenResponse,
    UserProfile,
)

from auth.hashing import (
    verify_password,
    hash_password,
)

from auth.jwt_handler import create_access_token

from auth.oauth2 import get_current_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ==========================================
# REGISTER
# ==========================================

@router.post(
    "/register",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
):

    # --------------------------------------
    # Clean input
    # --------------------------------------

    full_name = user_data.full_name.strip()
    email = user_data.email.strip().lower()

    phone = (
        user_data.phone.strip()
        if user_data.phone
        else None
    )

    password = user_data.password


    # --------------------------------------
    # Validate full name
    # --------------------------------------

    if not full_name:

        raise HTTPException(
            status_code=400,
            detail="Full name is required.",
        )


    # --------------------------------------
    # Validate email
    # --------------------------------------

    if not email:

        raise HTTPException(
            status_code=400,
            detail="Email is required.",
        )


    # --------------------------------------
    # Validate password
    # --------------------------------------

    if len(password) < 8:

        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )


    # --------------------------------------
    # Check duplicate email
    # --------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )


    # --------------------------------------
    # Check duplicate phone
    # --------------------------------------

    if phone:

        existing_phone = (
            db.query(User)
            .filter(User.phone == phone)
            .first()
        )

        if existing_phone:

            raise HTTPException(
                status_code=409,
                detail="This phone number is already registered.",
            )


    # --------------------------------------
    # Hash password
    # --------------------------------------

    password_hash = hash_password(password)


    # --------------------------------------
    # Create user
    # --------------------------------------

    new_user = User(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=password_hash,
    )


    db.add(new_user)


    # --------------------------------------
    # Save database
    # --------------------------------------

    try:

        db.commit()

        db.refresh(new_user)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create account.",
        )


    # --------------------------------------
    # Return created user
    # --------------------------------------

    return new_user


# ==========================================
# LOGIN
# ==========================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    email = form_data.username.strip().lower()


    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )


    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


    if not verify_password(
        form_data.password,
        user.password_hash,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


    token = create_access_token(
        data={
            "sub": str(user.user_id),
            "email": user.email,
        }
    )


    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ==========================================
# CURRENT USER
# ==========================================

@router.get(
    "/me",
    response_model=UserProfile,
)
def get_profile(
    current_user: User = Depends(
        get_current_user
    ),
):

    return current_user