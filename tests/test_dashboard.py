import unittest
from unittest.mock import patch

from app import create_app


class MonitoringDashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Demo Operator"
            session["user_role"] = "operator"

    @patch("app.db.get_dashboard_summary")
    def test_dashboard_uses_database_event_and_alert_values(self, get_dashboard_summary):
        get_dashboard_summary.return_value = {
            "database_available": True,
            "accident_count": 3,
            "recent_alerts": [{
                "alert_id": 1, "alert_status": "sent", "alert_channel": "email",
                "alert_message": "Event notification sent", "created_at": "2026-09-10 12:00:00",
                "severity": "HIGH",
            }],
        }
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Logged accidents", response.data)
        self.assertIn(b">3<", response.data)
        self.assertIn(b"Event notification sent", response.data)
        self.assertIn(b"MySQL connected", response.data)


if __name__ == "__main__":
    unittest.main()
