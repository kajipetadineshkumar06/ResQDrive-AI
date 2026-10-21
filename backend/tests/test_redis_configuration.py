"""Database-free tests for Redis client configuration."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.redis_client import create_redis_client


class RedisConfigurationTests(unittest.TestCase):
    def test_development_retains_the_existing_local_redis_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("core.redis_client.redis.Redis") as redis_factory:
                create_redis_client()

        redis_factory.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=False,
        )

    def test_configured_url_is_used_without_connecting(self):
        with patch.dict(
            os.environ,
            {"REDIS_URL": "redis://redis.example.invalid:6379/2"},
            clear=True,
        ):
            with patch("core.redis_client.redis.Redis.from_url") as from_url:
                create_redis_client()

        from_url.assert_called_once_with(
            "redis://redis.example.invalid:6379/2",
            decode_responses=False,
        )


if __name__ == "__main__":
    unittest.main()
