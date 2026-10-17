"""Shared validation for application signing secrets."""

import hmac
import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=BACKEND_ENV_FILE, override=False)

MIN_SIGNING_SECRET_LENGTH = 32
_PLACEHOLDER_MARKERS = (
    "your-",
    "your_",
    "replace",
    "placeholder",
    "change-me",
    "change_me",
    "changeme",
    "example",
    "sample",
)
_RELATED_SECRET_NAMES = {
    "JWT_SECRET_KEY": "ADMIN_JWT_SECRET_KEY",
    "ADMIN_JWT_SECRET_KEY": "JWT_SECRET_KEY",
}


def require_signing_secret(name: str) -> str:
    """Return a configured signing secret or fail without exposing its value."""
    secret = os.getenv(name)
    if secret is None or not secret.strip():
        raise RuntimeError(f"{name} is required and must not be empty.")

    if secret != secret.strip():
        raise RuntimeError(f"{name} must not contain surrounding whitespace.")

    if len(secret.encode("utf-8")) < MIN_SIGNING_SECRET_LENGTH:
        raise RuntimeError(
            f"{name} must contain at least {MIN_SIGNING_SECRET_LENGTH} bytes."
        )

    normalized = secret.lower()
    if any(marker in normalized for marker in _PLACEHOLDER_MARKERS):
        raise RuntimeError(f"{name} must not use a placeholder value.")

    other_name = _RELATED_SECRET_NAMES.get(name)
    other_secret = os.getenv(other_name) if other_name else None
    if other_secret and hmac.compare_digest(secret, other_secret):
        raise RuntimeError(f"{name} must differ from {other_name}.")

    return secret
