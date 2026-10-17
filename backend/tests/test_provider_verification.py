"""Regression tests for provider verification and assignment eligibility.

All tests use an isolated in-memory SQLite database. They never read or write
the configured MySQL databases.
"""

import os
import unittest
from datetime import timedelta
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models import Emergency, ServiceProvider, ServiceRequest, User
from models.provider_location import ProviderLocation
from agents.tool_registry import _find_available_providers
os.environ["JWT_SECRET_KEY"] = "unit-test-customer-signing-key-0123456789"
os.environ["ADMIN_JWT_SECRET_KEY"] = "unit-test-admin-signing-key-9876543210"
from routers.admin import verify_provider
from routers.provider_actions import accept_request
from routers.providers import get_available_providers
from routers.service_requests import create_service_request
from routers.tracking import track_provider
from schemas.admin import ProviderVerify
from schemas.service_provider import ProviderUpdate
from schemas.service_request import ServiceRequestCreate
from services.assignment_service import find_next_provider
from services import assignment_service, timeout_service
from services.nearby_service import find_nearest_provider
from tasks import auto_assign_requests as auto_assign_module


class ProviderVerificationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.db = self.session_factory()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def make_user(self, suffix="customer"):
        user = User(
            full_name="Verification Test User",
            email=f"{suffix}@example.test",
            password_hash="unused-test-hash",
        )
        self.db.add(user)
        self.db.flush()
        return user

    def make_provider(self, *, verified=False, available=True, user_id=None, phone="555-0100"):
        provider = ServiceProvider(
            name="Verification Test Provider",
            service_type="mechanic",
            phone=phone,
            location_lat=12.0,
            location_lng=77.0,
            is_available=available,
            verified=verified,
            is_tracking=False,
            user_id=user_id,
        )
        self.db.add(provider)
        self.db.flush()
        return provider

    def make_emergency(self, user):
        emergency = Emergency(
            user_id=user.user_id,
            emergency_type="vehicle breakdown",
            location_lat=12.0,
            location_lng=77.0,
            recommended_service="mechanic",
        )
        self.db.add(emergency)
        self.db.flush()
        return emergency

    def test_nearest_provider_does_not_select_unverified_provider(self):
        self.make_provider(verified=False)

        selected = find_nearest_provider(
            self.db,
            service_type="mechanic",
            latitude=12.0,
            longitude=77.0,
        )

        self.assertIsNone(selected)

    def test_tracking_returns_the_service_request_status(self):
        user = self.make_user()
        provider = self.make_provider(verified=True, user_id=user.user_id)
        emergency = self.make_emergency(user)
        request = ServiceRequest(
            emergency_id=emergency.emergency_id,
            provider_id=provider.provider_id,
            user_id=user.user_id,
            request_status="accepted",
        )
        self.db.add(request)
        self.db.flush()
        self.db.add(
            ProviderLocation(
                provider_id=provider.provider_id,
                latitude=12.0,
                longitude=77.0,
            )
        )
        self.db.flush()

        result = track_provider(emergency.emergency_id, self.db)

        self.assertEqual(result["status"], "accepted")

    def test_reassignment_search_only_returns_verified_provider(self):
        unverified = self.make_provider(verified=False, phone="555-0101")
        verified = self.make_provider(verified=True, phone="555-0102")

        selected = find_next_provider(
            self.db,
            service_type="mechanic",
            latitude=12.0,
            longitude=77.0,
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected.provider_id, verified.provider_id)
        self.assertNotEqual(selected.provider_id, unverified.provider_id)

    def test_customer_discovery_and_agent_tool_hide_unverified_providers(self):
        self.make_provider(verified=False)
        verified = self.make_provider(verified=True, phone="555-0102")

        public_results = get_available_providers(self.db)
        agent_results = _find_available_providers(self.db, "mechanic")

        self.assertEqual([p.provider_id for p in public_results], [verified.provider_id])
        self.assertEqual(agent_results["count"], 1)
        self.assertEqual(
            agent_results["providers"][0]["provider_id"],
            verified.provider_id,
        )

    def test_admin_verification_updates_the_persisted_model_field(self):
        provider = self.make_provider(verified=False)

        result = verify_provider(
            provider.provider_id,
            ProviderVerify(is_verified=True),
            self.db,
            admin=object(),
        )

        self.db.expire_all()
        persisted = self.db.get(ServiceProvider, provider.provider_id)
        self.assertTrue(persisted.verified)
        self.assertTrue(result["is_verified"])

    def test_provider_profile_update_rejects_verification_fields(self):
        with self.assertRaises(ValidationError):
            ProviderUpdate(
                name="Provider",
                service_type="mechanic",
                phone="555-0100",
                location_lat=12.0,
                location_lng=77.0,
                verified=True,
            )

        with self.assertRaises(ValidationError):
            ProviderUpdate(
                name="Provider",
                service_type="mechanic",
                phone="555-0100",
                location_lat=12.0,
                location_lng=77.0,
                is_available=True,
            )

    def test_direct_service_request_rejects_unverified_provider(self):
        user = self.make_user()
        emergency = self.make_emergency(user)
        provider = self.make_provider(verified=False)

        with self.assertRaises(HTTPException) as error:
            create_service_request(
                ServiceRequestCreate(
                    emergency_id=emergency.emergency_id,
                    provider_id=provider.provider_id,
                ),
                self.db,
                current_user=user,
            )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.db.query(ServiceRequest).count(), 0)
        self.assertTrue(provider.is_available)

    def test_direct_service_request_reserves_verified_provider(self):
        user = self.make_user()
        emergency = self.make_emergency(user)
        provider = self.make_provider(verified=True)

        request = create_service_request(
            ServiceRequestCreate(
                emergency_id=emergency.emergency_id,
                provider_id=provider.provider_id,
            ),
            self.db,
            current_user=user,
        )

        self.assertEqual(request.request_status, "pending")
        self.assertEqual(request.provider_id, provider.provider_id)
        self.assertFalse(provider.is_available)

    def test_unverified_provider_cannot_accept_an_existing_offer(self):
        user = self.make_user()
        emergency = self.make_emergency(user)
        provider = self.make_provider(verified=False, user_id=user.user_id)
        request = ServiceRequest(
            emergency_id=emergency.emergency_id,
            provider_id=provider.provider_id,
            user_id=user.user_id,
            request_status="pending",
        )
        self.db.add(request)
        self.db.flush()

        with self.assertRaises(HTTPException) as error:
            accept_request(request.request_id, self.db, current_user=user)

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(request.request_status, "pending")

    def test_scheduler_does_not_auto_assign_unverified_provider(self):
        user = self.make_user()
        emergency = self.make_emergency(user)
        provider = self.make_provider(verified=False)
        request = ServiceRequest(
            emergency_id=emergency.emergency_id,
            provider_id=None,
            user_id=user.user_id,
            request_status="pending",
        )
        self.db.add(request)
        self.db.commit()
        request_id = request.request_id

        original_factory = auto_assign_module.SessionLocal
        auto_assign_module.SessionLocal = self.session_factory
        try:
            auto_assign_module.auto_assign_requests()
        finally:
            auto_assign_module.SessionLocal = original_factory

        self.db.expire_all()
        persisted_request = self.db.get(ServiceRequest, request_id)
        self.db.refresh(provider)
        self.assertIsNone(persisted_request.provider_id)
        self.assertEqual(persisted_request.request_status, "pending")
        self.assertTrue(provider.is_available)

    def test_timeout_recovery_reassigns_only_to_verified_provider(self):
        user = self.make_user()
        emergency = self.make_emergency(user)
        old_provider = self.make_provider(
            verified=False,
            available=False,
            phone="555-0101",
        )
        self.make_provider(
            verified=False,
            available=True,
            phone="555-0102",
        )
        verified_provider = self.make_provider(
            verified=True,
            available=True,
            phone="555-0103",
        )
        from services.timeout_service import PROVIDER_TIMEOUT_SECONDS

        requested_at = (
            timeout_service.db_now()
            - timedelta(seconds=PROVIDER_TIMEOUT_SECONDS + 1)
        )
        request = ServiceRequest(
            emergency_id=emergency.emergency_id,
            provider_id=old_provider.provider_id,
            user_id=user.user_id,
            request_status="pending",
            requested_at=requested_at,
        )
        self.db.add(request)
        self.db.commit()
        request_id = request.request_id

        with (
            patch.object(timeout_service, "SessionLocal", self.session_factory),
            patch.object(timeout_service, "start_timeout"),
            patch.object(
                assignment_service,
                "calculate_reassignment_eta_minutes",
                return_value=None,
            ),
        ):
            timeout_service.recover_timed_out_requests()

        self.db.expire_all()
        persisted_request = self.db.get(ServiceRequest, request_id)
        self.db.refresh(old_provider)
        self.db.refresh(verified_provider)

        self.assertEqual(persisted_request.provider_id, verified_provider.provider_id)
        self.assertEqual(persisted_request.request_status, "pending")
        self.assertIn(old_provider.provider_id, persisted_request.excluded_provider_ids)
        self.assertTrue(old_provider.is_available)
        self.assertFalse(verified_provider.is_available)


if __name__ == "__main__":
    unittest.main()
