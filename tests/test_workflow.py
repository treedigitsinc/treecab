import tempfile
import unittest
from pathlib import Path

from od_draw.catalog.kcd_export import export_project_tsv
from od_draw.engine.geometry_engine import prepare_project
from od_draw.renderer.drawing_renderer import DrawingRenderer
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets


class WorkflowTests(unittest.TestCase):
    def test_sample_project_outputs(self) -> None:
        project = prepare_project(build_sample_project())
        build_default_sheets(project)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            pdf_path = DrawingRenderer().render_project(project, output_dir)
            tsv_path = export_project_tsv(project, output_dir / "sample.tsv")
            self.assertTrue(pdf_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 500)
            self.assertTrue(tsv_path.exists())
            contents = tsv_path.read_text(encoding="utf-8")
            self.assertIn("BW-SB36", contents)
            self.assertIn("OW-VSBDL30", contents)


if __name__ == "__main__":
    unittest.main()
