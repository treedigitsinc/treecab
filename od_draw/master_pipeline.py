from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from od_draw.models.master import Project
from od_draw.renderer.pdf_assembler import PDFAssembler
from od_draw.renderer.typst_sheet_composer import SheetComposer
from od_draw.renderer.viewport_renderer import ViewportRenderer


@dataclass(frozen=True)
class MasterGenerationArtifacts:
    viewport_svg_paths: dict[str, Path]
    sheet_typst_paths: dict[str, Path]
    sheet_pdf_paths: dict[str, Path]
    merged_pdf_path: Path | None


class MasterGenerationPipeline:
    def __init__(
        self,
        viewport_renderer: ViewportRenderer | None = None,
        sheet_composer: SheetComposer | None = None,
        pdf_assembler: PDFAssembler | None = None,
    ) -> None:
        self.viewport_renderer = viewport_renderer or ViewportRenderer()
        self.sheet_composer = sheet_composer or SheetComposer()
        self.pdf_assembler = pdf_assembler or PDFAssembler()

    def render_viewport_svgs(self, project: Project, output_dir: str | Path) -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        rendered: dict[str, str] = {}
        for sheet in project.sheets:
            for viewport in sheet.viewports:
                svg = self.viewport_renderer.render(viewport, project.model, project.model.linked_pdfs)
                rendered[viewport.id] = svg
                (output_path / f"{sheet.sheet_number}-{viewport.id}.svg").write_text(svg, encoding="utf-8")
        return rendered

    def render_typst_sources(self, project: Project, output_dir: str | Path) -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        viewport_svgs = self.render_viewport_svgs(project, output_path)
        sources: dict[str, str] = {}
        for sheet in project.sheets:
            source = self.sheet_composer.build_typst_source(sheet, viewport_svgs, project)
            sources[sheet.sheet_number] = source
            (output_path / f"{sheet.sheet_number}.typ").write_text(source, encoding="utf-8")
        return sources

    def generate(self, project: Project, output_dir: str | Path, drawing_type: str) -> MasterGenerationArtifacts:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        viewport_svgs = self.render_viewport_svgs(project, output_path)
        viewport_svg_paths: dict[str, Path] = {}
        for sheet in project.sheets:
            for viewport in sheet.viewports:
                viewport_svg_paths[viewport.id] = output_path / f"{sheet.sheet_number}-{viewport.id}.svg"

        sheet_typst_paths: dict[str, Path] = {}
        for sheet in project.sheets:
            source = self.sheet_composer.build_typst_source(sheet, viewport_svgs, project)
            path = output_path / f"{sheet.sheet_number}.typ"
            path.write_text(source, encoding="utf-8")
            sheet_typst_paths[sheet.sheet_number] = path

        sheet_pdf_paths: dict[str, Path] = {}
        merged_pdf_path: Path | None = None
        if shutil.which("typst") is not None:
            sheet_pdfs: list[tuple[str, bytes]] = []
            for sheet in project.sheets:
                viewport_payload = {
                    viewport.id: viewport_svgs[viewport.id]
                    for viewport in sheet.viewports
                    if viewport.id in viewport_svgs
                }
                pdf_bytes = self.sheet_composer.compose_sheet(sheet, viewport_payload, project)
                pdf_path = output_path / f"{sheet.sheet_number}.pdf"
                pdf_path.write_bytes(pdf_bytes)
                sheet_pdf_paths[sheet.sheet_number] = pdf_path
                sheet_pdfs.append((sheet.sheet_number, pdf_bytes))
            merged_pdf_path = self.pdf_assembler.merge(
                sheet_pdfs,
                output_path / f"{project.id}-{drawing_type}.pdf",
            )

        return MasterGenerationArtifacts(
            viewport_svg_paths=viewport_svg_paths,
            sheet_typst_paths=sheet_typst_paths,
            sheet_pdf_paths=sheet_pdf_paths,
            merged_pdf_path=merged_pdf_path,
        )
