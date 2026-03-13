import unittest

from od_draw.renderer.viewport_renderer import ViewportRenderer
from od_draw.sample_master_project import build_sample_master_project


class ViewportRendererTests(unittest.TestCase):
    def test_renders_master_viewport_svg(self) -> None:
        project = build_sample_master_project()
        viewport = project.sheets[0].viewports[0]
        svg = ViewportRenderer().render(viewport, project.model, project.model.linked_pdfs)
        self.assertIn("<svg", svg)
        self.assertIn("demo-hatch", svg)
        self.assertIn("OW-B30", svg)
        self.assertIn('SCALE: 1/2" = 1\'-0"', svg)


if __name__ == "__main__":
    unittest.main()
