# ==========================================
# database.py
# ==========================================

import os
import ssl

from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


# ==========================================
# Load .env
# ==========================================

load_dotenv(
    Path(__file__).resolve().with_name(".env")
)


# ==========================================
# Database URL
# ==========================================

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


if not DATABASE_URL:

    required = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME"
    )

    missing = [
        name
        for name in required
        if not os.getenv(name)
    ]

    if missing:

        raise ValueError(
            "Set DATABASE_URL or the following "
            "variables in .env: "
            + ", ".join(missing)
        )

    DATABASE_URL = (
        "mysql+pymysql://"
        f"{quote_plus(os.environ['DB_USER'])}:"
        f"{quote_plus(os.environ['DB_PASSWORD'])}@"
        f"{os.environ['DB_HOST']}:"
        f"{os.environ['DB_PORT']}/"
        f"{os.environ['DB_NAME']}"
    )


# ==========================================
# Engine
# ==========================================

def _database_host(database_url: str) -> str | None:
    """Return the host from a SQLAlchemy URL without exposing its contents."""
    try:
        return make_url(database_url).host
    except Exception:
        raise RuntimeError("DATABASE_URL must be a valid SQLAlchemy URL.") from None


def _is_aiven_host(host: str | None) -> bool:
    normalized = (host or "").rstrip(".").lower()
    return normalized == "aivencloud.com" or normalized.endswith(".aivencloud.com")


def _verified_tls_context(ca_path: str) -> ssl.SSLContext:
    if not ca_path.strip():
        raise RuntimeError("DB_SSL_CA must point to a valid CA certificate file.")

    try:
        ca_file = Path(ca_path.strip()).expanduser()
        if not ca_file.is_file():
            raise OSError
        context = ssl.create_default_context(cafile=str(ca_file))
    except (OSError, RuntimeError, ssl.SSLError, ValueError):
        raise RuntimeError("DB_SSL_CA must point to a valid, readable CA certificate file.") from None

    if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise RuntimeError("Database TLS must verify the server certificate and hostname.")
    return context


_configured_db_host = (
    _database_host(DATABASE_URL)
    if os.getenv("DATABASE_URL")
    else os.getenv("DB_HOST")
)
_db_ssl_ca = os.getenv("DB_SSL_CA")

if _db_ssl_ca is not None:
    _connect_args = {"ssl": _verified_tls_context(_db_ssl_ca)}
elif _is_aiven_host(_configured_db_host):
    raise RuntimeError("DB_SSL_CA is required for Aiven MySQL connections.")
else:
    _connect_args = None

_engine_options = {"pool_pre_ping": True}
if _connect_args is not None:
    _engine_options["connect_args"] = _connect_args

engine = create_engine(DATABASE_URL, **_engine_options)


# ==========================================
# Session
# ==========================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ==========================================
# Base
# ==========================================

Base = declarative_base()


# ==========================================
# Database dependency
# ==========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()
