import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app


class AuthenticationFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()

    def test_dashboard_requires_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    @patch("app.db.fetch_all")
    def test_invalid_login_shows_error(self, fetch_all):
        fetch_all.return_value = []
        response = self.client.post("/login", data={"email": "bad@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email address or password.", response.data)

    @patch("app.db.fetch_all")
    def test_login_dashboard_and_logout(self, fetch_all):
        password = "correct-password"
        fetch_all.return_value = [{
            "user_id": 7,
            "full_name": "System Admin",
            "email": "admin@example.com",
            "password_hash": generate_password_hash(password),
            "role": "admin",
            "is_active": True,
        }]
        response = self.client.post("/login", data={"email": "admin@example.com", "password": password})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"System Admin", dashboard.data)

        logout = self.client.post("/logout")
        self.assertEqual(logout.status_code, 302)
        self.assertIn("/login", logout.headers["Location"])
        self.assertEqual(self.client.get("/").status_code, 302)

    @patch("app.db.execute_query")
    @patch("app.db.fetch_all")
    def test_first_admin_setup_hashes_password(self, fetch_all, execute_query):
        fetch_all.return_value = [{"total": 0}]
        response = self.client.post("/setup-admin", data={
            "full_name": "First Admin",
            "email": "first@example.com",
            "password": "strong-password",
            "confirm_password": "strong-password",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        stored_hash = execute_query.call_args.args[1][2]
        self.assertNotEqual(stored_hash, "strong-password")
        self.assertTrue(check_password_hash(stored_hash, "strong-password"))


if __name__ == "__main__":
    unittest.main()
