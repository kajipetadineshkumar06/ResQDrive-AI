"""Explicit one-time bootstrap for the first administrator account.

Run from the backend directory with ``python -m admin_bootstrap`` after the
database schema has been provisioned. The command is disabled unless
ADMIN_BOOTSTRAP_ENABLED is explicitly true.
"""

import getpass
import hmac
import os
import sys
from collections.abc import Mapping
from pathlib import Path


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}


def bootstrap_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the one-time bootstrap command was explicitly enabled."""
    values = os.environ if environ is None else environ
    raw_value = values.get("ADMIN_BOOTSTRAP_ENABLED", "false").strip().lower()
    if raw_value in _TRUE_VALUES:
        return True
    if raw_value in _FALSE_VALUES:
        return False
    raise RuntimeError("ADMIN_BOOTSTRAP_ENABLED must be true or false.")


def bootstrap_first_admin(db, *, name: str, email: str, password: str):
    """Create the first admin only when the explicit bootstrap switch is on."""
    if not bootstrap_enabled():
        raise RuntimeError("Admin bootstrap is disabled.")
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("The initial admin password must be at least 12 characters.")

    from auth.hashing import hash_password
    from models.admin import Admin
    from schemas.admin import AdminCreate

    admin_data = AdminCreate(
        name=name.strip(),
        email=email.strip().lower(),
        password=password,
    )

    if db.query(Admin).first() is not None:
        raise RuntimeError("Admin bootstrap is already complete.")

    admin = Admin(
        name=admin_data.name,
        email=str(admin_data.email),
        password=hash_password(admin_data.password),
    )

    try:
        db.add(admin)
        db.commit()
        db.refresh(admin)
    except Exception:
        db.rollback()
        raise

    return admin


def main() -> int:
    """Prompt securely and create one initial admin without exposing credentials."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().with_name(".env"), override=False)

    try:
        if not bootstrap_enabled():
            print("Admin bootstrap is disabled. Explicitly enable it for this one-time command.")
            return 2

        name = input("Initial admin name: ").strip()
        email = input("Initial admin email: ").strip()
        password = getpass.getpass("Initial admin password: ")
        confirmation = getpass.getpass("Confirm initial admin password: ")

        if not hmac.compare_digest(password.encode("utf-8"), confirmation.encode("utf-8")):
            print("The password entries did not match.", file=sys.stderr)
            return 2

        from database import SessionLocal

        with SessionLocal() as db:
            bootstrap_first_admin(
                db,
                name=name,
                email=email,
                password=password,
            )
    except (EOFError, KeyboardInterrupt):
        print("Admin bootstrap cancelled.", file=sys.stderr)
        return 130
    except Exception:
        # Database and validation exceptions can contain submitted values. Keep
        # console output generic and never echo passwords or database parameters.
        print("Admin bootstrap failed. Check configuration and database readiness.", file=sys.stderr)
        return 1

    print("Initial admin created. Disable ADMIN_BOOTSTRAP_ENABLED before serving the API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
