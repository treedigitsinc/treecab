from __future__ import annotations

import base64
import math

import drawsvg as dw

from od_draw.catalog.master_catalog import lookup
from od_draw.models.master import LinkedPDF, ModelSpace, Point2D, Rect, Viewport, WallStatus
from od_draw.renderer.pdf_linker import PDFLinker


SCALES = {
    '1/2" = 1\'-0"': 0.5 / 12,
    '1/4" = 1\'-0"': 0.25 / 12,
    '3/4" = 1\'-0"': 0.75 / 12,
    '1" = 1\'-0"': 1.0 / 12,
    '1-1/2" = 1\'-0"': 1.5 / 12,
    '3" = 1\'-0"': 3.0 / 12,
}


class ViewportRenderer:
    def __init__(self, pdf_linker: PDFLinker | None = None) -> None:
        self.pdf_linker = pdf_linker or PDFLinker()

    def render(self, viewport: Viewport, model: ModelSpace, linked_pdfs: list[LinkedPDF] | None = None) -> str:
        linked_pdfs = linked_pdfs or []
        scale_factor = viewport.scale_factor * 72
        width_points = viewport.size_on_sheet.width
        height_points = viewport.size_on_sheet.height

        drawing = dw.Drawing(width_points, height_points)
        drawing.append(
            dw.Raw(
                """
<defs>
  <pattern id="demo-hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#C8B078" stroke-width="1.5"/>
  </pattern>
  <clipPath id="viewport-clip">
    <rect x="0" y="0" width="100%" height="100%"/>
  </clipPath>
</defs>
"""
            )
        )

        viewport_group = dw.Group()

        if "underlay" in viewport.render_layers:
            for linked_pdf in linked_pdfs:
                if linked_pdf.visible:
                    viewport_group.append(dw.Raw(self._render_pdf_underlay(linked_pdf, viewport)))

        if "walls" in viewport.render_layers:
            for wall in model.get_walls_in_rect(viewport.crop_rect):
                self._draw_wall(viewport_group, wall, viewport, scale_factor)

        if "openings" in viewport.render_layers:
            for opening in model.get_openings_in_rect(viewport.crop_rect):
                self._draw_opening(viewport_group, model, opening, viewport, scale_factor)

        if "cabinets" in viewport.render_layers:
            for cabinet in model.get_cabinets_in_rect(viewport.crop_rect):
                self._draw_cabinet(viewport_group, cabinet, viewport, scale_factor)

        if "appliances" in viewport.render_layers:
            for appliance in model.get_appliances_in_rect(viewport.crop_rect):
                self._draw_appliance(viewport_group, appliance, viewport, scale_factor)

        if "dimensions" in viewport.render_layers:
            for dimension in model.get_dimensions_in_rect(viewport.crop_rect):
                self._draw_dimension(viewport_group, dimension, viewport, scale_factor)

        if "annotations" in viewport.render_layers:
            for tag in model.get_annotations_in_rect(viewport.crop_rect):
                self._draw_room_tag(viewport_group, tag, viewport, scale_factor)

        drawing.append(viewport_group)
        drawing.append(dw.Text(viewport.label, 10, width_points / 2, height_points - 12, center=True, font_family="Arial"))
        drawing.append(
            dw.Text(
                f"SCALE: {viewport.scale}",
                7,
                width_points / 2,
                height_points - 2,
                center=True,
                font_family="Arial",
            )
        )
        return drawing.as_svg()

    def _paper_point(self, point: Point2D, viewport: Viewport, scale_factor: float) -> Point2D:
        return Point2D(
            (point.x - viewport.crop_rect.x) * scale_factor,
            (point.y - viewport.crop_rect.y) * scale_factor,
        )

    def _render_pdf_underlay(self, linked_pdf: LinkedPDF, viewport: Viewport) -> str:
        if linked_pdf.calibration is None:
            return ""
        png_bytes, pixel_width, pixel_height = self.pdf_linker.rasterize_page(linked_pdf.file_path, linked_pdf.page_number)
        pixels_per_inch = linked_pdf.calibration.pixels_per_inch or 1.0
        scale_factor = viewport.scale_factor * 72
        width_model = pixel_width / pixels_per_inch
        height_model = pixel_height / pixels_per_inch
        width_paper = width_model * scale_factor
        height_paper = height_model * scale_factor
        origin = self._paper_point(linked_pdf.calibration.model_point_a, viewport, scale_factor)
        origin_x = origin.x - (linked_pdf.calibration.pdf_point_a.x / pixels_per_inch) * scale_factor
        origin_y = origin.y - (linked_pdf.calibration.pdf_point_a.y / pixels_per_inch) * scale_factor
        encoded = base64.b64encode(png_bytes).decode("ascii")
        return (
            f'<image x="{origin_x}" y="{origin_y}" width="{width_paper}" height="{height_paper}" '
            f'href="data:image/png;base64,{encoded}" opacity="{linked_pdf.opacity}" clip-path="url(#viewport-clip)"/>'
        )

    def _draw_wall(self, group: dw.Group, wall, viewport: Viewport, scale_factor: float) -> None:
        start = self._paper_point(wall.start, viewport, scale_factor)
        end = self._paper_point(wall.end, viewport, scale_factor)
        thickness = wall.thickness * scale_factor
        angle = math.atan2(end.y - start.y, end.x - start.x)
        dx = math.sin(angle) * thickness / 2
        dy = -math.cos(angle) * thickness / 2
        points = [
            (start.x - dx, start.y - dy),
            (end.x - dx, end.y - dy),
            (end.x + dx, end.y + dy),
            (start.x + dx, start.y + dy),
        ]
        point_string = " ".join(f"{x},{y}" for x, y in points)
        if wall.status == WallStatus.EXISTING:
            fill = "white"
            stroke_width = 1.5
        elif wall.status == WallStatus.TO_REMOVE:
            fill = "url(#demo-hatch)"
            stroke_width = 1.0
        else:
            fill = "#B0B0B0"
            stroke_width = 2.0
        group.append(dw.Raw(f'<polygon points="{point_string}" fill="{fill}" stroke="black" stroke-width="{stroke_width}"/>'))

    def _draw_opening(self, group: dw.Group, model: ModelSpace, opening, viewport: Viewport, scale_factor: float) -> None:
        wall = next((wall for wall in model.get_walls_in_rect(viewport.crop_rect) if wall.id == opening.wall_id), None)
        if wall is None or wall.length == 0:
            return
        ratio = opening.position_along_wall / wall.length
        ratio_end = (opening.position_along_wall + opening.width) / wall.length
        start = Point2D(
            wall.start.x + (wall.end.x - wall.start.x) * ratio,
            wall.start.y + (wall.end.y - wall.start.y) * ratio,
        )
        end = Point2D(
            wall.start.x + (wall.end.x - wall.start.x) * ratio_end,
            wall.start.y + (wall.end.y - wall.start.y) * ratio_end,
        )
        start_paper = self._paper_point(start, viewport, scale_factor)
        end_paper = self._paper_point(end, viewport, scale_factor)
        group.append(dw.Line(start_paper.x, start_paper.y, end_paper.x, end_paper.y, stroke="#5D6C74", stroke_width=2))

    def _draw_cabinet(self, group: dw.Group, cabinet, viewport: Viewport, scale_factor: float) -> None:
        entry = lookup(cabinet.base_code or cabinet.kcd_code)
        if entry is None:
            return
        origin = self._paper_point(cabinet.position, viewport, scale_factor)
        width = entry.width * scale_factor
        depth = entry.depth * scale_factor
        group.append(dw.Rectangle(origin.x, origin.y, width, depth, fill="white", stroke="black", stroke_width=0.6))
        group.append(
            dw.Text(
                cabinet.kcd_code,
                6,
                origin.x + width / 2,
                origin.y + depth / 2,
                center=True,
                font_family="Arial",
            )
        )

    def _draw_appliance(self, group: dw.Group, appliance, viewport: Viewport, scale_factor: float) -> None:
        origin = self._paper_point(appliance.position, viewport, scale_factor)
        width = appliance.width * scale_factor
        depth = appliance.depth * scale_factor
        group.append(dw.Rectangle(origin.x, origin.y, width, depth, fill="none", stroke="#444", stroke_width=0.8))
        group.append(
            dw.Text(
                appliance.label or appliance.type.value,
                6,
                origin.x + width / 2,
                origin.y + depth / 2,
                center=True,
                font_family="Arial",
            )
        )

    def _draw_dimension(self, group: dw.Group, dimension, viewport: Viewport, scale_factor: float) -> None:
        start = self._paper_point(dimension.start, viewport, scale_factor)
        end = self._paper_point(dimension.end, viewport, scale_factor)
        color = "#FF0000" if dimension.is_vif else "black"
        group.append(dw.Line(start.x, start.y, end.x, end.y, stroke=color, stroke_width=0.6))
        label = f".{dimension.vif_label}." if dimension.is_vif and dimension.vif_label else self._format_dimension(dimension.value or hypot(end.x - start.x, end.y - start.y) / scale_factor)
        group.append(
            dw.Text(
                label,
                7,
                (start.x + end.x) / 2,
                (start.y + end.y) / 2 - 4,
                center=True,
                fill=color,
                font_family="Arial",
            )
        )

    def _draw_room_tag(self, group: dw.Group, tag, viewport: Viewport, scale_factor: float) -> None:
        point = self._paper_point(tag.position, viewport, scale_factor)
        group.append(dw.Text(tag.label, 9, point.x, point.y, center=True, font_family="Arial"))
        group.append(dw.Text(f"{tag.room_number:02d}", 7, point.x, point.y + 10, center=True, font_family="Arial"))

    def _format_dimension(self, inches: float) -> str:
        whole = int(inches)
        fraction = inches - whole
        if fraction < 0.125:
            return f'{whole}"'
        if fraction < 0.375:
            return f'{whole} 1/4"'
        if fraction < 0.625:
            return f'{whole} 1/2"'
        if fraction < 0.875:
            return f'{whole} 3/4"'
        return f'{whole + 1}"'
