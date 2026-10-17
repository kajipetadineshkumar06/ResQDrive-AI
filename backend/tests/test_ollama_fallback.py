import unittest
from unittest.mock import patch

from services import ollama_emergency_service, vehicle_ai_service


class OllamaFallbackTests(unittest.TestCase):
    def test_emergency_classifier_skips_network_when_disabled(self):
        with (
            patch.object(ollama_emergency_service, "OLLAMA_ENABLED", False),
            patch.object(
                ollama_emergency_service.urllib.request,
                "urlopen",
                side_effect=AssertionError("network call must be skipped"),
            ),
        ):
            result = ollama_emergency_service.classify_emergency("flat tire")

        self.assertEqual(result["source"], "ollama_disabled")
        self.assertEqual(result["confidence"], 0)

    def test_vehicle_ai_uses_fallback_when_disabled(self):
        with (
            patch.object(vehicle_ai_service, "OLLAMA_ENABLED", False),
            patch.object(
                vehicle_ai_service.urllib.request,
                "urlopen",
                side_effect=AssertionError("network call must be skipped"),
            ),
        ):
            result = vehicle_ai_service.analyze_vehicle_problem("flat tire")

        self.assertIsInstance(result, dict)
        self.assertIn("source", result)


if __name__ == "__main__":
    unittest.main()