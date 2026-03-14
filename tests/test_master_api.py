import tempfile
import unittest
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from od_draw.api.app import create_app
from od_draw.storage.master_project_store import MasterProjectStore
from od_draw.storage.project_store import ProjectStore


class MasterApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        legacy_store = ProjectStore(root / "projects", root / "outputs")
        master_store = MasterProjectStore(
            root / "master-projects",
            root / "master-outputs",
            root / "master-assets",
        )
        self.client = TestClient(create_app(legacy_store, master_store))

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def login(self) -> None:
        response = self.client.post("/auth/login", json={"password": "nina@123@321"})
        self.assertEqual(response.status_code, 200)

    def test_create_and_edit_master_project(self) -> None:
        self.login()
        created = self.client.post(
            "/api/master/projects",
            json={
                "project_name": "Harbor View Kitchen",
                "address": "1 Master Spec Way",
                "project_type": "Kitchen",
                "kcd_color": "OW",
                "kcd_style": "Oslo",
                "drawer_type": "slab",
                "uppers_height": 36,
                "crown_molding": "Flat",
                "status": "A1_Request",
                "use_sample": False,
            },
        )
        self.assertEqual(created.status_code, 200)
        project = created.json()
        self.assertEqual(project["project_name"], "Harbor View Kitchen")
        self.assertIn("model", project)
        room_id = project["model"]["rooms"][0]["id"]
        sheet_id = project["sheets"][0]["id"]

        add_wall = self.client.post(
            f"/api/master/projects/{project['id']}/rooms/{room_id}/walls",
            json={
                "start": {"x": 144, "y": 120},
                "end": {"x": 180, "y": 120},
                "thickness": 4.5,
                "status": "new",
            },
        )
        self.assertEqual(add_wall.status_code, 200)
        self.assertGreaterEqual(len(add_wall.json()["model"]["rooms"][0]["walls"]), 5)

        add_cabinet = self.client.post(
            f"/api/master/projects/{project['id']}/rooms/{room_id}/cabinets",
            json={
                "kcd_code": "B30",
                "position": {"x": 12, "y": 24},
                "wall_id": "",
                "is_upper": False,
            },
        )
        self.assertEqual(add_cabinet.status_code, 200)
        cabinets = add_cabinet.json()["model"]["rooms"][0]["cabinets"]
        self.assertEqual(cabinets[0]["kcd_code"], "OW-B30")

        create_sheet = self.client.post(
            f"/api/master/projects/{project['id']}/sheets",
            json={
                "sheet_number": "D-01",
                "description": "DETAILS",
                "purpose": "FOR CONSTRUCTION",
                "scale": '3/4" = 1\'-0"',
            },
        )
        self.assertEqual(create_sheet.status_code, 200)
        detail_sheet = next(sheet for sheet in create_sheet.json()["sheets"] if sheet["sheet_number"] == "D-01")

        add_viewport = self.client.post(
            f"/api/master/projects/{project['id']}/sheets/{detail_sheet['id']}/viewports",
            json={
                "label": "9 TYPICAL SECTION",
                "crop_rect": {"x": 0, "y": 0, "width": 48, "height": 48},
                "scale": '3/4" = 1\'-0"',
                "position_on_sheet": {"x": 48, "y": 48},
                "size_on_sheet": {"width": 220, "height": 180},
                "render_layers": ["walls", "cabinets", "annotations"],
            },
        )
        self.assertEqual(add_viewport.status_code, 200)
        updated_sheet = next(sheet for sheet in add_viewport.json()["sheets"] if sheet["id"] == detail_sheet["id"])
        self.assertEqual(len(updated_sheet["viewports"]), 1)

        update_viewport = self.client.put(
            f"/api/master/projects/{project['id']}/sheets/{detail_sheet['id']}/viewports/{updated_sheet['viewports'][0]['id']}",
            json={
                "label": "9 TYPICAL SECTION",
                "crop_rect": {"x": 12, "y": 12, "width": 60, "height": 60},
                "scale": '1" = 1\'-0"',
                "position_on_sheet": {"x": 72, "y": 60},
                "size_on_sheet": {"width": 240, "height": 200},
                "render_layers": ["walls", "dimensions"],
            },
        )
        self.assertEqual(update_viewport.status_code, 200)
        reloaded_sheet = next(sheet for sheet in update_viewport.json()["sheets"] if sheet["id"] == detail_sheet["id"])
        self.assertEqual(reloaded_sheet["viewports"][0]["scale"], '1" = 1\'-0"')

    def test_link_calibrate_and_extract_master_pdf(self) -> None:
        self.login()
        project = self.client.post(
            "/api/master/projects",
            json={"address": "2 PDF Underlay Ln", "use_sample": False},
        ).json()

        document = fitz.open()
        page = document.new_page(width=300, height=200)
        page.draw_line((20, 20), (180, 20))
        pdf_bytes = document.tobytes()
        document.close()

        linked = self.client.post(
            f"/api/master/projects/{project['id']}/link-pdf?page=0",
            files={"file": ("underlay.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(linked.status_code, 200)
        payload = linked.json()
        self.assertIn("preview_png_base64", payload)
        pdf_id = payload["linked_pdf"]["id"]

        calibrated = self.client.post(
            f"/api/master/projects/{project['id']}/calibrate-pdf/{pdf_id}",
            json={
                "pdf_point_a": {"x": 20, "y": 20},
                "pdf_point_b": {"x": 180, "y": 20},
                "model_point_a": {"x": 0, "y": 0},
                "model_point_b": {"x": 120, "y": 0},
                "known_distance": 120,
            },
        )
        self.assertEqual(calibrated.status_code, 200)
        self.assertAlmostEqual(calibrated.json()["calibration"]["known_distance"], 120)

        vectors = self.client.post(f"/api/master/projects/{project['id']}/extract-vectors/{pdf_id}")
        self.assertEqual(vectors.status_code, 200)
        self.assertGreaterEqual(len(vectors.json()["paths"]), 1)

    def test_generate_master_outputs_without_typst(self) -> None:
        self.login()
        created = self.client.post(
            "/api/master/projects",
            json={"address": "3 Output Ave", "use_sample": True},
        )
        self.assertEqual(created.status_code, 200)
        project_id = created.json()["id"]

        generated = self.client.post(f"/api/master/projects/{project_id}/generate-construction")
        self.assertEqual(generated.status_code, 200)
        payload = generated.json()
        self.assertIsNone(payload["pdf_url"])
        self.assertTrue(payload["warnings"])
        self.assertTrue(payload["viewport_svg_urls"])
        self.assertTrue(payload["sheet_typst_urls"])

        svg_url = next(iter(payload["viewport_svg_urls"].values()))
        svg_response = self.client.get(svg_url)
        self.assertEqual(svg_response.status_code, 200)
        self.assertIn("<svg", svg_response.text)

        typst_url = next(iter(payload["sheet_typst_urls"].values()))
        typst_response = self.client.get(typst_url)
        self.assertEqual(typst_response.status_code, 200)
        self.assertIn("3 Output Ave", typst_response.text)
        self.assertNotIn("grid(", typst_response.text)

        preview = self.client.get(f"/api/master/projects/{project_id}/preview/A-02")
        self.assertEqual(preview.status_code, 503)


if __name__ == "__main__":
    unittest.main()
