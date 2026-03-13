import tempfile
import unittest
from pathlib import Path

import fitz

from od_draw.master_pipeline import MasterGenerationPipeline
from od_draw.renderer.pdf_assembler import PDFAssembler
from od_draw.renderer.pdf_linker import PDFLinker
from od_draw.renderer.typst_sheet_composer import SheetComposer
from od_draw.sample_master_project import build_sample_master_project


class PDFPipelineTests(unittest.TestCase):
    def test_pdf_linker_rasterizes_and_extracts_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.pdf"
            document = fitz.open()
            page = document.new_page(width=300, height=200)
            page.draw_line((20, 20), (180, 20))
            document.save(path)
            document.close()

            linker = PDFLinker()
            png_bytes, pixel_width, pixel_height = linker.rasterize_page(str(path), 0)
            vectors = linker.extract_vectors(str(path), 0)

            self.assertTrue(png_bytes.startswith(b"\x89PNG"))
            self.assertGreater(pixel_width, 0)
            self.assertGreater(pixel_height, 0)
            self.assertGreaterEqual(len(vectors), 1)

    def test_sheet_composer_builds_typst_source(self) -> None:
        project = build_sample_master_project()
        sheet = project.sheets[0]
        viewport = sheet.viewports[0]
        source = SheetComposer().build_typst_source(sheet, {viewport.id: "<svg />"}, project)
        self.assertIn(sheet.sheet_number, source)
        self.assertIn(project.address, source)
        self.assertIn(f'{viewport.id}.svg', source)

    def test_pdf_assembler_merges_pdf_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            def make_pdf(text: str) -> bytes:
                document = fitz.open()
                page = document.new_page()
                page.insert_text((72, 72), text)
                data = document.tobytes()
                document.close()
                return data

            output_path = Path(tmpdir) / "merged.pdf"
            merged = PDFAssembler().merge([("A-01", make_pdf("A-01")), ("A-02", make_pdf("A-02"))], output_path)
            merged_doc = fitz.open(merged)
            self.assertEqual(merged_doc.page_count, 2)
            merged_doc.close()

    def test_master_pipeline_writes_svg_and_typst(self) -> None:
        project = build_sample_master_project()
        pipeline = MasterGenerationPipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            sources = pipeline.render_typst_sources(project, tmpdir)
            svg_files = list(Path(tmpdir).glob("*.svg"))
            typ_files = list(Path(tmpdir).glob("*.typ"))
            self.assertEqual(len(svg_files), 1)
            self.assertEqual(len(typ_files), 1)
            self.assertIn("A-02", sources)


if __name__ == "__main__":
    unittest.main()
