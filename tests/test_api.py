import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from od_draw.api.app import create_app
from od_draw.storage.project_store import ProjectStore


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        store = ProjectStore(root / "projects", root / "outputs")
        self.client = TestClient(create_app(store))

    def login(self) -> None:
        response = self.client.post("/auth/login", json={"password": "nina@123@321"})
        self.assertEqual(response.status_code, 200)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_site_requires_password_for_ui_and_api(self) -> None:
        index = self.client.get("/")
        self.assertEqual(index.status_code, 401)
        self.assertIn("treecab", index.text)

        api_response = self.client.get("/api/status")
        self.assertEqual(api_response.status_code, 401)
        self.assertEqual(api_response.json()["detail"], "Unauthorized")

    def test_login_and_logout_control_access(self) -> None:
        denied = self.client.post("/auth/login", json={"password": "wrong"})
        self.assertEqual(denied.status_code, 401)

        self.login()
        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)

        logout = self.client.post("/auth/logout", follow_redirects=False)
        self.assertEqual(logout.status_code, 303)

        blocked_again = self.client.get("/api/status")
        self.assertEqual(blocked_again.status_code, 401)

    def test_authorized_ui_serves_frontend_entry(self) -> None:
        self.login()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="root"', response.text)
        self.assertIn("/frontend/", response.text)

    def test_sample_project_round_trip_and_preview(self) -> None:
        self.login()
        payload = {
            "address": "773 Harbor View Rd, Charleston, SC 29412",
            "kcd_color": "BW",
            "kcd_style": "Brooklyn White",
            "drawer_type": "5-piece",
            "uppers_height": 36,
            "crown_molding": "Flat",
            "designer": "LOCAL MVP",
            "use_sample": True,
        }
        created = self.client.post("/api/projects", json=payload)
        self.assertEqual(created.status_code, 200)
        project_id = created.json()["id"]

        fetched = self.client.get(f"/api/projects/{project_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertGreaterEqual(len(fetched.json()["rooms"]), 1)

        generation = self.client.post(f"/api/projects/{project_id}/generate-cd")
        self.assertEqual(generation.status_code, 200)
        sheet_urls = generation.json()["sheet_urls"]
        self.assertIn("A-02", sheet_urls)

        preview = self.client.get(sheet_urls["A-02"])
        self.assertEqual(preview.status_code, 200)
        self.assertIn("<svg", preview.text)

    def test_blank_project_room_update(self) -> None:
        self.login()
        payload = {
            "address": "1 Test Ave",
            "kcd_color": "OW",
            "kcd_style": "Oslo White",
            "drawer_type": "slab",
            "uppers_height": 30,
            "crown_molding": "NoCrown",
            "designer": "TEST",
            "use_sample": False,
        }
        created = self.client.post("/api/projects", json=payload).json()
        room = created["rooms"][0]
        room["label"] = "Edited Kitchen"
        room["walls"][0]["end"]["x"] = 156
        updated = self.client.put(f"/api/projects/{created['id']}/rooms/{room['id']}", json=room)
        self.assertEqual(updated.status_code, 200)
        updated_room = updated.json()["rooms"][0]
        self.assertEqual(updated_room["label"], "Edited Kitchen")
        self.assertEqual(updated_room["walls"][0]["end"]["x"], 156)


if __name__ == "__main__":
    unittest.main()
