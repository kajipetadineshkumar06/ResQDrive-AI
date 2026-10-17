import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# The service imports SQLAlchemy models, but this test uses only a fake session.
# Force a local in-memory URL before importing backend modules; no connection is made.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import emergency_service


class FakeSession:
    def __init__(self, events):
        self.events = events

    def add(self, entity):
        self.events.append(("add", type(entity).__name__))

    def commit(self):
        self.events.append("commit")

    def refresh(self, entity):
        self.events.append(("refresh", type(entity).__name__))


class EmergencyPersistenceTests(unittest.TestCase):
    def test_emergency_is_committed_before_optional_ai_calls(self):
        events = []
        db = FakeSession(events)
        user = SimpleNamespace(user_id=7)
        request_data = SimpleNamespace(
            emergency_type="flat_tire",
            priority="high",
            description="flat tyre",
            vehicle_id=None,
            location_lat=1.0,
            location_lng=2.0,
        )

        def vehicle_ai(_description):
            events.append("vehicle_ai")
            return None

        def emergency_ai(_description):
            events.append("emergency_ai")
            return {
                "emergency_type": "flat_tire",
                "priority": "HIGH",
                "confidence": 90,
                "source": "ollama_qwen3",
            }

        with (
            patch.object(emergency_service, "OLLAMA_ENABLED", True),
            patch.object(emergency_service, "analyze_vehicle_problem", side_effect=vehicle_ai),
            patch.object(emergency_service, "classify_emergency", side_effect=emergency_ai),
            patch.object(emergency_service, "recommend_provider_type", return_value="mechanic"),
            patch.object(emergency_service, "find_nearest_provider", return_value=None),
        ):
            result = emergency_service.create_emergency_service(db, user, request_data)

        first_commit = events.index("commit")
        self.assertLess(first_commit, events.index("vehicle_ai"))
        self.assertLess(first_commit, events.index("emergency_ai"))
        self.assertIsNotNone(result["emergency"])
        self.assertEqual(result["emergency"].priority, "high")


    def test_ollama_failure_keeps_customer_emergency_details(self):
        events = []
        db = FakeSession(events)
        user = SimpleNamespace(user_id=7)
        request_data = SimpleNamespace(
            emergency_type="accident",
            priority="CRITICAL",
            description="collision",
            vehicle_id=None,
            location_lat=1.0,
            location_lng=2.0,
        )

        with (
            patch.object(emergency_service, "OLLAMA_ENABLED", True),
            patch.object(emergency_service, "analyze_vehicle_problem", return_value=None),
            patch.object(
                emergency_service,
                "classify_emergency",
                return_value={
                    "emergency_type": "other",
                    "priority": "MEDIUM",
                    "confidence": 0,
                    "source": "ollama_timeout",
                },
            ),
            patch.object(emergency_service, "recommend_provider_type", return_value="mechanic"),
            patch.object(emergency_service, "find_nearest_provider", return_value=None),
        ):
            result = emergency_service.create_emergency_service(db, user, request_data)

        self.assertEqual(result["emergency"].emergency_type, "accident")
        self.assertEqual(result["emergency"].priority, "critical")
if __name__ == "__main__":

    unittest.main()