import os
import unittest
from unittest.mock import patch

from auth.jwt_settings import require_signing_secret


class RequiredSigningSecretTests(unittest.TestCase):
    def test_both_signing_secret_names_are_required(self):
        with patch.dict(os.environ, {}, clear=True):
            for name in ("JWT_SECRET_KEY", "ADMIN_JWT_SECRET_KEY"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(RuntimeError, name):
                        require_signing_secret(name)

    def test_empty_short_and_placeholder_values_are_rejected(self):
        for value in ("", "short", "replace-with-a-real-value"):
            with self.subTest(value_kind=len(value)):
                with patch.dict(os.environ, {"JWT_SECRET_KEY": value}, clear=True):
                    with self.assertRaises(RuntimeError):
                        require_signing_secret("JWT_SECRET_KEY")

    def test_customer_and_admin_secrets_must_differ(self):
        same_value = "x" * 40
        env = {
            "JWT_SECRET_KEY": same_value,
            "ADMIN_JWT_SECRET_KEY": same_value,
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "must differ"):
                require_signing_secret("JWT_SECRET_KEY")

    def test_distinct_non_placeholder_secrets_are_accepted(self):
        env = {
            "JWT_SECRET_KEY": "SYNTHETIC_CUSTOMER_SIGNING_FIXTURE_00001",
            "ADMIN_JWT_SECRET_KEY": "SYNTHETIC_ADMIN_SIGNING_FIXTURE_00000001",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(len(require_signing_secret("JWT_SECRET_KEY")), 40)
            self.assertEqual(len(require_signing_secret("ADMIN_JWT_SECRET_KEY")), 40)


if __name__ == "__main__":
    unittest.main()