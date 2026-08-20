import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from agents.models import DiagnosticReport, InvestigationResult
from app.api import create_app
from app.store import InvestigationStore


def successful_runner(service: str, alert_message: str) -> InvestigationResult:
    return InvestigationResult(
        report=DiagnosticReport(
            status="inconclusive",
            root_cause=None,
            confidence=0.3,
        ),
        tool_calls=["get_metrics"],
        turns=1,
    )


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Path(self.temporary_directory.name) / "investigations.db"
        self.store = InvestigationStore(database)
        self.client = TestClient(create_app(store=self.store, runner=successful_runner))

    def tearDown(self):
        self.client.close()
        self.temporary_directory.cleanup()

    def test_health_is_read_only(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "mode": "read-only"})

    def test_investigation_is_persisted_and_completed(self):
        response = self.client.post(
            "/investigations",
            json={"service": "pricing-service", "alert_message": "Latency alert"},
        )
        self.assertEqual(response.status_code, 202)
        investigation_id = response.json()["id"]

        stored = self.client.get(f"/investigations/{investigation_id}")
        self.assertEqual(stored.status_code, 200)
        self.assertEqual(stored.json()["status"], "completed")
        self.assertEqual(stored.json()["result"]["report"]["status"], "inconclusive")

    def test_invalid_request_is_rejected(self):
        response = self.client.post(
            "/investigations",
            json={"service": "", "alert_message": "Latency alert", "extra": True},
        )
        self.assertEqual(response.status_code, 422)

    def test_missing_investigation_returns_404(self):
        response = self.client.get("/investigations/does-not-exist")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
