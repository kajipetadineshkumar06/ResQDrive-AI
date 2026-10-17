"""Database-free coverage for the existing password hashing helpers."""

import os
import sys
import unittest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth.hashing import hash_password, verify_password


try:
    INSTALLED_BCRYPT_VERSION = version("bcrypt")
except PackageNotFoundError:
    INSTALLED_BCRYPT_VERSION = None


class CustomerPasswordHashingTests(unittest.TestCase):
    def test_password_hash_verifies_and_wrong_password_is_rejected(self):
        encoded = hash_password("isolated-customer-check-password")

        self.assertNotEqual(encoded, "isolated-customer-check-password")
        self.assertTrue(verify_password("isolated-customer-check-password", encoded))
        self.assertFalse(verify_password("different-isolated-check-password", encoded))


@unittest.skipUnless(
    INSTALLED_BCRYPT_VERSION == "4.0.1",
    "Admin bcrypt helper test requires the pinned bcrypt 4.0.1 runtime; no dependency installation is performed by this test.",
)
class AdminPasswordHashingTests(unittest.TestCase):
    def test_password_hash_verifies_and_wrong_password_is_rejected(self):
        test_environment = {
            "DATABASE_URL": "sqlite:///:memory:",
            "JWT_SECRET_KEY": "TEST_ONLY_CORRECT_PASSWORD_2026!",
            "ADMIN_JWT_SECRET_KEY": "TEST_ONLY_WRONG_PASSWORD_2026!_for_unit_harness",
        }
        with patch.dict(os.environ, test_environment, clear=False):
            from auth.admin_oauth2 import hash_password, verify_password

            encoded = hash_password("isolated-admin-check-password")
            self.assertNotEqual(encoded, "isolated-admin-check-password")
            self.assertTrue(verify_password("isolated-admin-check-password", encoded))
            self.assertFalse(verify_password("different-isolated-check-password", encoded))


if __name__ == "__main__":
    unittest.main()
