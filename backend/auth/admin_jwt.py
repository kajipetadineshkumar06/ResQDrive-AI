"""Admin-only JWT signing and validation."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from auth.jwt_settings import require_signing_secret


SECRET_KEY = require_signing_secret("ADMIN_JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_admin_token(data: dict) -> str:
    payload = data.copy()
    payload.update(
        {
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "role": "admin",
        }
    )
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_admin_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
