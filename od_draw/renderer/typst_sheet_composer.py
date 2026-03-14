from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from od_draw.models.master import Project, Sheet


class SheetComposer:
    TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

    @staticmethod
    def _typst_text(value: str) -> str:
        return (
            " ".join((value or "").split())
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("[", "\\[")
            .replace("]", "\\]")
        )

    def _template_path(self, sheet: Sheet, project: Project) -> str:
        try:
            index = next(i for i, candidate in enumerate(project.sheets) if candidate.id == sheet.id)
        except StopIteration:
            index = 0
        candidate = self.TEMPLATE_DIR / f"opendoor-page-{index}.jpg"
        if not candidate.exists():
            candidate = self.TEMPLATE_DIR / "opendoor-page-0.jpg"
        return candidate.as_posix()

    def build_typst_source(self, sheet: Sheet, viewport_svgs: dict[str, str], project: Project) -> str:
        viewport_embeds: list[str] = []
        for viewport in sheet.viewports:
            if viewport.id not in viewport_svgs:
                continue
            viewport_embeds.append(
                f'#place(dx: {viewport.position_on_sheet.x}pt, dy: {viewport.position_on_sheet.y}pt, '
                f'image("{viewport.id}.svg", width: {viewport.size_on_sheet.width}pt, height: {viewport.size_on_sheet.height}pt))'
            )

        notes_block = (
            '#place(dx: 970pt, dy: 18pt, rect(width: 234pt, height: 720pt, stroke: 0.5pt + black)['
            '#set text(size: 6.5pt) FIN. CABINET SPECIFICATION NOTES ])'
            if sheet.has_notes_sidebar
            else ""
        )
        project_name = self._typst_text(project.project_name or project.address or "New Project")
        sheet_title = self._typst_text(f"{sheet.purpose.value} - {sheet.description}")
        address = self._typst_text(project.address)
        date_text = self._typst_text(sheet.date or project.date)
        designer_text = self._typst_text(sheet.designer)
        scale_text = self._typst_text(sheet.scale)
        sheet_number = self._typst_text(sheet.sheet_number)
        template_path = self._template_path(sheet, project)

        return f"""
#set page(width: 17in, height: 11in, margin: 0in)
#set text(font: "Arial")
#place(dx: 0pt, dy: 0pt, image("{template_path}", width: 1224pt, height: 792pt))
{' '.join(viewport_embeds)}
{notes_block}
#place(dx: 24pt, dy: 738pt, box(width: 88pt)[#set text(size: 8.5pt, weight: 700)[{project_name}]])
#place(dx: 124pt, dy: 741pt, box(width: 64pt)[#set text(size: 6.4pt, weight: 600)[{date_text}]])
#place(dx: 237pt, dy: 741pt, box(width: 132pt)[#set text(size: 6.4pt, weight: 600)[{designer_text}]])
#place(dx: 408pt, dy: 738pt, box(width: 254pt)[#set text(size: 7.1pt, weight: 700)#align(center)[{sheet_title}]])
#place(dx: 675pt, dy: 738pt, box(width: 94pt)[#set text(size: 7.1pt, weight: 700)#align(center)[{scale_text}]])
#place(dx: 846pt, dy: 741pt, box(width: 262pt)[#set text(size: 6.4pt, weight: 600)[{address}]])
#place(dx: 1170pt, dy: 733pt, box(width: 42pt)[#set text(size: 14pt, weight: 800)#align(center)[{sheet_number}]])
"""

    def compose_sheet(self, sheet: Sheet, viewport_svgs: dict[str, str], project: Project) -> bytes:
        if shutil.which("typst") is None:
            raise RuntimeError("Typst is not installed in PATH")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            for viewport_id, svg in viewport_svgs.items():
                (tmp_path / f"{viewport_id}.svg").write_text(svg, encoding="utf-8")
            source_path = tmp_path / "sheet.typ"
            output_path = tmp_path / "sheet.pdf"
            source_path.write_text(self.build_typst_source(sheet, viewport_svgs, project), encoding="utf-8")
            result = subprocess.run(
                ["typst", "compile", str(source_path), str(output_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Typst compile failed: {result.stderr}")
            return output_path.read_bytes()
