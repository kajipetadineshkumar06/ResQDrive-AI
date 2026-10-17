"""Database-free regression tests for admin password storage and login."""

import os
import sys
import unittest
import hmac
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure imports construct only an isolated SQLite engine; tests use fake sessions
# and never open a database connection.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["JWT_SECRET_KEY"] = "unit-test-customer-signing-key-0123456789"
os.environ["ADMIN_JWT_SECRET_KEY"] = "unit-test-admin-signing-key-9876543210"

from fastapi import HTTPException
from auth.admin_oauth2 import hash_password as hash_bcrypt_password
from auth.hashing import hash_password as hash_pbkdf2_password
from auth.hashing import verify_password as verify_pbkdf2_password
from models.admin import Admin
from routers import admin as admin_router
from routers import admin_auth as admin_auth_router
from schemas.admin import AdminCreate


class _FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_conditions):
        return self

    def first(self):
        return self.result


class _FakeSession:
    def __init__(self, result=None):
        self.result = result
        self.added = None
        self.commits = 0

    def query(self, _model):
        return _FakeQuery(self.result)

    def add(self, value):
        self.added = value
        self.result = value

    def commit(self):
        self.commits += 1

    def refresh(self, _value):
        return None


def _make_admin(stored_password):
    admin = SimpleNamespace(
        admin_id=73,
        name="Isolated Admin",
        email="admin@example.com",
        is_active=True,
        password=stored_password,
        roles=("administrator",),
        permissions=("manage_requests",),
    )
    return admin


def _login(admin, submitted_password, db):
    form = SimpleNamespace(username=admin.email, password=submitted_password)
    with patch.object(admin_auth_router, "create_admin_token", return_value="isolated-token"):
        return admin_auth_router.admin_login(form, db)


class AdminPasswordAuthTests(unittest.TestCase):
    def test_new_admin_password_is_stored_as_pbkdf2_hash(self):
        db = _FakeSession()
        submitted_password = "isolated-new-admin-password"

        created = admin_router.create_admin(
            AdminCreate(
                name="Isolated Admin",
                email="new-admin@example.com",
                password=submitted_password,
            ),
            _make_admin("unused-authorized-admin-password"),
            db,
        )

        self.assertIs(created, db.added)
        self.assertFalse(
            created.password == submitted_password,
            "New admin password was stored as plaintext",
        )
        self.assertTrue(verify_pbkdf2_password(submitted_password, created.password))
        self.assertLessEqual(len(created.password), 255)
        self.assertEqual(db.commits, 1)

    def test_pbkdf2_admin_password_login_succeeds_without_rehashing(self):
        submitted_password = "isolated-pbkdf2-admin-password"
        encoded = hash_pbkdf2_password(submitted_password)
        admin = _make_admin(encoded)
        db = _FakeSession(admin)

        result = _login(admin, submitted_password, db)

        self.assertEqual(result["token_type"], "bearer")
        self.assertIs(admin.password, encoded)
        self.assertEqual(db.commits, 0)

    def test_existing_bcrypt_admin_password_login_succeeds(self):
        submitted_password = "isolated-bcrypt-admin-password"
        admin = _make_admin(hash_bcrypt_password(submitted_password))
        db = _FakeSession(admin)

        result = _login(admin, submitted_password, db)

        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(db.commits, 0)

    def test_wrong_password_uses_same_generic_response_for_known_and_missing_admin(self):
        admin = _make_admin(hash_pbkdf2_password("isolated-correct-password"))
        incorrect_db = _FakeSession(admin)
        missing_db = _FakeSession()
        incorrect_form = SimpleNamespace(
            username=admin.email,
            password="TEST_ONLY_WRONG_ADMIN_PASSWORD_2026!",
        )
        missing_form = SimpleNamespace(
            username="missing@example.com",
            password="TEST_ONLY_WRONG_ADMIN_PASSWORD_2026!",
        )

        with self.assertRaises(HTTPException) as incorrect_error:
            admin_auth_router.admin_login(incorrect_form, incorrect_db)
        with self.assertRaises(HTTPException) as missing_error:
            admin_auth_router.admin_login(missing_form, missing_db)

        self.assertEqual(incorrect_error.exception.status_code, 401)
        self.assertEqual(missing_error.exception.status_code, 401)
        self.assertEqual(incorrect_error.exception.detail, "Invalid email or password")
        self.assertEqual(missing_error.exception.detail, "Invalid email or password")

    def test_legacy_plaintext_login_upgrades_password_and_preserves_admin_access_fields(self):
        submitted_password = "isolated-legacy-admin-password"
        admin = _make_admin(submitted_password)
        before = (
            admin.admin_id,
            admin.name,
            admin.email,
            admin.is_active,
            admin.roles,
            admin.permissions,
        )
        db = _FakeSession(admin)

        result = _login(admin, submitted_password, db)

        after = (
            admin.admin_id,
            admin.name,
            admin.email,
            admin.is_active,
            admin.roles,
            admin.permissions,
        )
        self.assertEqual(result["token_type"], "bearer")
        self.assertFalse(
            admin.password == submitted_password,
            "Legacy password was not upgraded",
        )
        self.assertTrue(verify_pbkdf2_password(submitted_password, admin.password))
        self.assertEqual(db.commits, 1)
        self.assertEqual(after, before)

    def test_wrong_legacy_password_does_not_upgrade_or_commit(self):
        admin = _make_admin("isolated-legacy-admin-password")
        original_password = admin.password
        db = _FakeSession(admin)
        form = SimpleNamespace(
            username=admin.email,
            password="TEST_ONLY_WRONG_LEGACY_PASSWORD_2026!",
        )

        with self.assertRaises(HTTPException) as error:
            admin_auth_router.admin_login(form, db)

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.detail, "Invalid email or password")
        self.assertTrue(
            hmac.compare_digest(
                admin.password.encode("utf-8"),
                original_password.encode("utf-8"),
            ),
            "Wrong legacy password changed the stored credential",
        )
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
