import hmac

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db
from models.admin import Admin

from auth.admin_oauth2 import (
    create_admin_token,
    verify_password as verify_bcrypt_password,
)
from auth.hashing import (
    hash_password,
    verify_password as verify_pbkdf2_password,
)


_BCRYPT_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$", "$2$")
_PBKDF2_HASH_PREFIX = "$pbkdf2-sha256$"


def _verify_admin_password(submitted_password: str, stored_value: str) -> tuple[bool, bool]:
    """Return (verified, is_legacy_plaintext) without treating hashes as plaintext."""
    if not isinstance(submitted_password, str) or not isinstance(stored_value, str):
        return False, False

    try:
        if stored_value.startswith(_PBKDF2_HASH_PREFIX):
            return verify_pbkdf2_password(submitted_password, stored_value), False

        if stored_value.startswith(_BCRYPT_HASH_PREFIXES):
            return verify_bcrypt_password(submitted_password, stored_value), False

        # A malformed or unrecognized hash must never fall through to the legacy
        # plaintext check. Legacy values written by the previous route were raw
        # passwords and did not use a Passlib hash prefix.
        if stored_value.startswith("$"):
            return False, False

        matches = hmac.compare_digest(
            submitted_password.encode("utf-8"),
            stored_value.encode("utf-8"),
        )
        return matches, matches
    except (TypeError, ValueError, UnicodeError):
        return False, False


router = APIRouter(
    prefix="/admin",
    tags=["Admin Authentication"]
)



@router.post("/login")
def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    admin = db.query(Admin).filter(
        Admin.email == form_data.username
    ).first()


    if not admin or not admin.is_active:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )


    verified, is_legacy_plaintext = _verify_admin_password(
        form_data.password,
        admin.password,
    )

    if not verified:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if is_legacy_plaintext:
        admin.password = hash_password(form_data.password)
        db.commit()


    token = create_admin_token(
        {
            "sub": str(admin.admin_id),
            "email": admin.email
        }
    )


    return {

        "access_token": token,

        "token_type": "bearer"

    }
