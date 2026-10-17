"""Focused, database-free tests for signing-secret configuration."""

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class SigningSecretConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._environment = patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "customerSigningKeyForUnitTests0123456789ABCDEF",
                "ADMIN_JWT_SECRET_KEY": "adminSigningKeyForUnitTests9876543210ABCDEF",
            },
            clear=False,
        )
        cls._environment.start()

        from auth import admin_jwt, jwt_handler

        cls.admin_jwt = importlib.reload(admin_jwt)
        cls.customer_jwt = importlib.reload(jwt_handler)
        cls.jwt_settings = importlib.import_module("auth.jwt_settings")

    @classmethod
    def tearDownClass(cls):
        cls._environment.stop()

    def assert_secret_rejected(self, name, value):
        with patch.dict(os.environ, clear=True):
            if value is not None:
                os.environ[name] = value
            with self.assertRaises(RuntimeError) as raised:
                self.jwt_settings.require_signing_secret(name)
        self.assertIn(name, str(raised.exception))
        if value:
            self.assertNotIn(value, str(raised.exception))

    def test_missing_empty_short_and_placeholder_secrets_are_rejected(self):
        for name in ("JWT_SECRET_KEY", "ADMIN_JWT_SECRET_KEY"):
            with self.subTest(name=name, state="missing"):
                self.assert_secret_rejected(name, None)
            with self.subTest(name=name, state="empty"):
                self.assert_secret_rejected(name, "")
            with self.subTest(name=name, state="short"):
                self.assert_secret_rejected(name, "short-value")
            with self.subTest(name=name, state="placeholder"):
                self.assert_secret_rejected(
                    name, "replace-with-a-placeholder-signing-secret-value"
                )

    def test_customer_and_admin_secrets_must_differ(self):
        repeated = "Abcd0123" * 6
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": repeated,
                "ADMIN_JWT_SECRET_KEY": repeated,
            },
            clear=True,
        ):
            with self.assertRaises(RuntimeError) as raised:
                self.jwt_settings.require_signing_secret("JWT_SECRET_KEY")
        self.assertNotIn(repeated, str(raised.exception))

    def test_customer_and_admin_tokens_validate_only_with_their_own_key(self):
        customer_token = self.customer_jwt.create_access_token(
            {"sub": "customer-test-subject"}
        )
        admin_token = self.admin_jwt.create_admin_token({"sub": "1"})

        self.assertIsNotNone(self.customer_jwt.decode_access_token(customer_token))
        self.assertIsNone(self.admin_jwt.decode_admin_token(customer_token))
        self.assertIsNotNone(self.admin_jwt.decode_admin_token(admin_token))
        self.assertIsNone(self.customer_jwt.decode_access_token(admin_token))


if __name__ == "__main__":
    unittest.main()
