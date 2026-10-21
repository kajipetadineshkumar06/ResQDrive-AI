"""Database-free HTTP coverage for protected job-management routes."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Router imports build an engine but the dependency below uses only a fake session.
_test_environment = patch.dict(
    os.environ,
    {
        "DATABASE_URL": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "JOB_ROUTER_TEST_CUSTOMER_SECRET_0123456789",
        "ADMIN_JWT_SECRET_KEY": "JOB_ROUTER_TEST_ADMIN_SECRET_9876543210",
    },
    clear=False,
)
_test_environment.start()

from fastapi import HTTPException
from starlette.requests import Request

from auth.admin_jwt import create_admin_token
from auth.jwt_handler import create_access_token
from auth.admin_oauth2 import get_current_admin, oauth2_scheme
from database import get_db
from routers import background_jobs, jobs
from tasks import scheduler as scheduler_module

_test_environment.stop()


class _FakeQuery:
    def __init__(self, admin):
        self.admin = admin

    def filter(self, _condition):
        return self

    def first(self):
        return self.admin


class _FakeDatabase:
    def __init__(self, admin):
        self.admin = admin

    def query(self, _model):
        return _FakeQuery(self.admin)


def _resolve_immediate(coroutine):
    """Resolve FastAPI's no-I/O OAuth2 header parser without an event loop."""
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value


class JobRouterSecurityTests(unittest.TestCase):
    def setUp(self):
        self.admin = SimpleNamespace(admin_id=41, is_active=True)
        self.database = _FakeDatabase(self.admin)

    @staticmethod
    def _admin_headers():
        token = create_admin_token({"sub": "41"})
        return {"Authorization": f"Bearer {token}"}

    def test_every_state_changing_job_route_requires_active_admin_auth(self):
        expected_routes = {
            ("POST", "/jobs/request-timeout/{request_id}"),
            ("POST", "/jobs/release-provider/{provider_id}"),
            ("POST", "/jobs/test-timeout/{request_id}"),
            ("POST", "/jobs/enqueue/release-provider/{provider_id}"),
        }
        actual_routes = set()
        for router in (jobs.router, background_jobs.router):
            for route in router.routes:
                if hasattr(route, "methods"):
                    for method in route.methods:
                        actual_routes.add((method, route.path))
                    self.assertTrue(
                        any(
                            dependency.call is get_current_admin
                            for dependency in route.dependant.dependencies
                        ),
                        f"{route.path} is missing the admin dependency",
                    )
                    admin_dependency = next(
                        dependency
                        for dependency in route.dependant.dependencies
                        if dependency.call is get_current_admin
                    )
                    self.assertTrue(oauth2_scheme.auto_error)
                    self.assertTrue(
                        any(
                            dependency.call is oauth2_scheme
                            for dependency in admin_dependency.dependencies
                        ),
                        f"{route.path} does not require an OAuth2 bearer token",
                    )
        self.assertEqual(actual_routes, expected_routes)

    def test_missing_credentials_are_rejected_by_the_route_auth_dependency(self):
        for router in (jobs.router, background_jobs.router):
            for route in router.routes:
                if not hasattr(route, "dependant"):
                    continue
                with self.subTest(path=route.path):
                    scope = {
                        "type": "http",
                        "method": "POST",
                        "path": route.path,
                        "headers": [],
                        "query_string": b"",
                        "server": ("testserver", 80),
                        "client": ("testclient", 50000),
                        "scheme": "http",
                    }
                    with self.assertRaises(HTTPException) as error:
                        _resolve_immediate(oauth2_scheme(Request(scope)))
                    self.assertEqual(error.exception.status_code, 401)

    def test_customer_token_is_not_authorized_for_admin_job_routes(self):
        customer_token = create_access_token({"sub": "customer-7"})
        with self.assertRaises(HTTPException) as error:
            get_current_admin(customer_token, self.database)
        self.assertEqual(error.exception.status_code, 401)

    def test_inactive_admin_is_rejected(self):
        self.admin.is_active = False
        token = create_admin_token({"sub": "41"})
        with self.assertRaises(HTTPException) as error:
            get_current_admin(token, self.database)
        self.assertEqual(error.exception.status_code, 401)

    def test_active_admin_can_use_direct_and_queued_job_routes(self):
        active_admin = get_current_admin(
            create_admin_token({"sub": "41"}),
            self.database,
        )
        self.assertTrue(active_admin.is_active)
        queued = SimpleNamespace(id="isolated-job-id")
        with (
            patch.object(jobs, "cancel_expired_request", return_value={"processed": True}) as timeout,
            patch.object(jobs, "release_provider", return_value={"released": True}) as release,
            patch.object(background_jobs.task_queue, "enqueue", return_value=queued) as enqueue,
        ):
            direct_timeout = jobs.request_timeout(12)
            direct_release = jobs.provider_release(13)
            queued_timeout = background_jobs.test_timeout(14)
            queued_release = background_jobs.test_release(15)

        self.assertEqual(direct_timeout, {"processed": True})
        self.assertEqual(direct_release, {"released": True})
        self.assertTrue(queued_timeout["success"])
        self.assertTrue(queued_release["success"])
        timeout.assert_called_once_with(12)
        release.assert_called_once_with(13)
        self.assertEqual(enqueue.call_count, 2)

    def test_internal_scheduler_jobs_remain_registered(self):
        with (
            patch.object(scheduler_module.scheduler, "add_job") as add_job,
            patch.object(scheduler_module.scheduler, "start") as start,
            patch("builtins.print"),
        ):
            scheduler_module.start_scheduler()

        self.assertEqual(add_job.call_count, 3)
        registered_functions = [call.args[0] for call in add_job.call_args_list]
        self.assertEqual(
            registered_functions,
            [
                scheduler_module.auto_assign_requests,
                scheduler_module.recover_timed_out_requests,
                scheduler_module.send_notifications,
            ],
        )
        start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
