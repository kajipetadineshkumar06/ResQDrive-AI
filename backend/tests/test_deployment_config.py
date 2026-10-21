import os
import unittest
from unittest.mock import patch

from deployment_config import (
    auto_create_tables_enabled,
    get_cors_origins,
    get_ollama_settings,
    scheduler_enabled,
)


class DeploymentConfigTests(unittest.TestCase):
    def test_development_uses_local_cors_origins_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                get_cors_origins(),
                [
                    "http://localhost:5174",
                    "http://127.0.0.1:5174",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ],
            )

    def test_production_requires_https_origin(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CORS_ALLOWED_ORIGINS"):
                get_cors_origins()

    def test_production_rejects_wildcard_origin(self):
        env = {"APP_ENV": "production", "CORS_ALLOWED_ORIGINS": "*"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "wildcard"):
                get_cors_origins()

    def test_production_rejects_non_https_origin(self):
        env = {"APP_ENV": "production", "CORS_ALLOWED_ORIGINS": "http://example.test"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "HTTPS"):
                get_cors_origins()

    def test_ollama_is_disabled_by_default_and_has_bounded_timeout(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_ollama_settings()
        self.assertFalse(settings["enabled"])
        self.assertLessEqual(settings["timeout_seconds"], 10)

    def test_ollama_timeout_cannot_exceed_ten_seconds(self):
        with patch.dict(os.environ, {"OLLAMA_TIMEOUT_SECONDS": "11"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "1 to 10"):
                get_ollama_settings()

    def test_automatic_table_creation_is_off_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(auto_create_tables_enabled())

    def test_production_forbids_automatic_table_creation(self):
        env = {"APP_ENV": "production", "AUTO_CREATE_TABLES": "true"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "production"):
                auto_create_tables_enabled()

    def test_scheduler_remains_enabled_by_default_in_development(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(scheduler_enabled())

    def test_production_requires_an_explicit_scheduler_choice(self):
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SCHEDULER_ENABLED"):
                scheduler_enabled()

    def test_production_scheduler_can_be_explicitly_enabled_or_disabled(self):
        for value, expected in (("true", True), ("false", False)):
            with self.subTest(value=value):
                env = {"APP_ENV": "production", "SCHEDULER_ENABLED": value}
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(scheduler_enabled(), expected)

    def test_invalid_scheduler_value_is_rejected(self):
        with patch.dict(
            os.environ,
            {"APP_ENV": "test", "SCHEDULER_ENABLED": "sometimes"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "SCHEDULER_ENABLED"):
                scheduler_enabled()


if __name__ == "__main__":
    unittest.main()
