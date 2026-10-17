"""Validated runtime settings for deployment-sensitive behavior."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


BACKEND_ENV_FILE = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=BACKEND_ENV_FILE, override=False)

_LOCAL_CORS_ORIGINS = (
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
_ALLOWED_APP_ENVIRONMENTS = {"development", "test", "production"}


def app_environment() -> str:
    """Return a validated application environment name."""
    value = os.getenv("APP_ENV", "development").strip().lower()
    if value not in _ALLOWED_APP_ENVIRONMENTS:
        raise RuntimeError("APP_ENV must be development, test, or production.")
    return value


def is_production() -> bool:
    return app_environment() == "production"


def get_cors_origins() -> list[str]:
    """Read explicit browser origins; production requires HTTPS origins."""
    production = is_production()
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    origins = [item.strip().rstrip("/") for item in configured.split(",") if item.strip()]

    if not origins:
        if production:
            raise RuntimeError("CORS_ALLOWED_ORIGINS is required in production.")
        return list(_LOCAL_CORS_ORIGINS)

    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must not contain a wildcard.")

    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RuntimeError("CORS_ALLOWED_ORIGINS must contain valid origins.")
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise RuntimeError("CORS_ALLOWED_ORIGINS entries must be origins without paths.")
        if production and parsed.scheme != "https":
            raise RuntimeError("Production CORS origins must use HTTPS.")

    return origins


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true or false.")


def auto_create_tables_enabled() -> bool:
    """DDL at application startup is opt-in and forbidden in production."""
    enabled = _read_bool("AUTO_CREATE_TABLES", default=False)
    if enabled and is_production():
        raise RuntimeError("AUTO_CREATE_TABLES cannot be enabled in production.")
    return enabled


def get_ollama_settings() -> dict[str, object]:
    """Return bounded local Ollama settings; AI stays off by default."""
    enabled = _read_bool("OLLAMA_ENABLED", default=False)
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("OLLAMA_BASE_URL must be an HTTP or HTTPS base URL.")

    model = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
    if not model:
        raise RuntimeError("OLLAMA_MODEL must not be empty.")

    try:
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "5"))
    except ValueError as error:
        raise RuntimeError("OLLAMA_TIMEOUT_SECONDS must be a number from 1 to 10.") from error
    if not 1 <= timeout <= 10:
        raise RuntimeError("OLLAMA_TIMEOUT_SECONDS must be from 1 to 10.")

    return {
        "enabled": enabled,
        "model": model,
        "generate_url": f"{base_url}/api/generate",
        "tags_url": f"{base_url}/api/tags",
        "timeout_seconds": timeout,
    }