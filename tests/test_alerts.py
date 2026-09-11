import unittest
from unittest.mock import patch

from alerts import build_alert_message, generate_alert
from app import create_app


class AlertTests(unittest.TestCase):
    def test_alert_message_contains_required_event_context(self):
        message = build_alert_message(12, "2026-09-10T12:00:00", "HIGH", "Demo Road", "snapshot.jpg")
        for value in ("Event #12", "2026-09-10T12:00:00", "Demo Road", "HIGH", "snapshot.jpg"):
            self.assertIn(value, message)

    @patch("alerts.db.log_notification_attempt")
    @patch("alerts.db.update_alert_status")
    @patch("alerts.send_optional_email", return_value=(False, "Demo email disabled"))
    @patch("alerts.db.get_active_email_contacts")
    @patch("alerts.db.create_alert")
    def test_dashboard_and_failed_email_attempt_are_logged(self, create_alert, contacts, send_email, update_alert, log_attempt):
        create_alert.side_effect = [100, 101]
        contacts.return_value = [{"emergency_contact_id": 3, "contact_name": "Demo Admin", "email": "demo@example.com"}]
        result = generate_alert(9, "2026-09-10T12:00:00", "HIGH", "Uploaded video", "snap.jpg")
        self.assertEqual(result["alert_id"], 100)
        self.assertEqual(result["email_results"][0]["status"], "failed")
        update_alert.assert_called_once_with(101, "failed")
        self.assertEqual(log_attempt.call_count, 2)


class EmergencyContactsViewTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Admin"
            session["user_role"] = "admin"

    @patch("app.db.get_emergency_contacts", return_value=[])
    def test_admin_can_open_contacts_page(self, _contacts):
        response = self.client.get("/emergency-contacts")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Emergency contacts", response.data)

    @patch("app.db.get_emergency_contacts", return_value=[])
    def test_non_admin_is_redirected(self, _contacts):
        with self.client.session_transaction() as session:
            session["user_role"] = "operator"
        response = self.client.get("/emergency-contacts")
        self.assertEqual(response.status_code, 302)


if __name__ == "__main__":
    unittest.main()
