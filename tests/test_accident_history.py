import unittest
from unittest.mock import patch

from app import create_app


class AccidentHistoryTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Test Admin"
            session["user_role"] = "admin"

    @patch("app.db.get_accident_history")
    def test_history_filters_by_severity(self, get_accident_history):
        get_accident_history.return_value = [{
            "accident_event_id": 9, "event_status": "detected", "created_at": "2026-09-10 12:00:00",
            "snapshot_path": None, "description": "{}", "severity": "HIGH",
            "source_video_path": "traffic.mp4", "confidence_score": 0.88, "camera_name": "Uploaded Video Source",
        }]
        response = self.client.get("/accident-history?severity=HIGH")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Event #9", response.data)
        get_accident_history.assert_called_once_with("HIGH")


if __name__ == "__main__":
    unittest.main()
