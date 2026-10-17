"""Isolated coverage for authenticated admin creation and bootstrap policy."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Router imports construct an engine only; all test persistence uses isolated SQLite.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["JWT_SECRET_KEY"] = "unit-test-customer-signing-key-0123456789"
os.environ["ADMIN_JWT_SECRET_KEY"] = "unit-test-admin-signing-key-9876543210"

from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from admin_bootstrap import bootstrap_enabled, bootstrap_first_admin
from auth.admin_jwt import create_admin_token
from auth.hashing import hash_password, verify_password
from auth.jwt_handler import create_access_token, decode_access_token
from models.admin import Admin
from routers import admin as admin_router
from auth.admin_oauth2 import get_current_admin, oauth2_scheme
from schemas.admin import AdminCreate, AdminResponse


class AdminProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Admin.__table__.create(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.db = self.session_factory()

    def tearDown(self):
        self.db.close()
        Admin.__table__.drop(self.engine)
        self.engine.dispose()

    def _assert_all_admin_routes_require_admin(self):
        for route in admin_router.router.routes:
            self.assertTrue(
                any(
                    dependency.call is get_current_admin
                    for dependency in route.dependant.dependencies
                ),
                f"Admin route {route.path} is missing its admin authentication dependency",
            )

    @staticmethod
    def _resolve_immediate_dependency(coroutine):
        try:
            coroutine.send(None)
        except StopIteration as result:
            return result.value

    def _create_admin(self, *, email="existing-admin@example.com", active=True):
        admin = Admin(
            name="Existing Admin",
            email=email,
            password=hash_password("isolated-existing-admin-password"),
            is_active=active,
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def test_unauthenticated_request_cannot_create_admin(self):
        self._assert_all_admin_routes_require_admin()
        request = Request(
            {
                "type": "http",
                "headers": [],
            }
        )

        with self.assertRaises(HTTPException) as error:
            self._resolve_immediate_dependency(oauth2_scheme(request))

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(self.db.query(Admin).count(), 0)

    def test_authenticated_customer_cannot_create_admin(self):
        self._assert_all_admin_routes_require_admin()
        customer_token = create_access_token(
            {"sub": "42", "email": "customer@example.com"}
        )
        self.assertIsNotNone(decode_access_token(customer_token))

        with self.assertRaises(HTTPException) as error:
            get_current_admin(customer_token, self.db)

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(self.db.query(Admin).count(), 0)

    def test_only_active_admin_can_create_admin_through_protected_route(self):
        self._assert_all_admin_routes_require_admin()
        existing_admin = self._create_admin()
        token = create_admin_token(
            {
                "sub": str(existing_admin.admin_id),
                "email": existing_admin.email,
            }
        )

        authorized_admin = get_current_admin(token, self.db)
        created_response = admin_router.create_admin(
            AdminCreate(
                name="New Admin",
                email="new-admin@example.com",
                password="TEST_ONLY_NEW_ADMIN_PASSWORD_2026!",
            ),
            authorized_admin,
            self.db,
        )
        response = AdminResponse.model_validate(created_response)
        self.assertNotIn("password", response.model_dump())

        self.db.expire_all()
        created = self.db.query(Admin).filter(
            Admin.email == "new-admin@example.com"
        ).first()
        self.assertIsNotNone(created)
        self.assertFalse(
            created.password == "isolated-new-admin-password",
            "New admin credential was stored as plaintext",
        )
        self.assertTrue(
            verify_password("isolated-new-admin-password", created.password)
        )

    def test_inactive_admin_cannot_create_admin(self):
        self._assert_all_admin_routes_require_admin()
        inactive_admin = self._create_admin(active=False)
        token = create_admin_token(
            {
                "sub": str(inactive_admin.admin_id),
                "email": inactive_admin.email,
            }
        )

        with self.assertRaises(HTTPException) as error:
            get_current_admin(token, self.db)

        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(self.db.query(Admin).count(), 1)

    def test_bootstrap_is_disabled_by_default_in_production(self):
        production_environment = {"APP_ENV": "production"}
        self.assertFalse(bootstrap_enabled(production_environment))

        with patch.dict(os.environ, production_environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "disabled"):
                bootstrap_first_admin(
                    self.db,
                    name="Initial Admin",
                    email="initial-admin@example.com",
                    password="TEST_ONLY_BOOTSTRAP_PASSWORD_2026!",
                )

        self.assertEqual(self.db.query(Admin).count(), 0)

    def test_bootstrap_cannot_be_reused_after_success(self):
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "ADMIN_BOOTSTRAP_ENABLED": "true"},
            clear=True,
        ):
            created = bootstrap_first_admin(
                self.db,
                name="Initial Admin",
                email="initial-admin@example.com",
                password="TEST_ONLY_BOOTSTRAP_PASSWORD_2026!",
            )
            self.assertIsNotNone(created.admin_id)
            self.assertTrue(
                verify_password(
                    "isolated-initial-admin-password",
                    created.password,
                )
            )

            with self.assertRaisesRegex(RuntimeError, "already complete"):
                bootstrap_first_admin(
                    self.db,
                    name="Second Initial Admin",
                    email="second-admin@example.com",
                    password="TEST_ONLY_BOOTSTRAP_PASSWORD_2026!",
                )

        self.assertEqual(self.db.query(Admin).count(), 1)


if __name__ == "__main__":
    unittest.main()
