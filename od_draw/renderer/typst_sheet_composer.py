from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from od_draw.models.master import Project, Sheet


class SheetComposer:
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

        return f"""
#set page(width: 17in, height: 11in, margin: 0in)
#set text(font: "Arial")
#place(dx: 18pt, dy: 18pt, rect(width: 1188pt, height: 756pt, stroke: 1.5pt + black))
{' '.join(viewport_embeds)}
{notes_block}
#place(dx: 18pt, dy: 738pt, grid(
  columns: (120pt, 100pt, 100pt, 220pt, 140pt, 418pt, 90pt),
  rows: (36pt,),
  stroke: 0.75pt + black,
  [Opendoor],
  [DATE: {project.date}],
  [DESIGNER: {sheet.designer}],
  [{sheet.purpose.value} - {sheet.description}],
  [SCALE: {sheet.scale}],
  [STREET ADDRESS: {project.address}],
  [{sheet.sheet_number}],
))
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
