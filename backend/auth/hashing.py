# ==========================================
# auth/hashing.py
# ==========================================

from passlib.context import CryptContext


# ==========================================
# PASSWORD CONTEXT
# ==========================================

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)


# ==========================================
# HASH PASSWORD
# ==========================================

def hash_password(password: str) -> str:

    return pwd_context.hash(password)


# ==========================================
# VERIFY PASSWORD
# ==========================================

def verify_password(
    password: str,
    hashed_password: str
) -> bool:

    return pwd_context.verify(
        password,
        hashed_password
    )