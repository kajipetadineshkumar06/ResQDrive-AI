# ==========================================
# database.py
# ==========================================

import os

from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

from sqlalchemy import create_engine
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

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


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