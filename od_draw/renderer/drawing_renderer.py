from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from od_draw.models.enums import SheetMode, WallStatus
from od_draw.models.geometry import Point2D, Rect
from od_draw.models.project import Project, Room, Sheet
from od_draw.renderer.pdf_renderer import PdfDocument, PdfPage
from od_draw.renderer.styles import (
    BOTTOM_STRIP_HEIGHT,
    COLOR_BG,
    COLOR_BLACK,
    COLOR_BLUE,
    COLOR_DEMO,
    COLOR_LIGHT,
    COLOR_MID,
    COLOR_MUTED,
    COLOR_NEW,
    COLOR_RED,
    COLOR_TEXT,
    CONTENT_MARGIN,
    DETAIL_GAP,
    PLAN_CONTENT_BOTTOM,
    PLAN_CONTENT_TOP,
    SHEET_HEIGHT,
    SHEET_MARGIN,
    SHEET_WIDTH,
    SIDEBAR_WIDTH,
    VIEW_GAP,
)


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _fmt_inches(value: float) -> str:
    rounded = round(value * 2) / 2
    whole = int(rounded)
    fraction = Fraction(rounded - whole).limit_denominator(2)
    if fraction.numerator == 0:
        return f'{whole}"'
    if whole == 0:
        return f'{fraction.numerator}/{fraction.denominator}"'
    return f'{whole} {fraction.numerator}/{fraction.denominator}"'


def _estimate_text_width(value: str, size: float) -> float:
    return len(value) * size * 0.46


def _wrap_text(value: str, max_chars: int) -> list[str]:
    words = value.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    offset = 2
    while offset < len(data):
        while offset < len(data) and data[offset] != 0xFF:
            offset += 1
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 1 >= len(data):
            break
        length = int.from_bytes(data[offset : offset + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height = int.from_bytes(data[offset + 3 : offset + 5], "big")
            width = int.from_bytes(data[offset + 5 : offset + 7], "big")
            return width, height
        offset += length
    raise ValueError("Unable to determine JPEG dimensions")


TEMPLATE_PAGE_INDEX = {
    "CP-00": 0,
    "A-01": 1,
    "A-02": 2,
    "A-03": 3,
    "A-04": 4,
    "D-01": 5,
}


class DrawingRenderer:
    def __init__(self) -> None:
        self.document = PdfDocument()
        self.dark = _hex_to_rgb(COLOR_BLACK)
        self.text = _hex_to_rgb(COLOR_TEXT)
        self.muted = _hex_to_rgb(COLOR_MUTED)
        self.blue = _hex_to_rgb(COLOR_BLUE)
        self.demo = _hex_to_rgb(COLOR_DEMO)
        self.new = _hex_to_rgb(COLOR_NEW)
        self.red = _hex_to_rgb(COLOR_RED)
        self.light = _hex_to_rgb(COLOR_LIGHT)
        self.mid = _hex_to_rgb(COLOR_MID)
        self.bg = _hex_to_rgb(COLOR_BG)
        self.templates = self._load_templates()

    def _load_templates(self) -> dict[str, tuple[bytes, int, int]]:
        template_dir = Path(__file__).resolve().parents[1] / "templates"
        templates: dict[str, tuple[bytes, int, int]] = {}
        for sheet_number, page_index in TEMPLATE_PAGE_INDEX.items():
            path = template_dir / f"opendoor-page-{page_index}.jpg"
            if not path.exists():
                continue
            data = path.read_bytes()
            width, height = _jpeg_dimensions(data)
            templates[sheet_number] = (data, width, height)
        return templates

    def render_project(self, project: Project, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        for sheet in project.sheets:
            page = self.document.add_page(SHEET_WIDTH, SHEET_HEIGHT)
            self._render_sheet(page, project, sheet)
            (output_dir / f"{sheet.sheet_number}.svg").write_text(
                self._sheet_to_svg(project, sheet), encoding="utf-8"
            )
        pdf_path = output_dir / f"{project.id}.pdf"
        pdf_path.write_bytes(self.document.to_bytes())
        return pdf_path

    def _render_sheet(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        if self._render_template_sheet(page, project, sheet):
            return
        self._draw_page_frame(page, project, sheet)
        if sheet.mode == SheetMode.COVER:
            self._render_cover_sheet(page, project, sheet)
            return
        if sheet.mode == SheetMode.DETAILS:
            self._render_detail_sheet(page, project, sheet)
            return
        self._render_plan_sheet(page, project, sheet)

    def _render_template_sheet(self, page: PdfPage, project: Project, sheet: Sheet) -> bool:
        template = self.templates.get(sheet.sheet_number)
        if template is None:
            return False
        data, pixel_width, pixel_height = template
        page.jpeg(0, 0, SHEET_WIDTH, SHEET_HEIGHT, data, pixel_width, pixel_height)
        self._clear_bottom_strip_fields(page)
        self._draw_bottom_strip_text(page, project, sheet, include_logo=False)
        if sheet.mode in {SheetMode.COVER, SheetMode.DETAILS}:
            return True
        for rect in self._template_blank_rects(sheet):
            self._clear_rect(page, rect)
        self._render_plan_sheet(page, project, sheet)
        return True

    def _clear_rect(self, page: PdfPage, rect: Rect) -> None:
        page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.1, stroke_rgb=self.bg, fill_rgb=self.bg)

    def _clear_bottom_strip_fields(self, page: PdfPage) -> None:
        x = SHEET_MARGIN + 82
        y = SHEET_MARGIN + 1.5
        height = max(BOTTOM_STRIP_HEIGHT - 3, 1)
        for width in [68, 74, 148, 242, 84, 430, 60]:
            self._clear_rect(page, Rect(x + 1.5, y, width - 3, height))
            x += width

    def _template_blank_rects(self, sheet: Sheet) -> list[Rect]:
        if sheet.sheet_number == "A-01":
            return [Rect(24, 74, 998, 610)]
        if sheet.sheet_number == "A-02":
            return [Rect(40, 82, 900, 620), Rect(410, 648, 260, 30)]
        if sheet.sheet_number in {"A-03", "A-04"}:
            return [
                Rect(30, 90, 470, 590),
                Rect(490, 90, 470, 590),
                Rect(18, 430, 932, 250),
                Rect(820, 160, 132, 340),
            ]
        return []

    def _draw_page_frame(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        page.rect(
            SHEET_MARGIN,
            SHEET_MARGIN,
            SHEET_WIDTH - (SHEET_MARGIN * 2),
            SHEET_HEIGHT - (SHEET_MARGIN * 2),
            stroke_rgb=self.dark,
            stroke_width=0.9,
        )
        page.line(
            SHEET_MARGIN,
            SHEET_MARGIN + BOTTOM_STRIP_HEIGHT,
            SHEET_WIDTH - SHEET_MARGIN,
            SHEET_MARGIN + BOTTOM_STRIP_HEIGHT,
            width=0.8,
            stroke_rgb=self.dark,
        )
        page.text(
            SHEET_MARGIN + 6,
            SHEET_HEIGHT - SHEET_MARGIN - 7,
            f"OD SELECT - {sheet.title.upper()}",
            6.2,
            fill_rgb=self.muted,
        )
        self._draw_bottom_strip(page, project, sheet)

    def _draw_bottom_strip(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        y = SHEET_MARGIN
        height = BOTTOM_STRIP_HEIGHT
        columns = [82, 68, 74, 148, 242, 84, 430]
        x = SHEET_MARGIN
        for width in columns:
            page.line(x + width, y, x + width, y + height, width=0.5, stroke_rgb=self.dark)
            x += width
        self._draw_bottom_strip_text(page, project, sheet)

    def _draw_bottom_strip_text(self, page: PdfPage, project: Project, sheet: Sheet, include_logo: bool = True) -> None:
        y = SHEET_MARGIN
        columns = [82, 68, 74, 148, 242, 84, 430]
        labels = [
            ("Opendoor", 9.0, self.blue),
            (project.created_at.strftime("%m.%d.%y"), 5.2, self.text),
            (project.designer, 5.2, self.text),
            (sheet.purpose, 5.2, self.text),
            (sheet.title.upper(), 5.2, self.text),
            (sheet.scale_label, 5.2, self.text),
            (project.address, 5.2, self.text),
        ]
        x = SHEET_MARGIN
        for index, (width, (value, size, color)) in enumerate(zip(columns, labels)):
            if index == 0 and not include_logo:
                x += width
                continue
            page.text(x + 4, y + 5, value, size, fill_rgb=color)
            x += width
        sheet_box_width = (SHEET_WIDTH - SHEET_MARGIN) - x
        page.text(
            x + max((sheet_box_width - _estimate_text_width(sheet.sheet_number, 8.5)) / 2, 6),
            y + 4,
            sheet.sheet_number,
            8.5,
            fill_rgb=self.text,
        )

    def _content_rect(self, include_sidebar: bool) -> Rect:
        width = SHEET_WIDTH - (SHEET_MARGIN * 2) - (CONTENT_MARGIN * 2)
        if include_sidebar:
            width -= SIDEBAR_WIDTH + VIEW_GAP
        return Rect(
            x=SHEET_MARGIN + CONTENT_MARGIN,
            y=PLAN_CONTENT_BOTTOM,
            width=width,
            height=PLAN_CONTENT_TOP - PLAN_CONTENT_BOTTOM,
        )

    def _sidebar_rect(self) -> Rect:
        return Rect(
            x=SHEET_WIDTH - SHEET_MARGIN - CONTENT_MARGIN - SIDEBAR_WIDTH,
            y=PLAN_CONTENT_BOTTOM,
            width=SIDEBAR_WIDTH,
            height=PLAN_CONTENT_TOP - PLAN_CONTENT_BOTTOM,
        )

    def _draw_box_title(self, page: PdfPage, rect: Rect, title: str) -> None:
        page.text(rect.x + 6, rect.y + rect.height - 12, title, 6.2, fill_rgb=self.text)
        page.line(
            rect.x,
            rect.y + rect.height - 18,
            rect.x + rect.width,
            rect.y + rect.height - 18,
            width=0.5,
            stroke_rgb=self.dark,
        )

    def _draw_text_block(
        self,
        page: PdfPage,
        x: float,
        y: float,
        lines: list[str],
        size: float,
        color: tuple[float, float, float] | None = None,
        leading: float = 9.0,
    ) -> None:
        cursor = y
        fill = self.text if color is None else color
        for line in lines:
            page.text(x, cursor, line, size, fill_rgb=fill)
            cursor -= leading

    def _render_cover_sheet(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        content = self._content_rect(include_sidebar=False)
        gutter = 10.0
        panel_width = (content.width - gutter) / 2
        left = Rect(content.x, content.y, panel_width, content.height)
        right = Rect(content.x + panel_width + gutter, content.y, panel_width, content.height)

        page.rect(left.x, left.y, left.width, left.height, stroke_width=0.8, stroke_rgb=self.dark)
        page.rect(right.x, right.y, right.width, right.height, stroke_width=0.8, stroke_rgb=self.dark)

        logo = "Opendoor"
        logo_x = left.x + (left.width - _estimate_text_width(logo, 30)) / 2
        page.text(logo_x, left.y + left.height - 44, logo, 30, fill_rgb=self.blue)
        page.text(left.x + 110, left.y + left.height - 66, "OD SELECT - CABINET GUIDE", 8.0, fill_rgb=self.text)
        page.text(left.x + 96, left.y + left.height - 84, "All cabinets ordered & paid by Opendoor (OD)", 6.4, fill_rgb=self.text)

        paragraphs = [
            "PRIOR ORDER: As soon as project is awarded, measurements, photos and wall conditions are designated on the measure guide.",
            "AT ORDER: OD will order cabinets and expected delivery date will be provided to the GC. Filler install tables and approved plan sheets remain accessible by QR code as well.",
            "DELIVERY: GC receives all cabinets. The GC or installer is responsible for the site condition, trim pieces and punch review before install.",
            "IF ADDITIONAL PARTS ARE REQUIRED: Contact OD and reference the SKU, quantity, finish and door style.",
        ]
        cursor = left.y + left.height - 118
        for paragraph in paragraphs:
            lines = _wrap_text(paragraph, 52)
            self._draw_text_block(page, left.x + 12, cursor, lines, 6.0, leading=8.0)
            cursor -= (len(lines) * 8.0) + 12
        page.text(left.x + 134, left.y + 18, "Thank You!", 7.6, fill_rgb=self.blue)

        header = "OD SELECT - MEASUREMENT GUIDE"
        header_x = right.x + (right.width - _estimate_text_width(header, 9.0)) / 2
        page.text(header_x, right.y + right.height - 18, header, 9.0, fill_rgb=self.text)
        info = Rect(right.x + 36, right.y + right.height - 82, right.width - 72, 46)
        page.rect(info.x, info.y, info.width, info.height, stroke_width=0.6, stroke_rgb=self.mid, fill_rgb=self.light)
        info_lines = [
            "We all know that clear communication is key!",
            "This guide outlines a measure language for OD Select",
            "to accurately provide information to create",
            "detailed cabinetry plans for projects.",
        ]
        self._draw_text_block(page, info.x + 18, info.y + 31, info_lines, 6.2, leading=7.0)

        request_lines = [
            "Measure Request:",
            "Measure in inches only. Never feet & inches.",
            "Capture room width and full wall lengths.",
            "Tape measure is required for room verification.",
            "Laser measure can be used as a secondary check.",
            "If you see a soffit, window or vent, note it on the sketch.",
            "If wall bowing exists, measure from each side and give us the smallest run.",
        ]
        self._draw_text_block(page, right.x + 12, right.y + right.height - 108, request_lines, 6.0, leading=8.0)
        self._draw_measurement_example(page, Rect(right.x + 62, right.y + 36, right.width - 96, 110))

    def _draw_measurement_example(self, page: PdfPage, rect: Rect) -> None:
        page.text(rect.x, rect.y + rect.height + 8, "Measurement Example", 6.2, fill_rgb=self.text)
        base_y = rect.y + 16
        left_box = Rect(rect.x + 6, base_y, 52, 58)
        center_box = Rect(left_box.x + left_box.width, base_y, 118, 58)
        window_box = Rect(center_box.x + 32, base_y + 12, 62, 34)

        for box in [left_box, center_box]:
            page.rect(box.x, box.y, box.width, box.height, stroke_width=0.7, stroke_rgb=self.mid)
        page.rect(window_box.x, window_box.y, window_box.width, window_box.height, stroke_width=0.7, stroke_rgb=self.mid)
        page.text(left_box.x + 10, left_box.y + 27, '24"', 6.0, fill_rgb=self.text)
        page.text(center_box.x + 48, center_box.y + 27, '30 1/2"', 6.0, fill_rgb=self.text)
        page.text(window_box.x + 7, window_box.y + 16, "WINDOW OPENING", 4.6, fill_rgb=self.muted)

        page.line(left_box.x + 12, left_box.y + 6, left_box.x + left_box.width - 12, left_box.y + left_box.height - 6, width=0.5, stroke_rgb=self.mid)
        page.line(left_box.x + left_box.width - 12, left_box.y + 6, left_box.x + 12, left_box.y + left_box.height - 6, width=0.5, stroke_rgb=self.mid)

        dim_y = base_y + 76
        self._draw_dimension(page, left_box.x, dim_y, left_box.x + left_box.width, dim_y, '24"', vertical=False)
        self._draw_dimension(page, center_box.x, dim_y, center_box.x + center_box.width, dim_y, '30 1/2"', vertical=False)
        self._draw_dimension(page, window_box.x, dim_y - 22, window_box.x + window_box.width, dim_y - 22, '33"', vertical=False)
        self._draw_dimension(page, center_box.x + center_box.width + 42, base_y, center_box.x + center_box.width + 42, base_y + 58, '36"', vertical=True)

    def _render_plan_sheet(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        rooms = [room for room in project.rooms if room.id in sheet.room_ids]
        template_viewports = self._template_viewports(sheet)
        if template_viewports:
            if len(rooms) == 1:
                self._render_room_view(page, rooms[0], sheet.mode, template_viewports[0])
                return
            for room, rect in zip(rooms[: len(template_viewports)], template_viewports):
                self._render_room_view(page, room, sheet.mode, rect)
            return

        show_sidebar = sheet.mode in {SheetMode.LAYOUT, SheetMode.BATH}
        content = self._content_rect(include_sidebar=show_sidebar)
        if show_sidebar:
            self._draw_plan_sidebar(page, project, sheet, self._sidebar_rect())

        if len(rooms) == 1:
            self._render_room_view(page, rooms[0], sheet.mode, content)
            if sheet.mode == SheetMode.DEMO:
                self._draw_demo_legend(page, Rect(content.x + content.width - 108, content.y + 10, 92, 40))
            return

        split_width = (content.width - VIEW_GAP) / 2
        left = Rect(content.x, content.y + 36, split_width, content.height - 52)
        right = Rect(content.x + split_width + VIEW_GAP, content.y + 36, split_width, content.height - 52)
        divider_x = content.x + split_width + (VIEW_GAP / 2)
        page.line(divider_x, content.y, divider_x, content.y + content.height, width=0.5, stroke_rgb=self.mid)

        for index, (room, rect) in enumerate(zip(rooms[:2], [left, right]), start=1):
            self._render_room_view(page, room, sheet.mode, rect)
            page.text(rect.x + 6, content.y + 12, f"{index:02d}  {room.label.upper()}  {sheet.title.upper()}", 6.0, fill_rgb=self.text)

        if sheet.mode == SheetMode.DEMO:
            self._draw_demo_legend(page, Rect(content.x + content.width - 108, content.y + 10, 92, 40))

    def _template_viewports(self, sheet: Sheet) -> list[Rect]:
        if sheet.sheet_number == "A-01":
            return [Rect(84, 108, 858, 536)]
        if sheet.sheet_number == "A-02":
            return [Rect(88, 104, 820, 548)]
        if sheet.sheet_number in {"A-03", "A-04"}:
            return [Rect(74, 130, 396, 278), Rect(524, 130, 396, 278)]
        return []

    def _draw_plan_sidebar(self, page: PdfPage, project: Project, sheet: Sheet, rect: Rect) -> None:
        page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.8, stroke_rgb=self.dark)
        sections = [
            ("FIN. CABINET SPECIFICATION NOTES", [
                f"STYLE: {project.kcd_style.upper()}",
                f"COLOR: {project.kcd_color}",
                f"DRAWER: {project.drawer_type.upper()}",
                f"UPPERS: {project.uppers_height}\" HIGH",
                f"CROWN: {project.crown_molding.upper()}",
            ]),
            ("NOTES", sheet.notes + ["VERIFY ALL DIMENSIONS IN FIELD."]),
            ("ABBREVIATIONS", ["REF = REFRIGERATOR", "DW = DISHWASHER", "RNG = RANGE", "UPP = UPPER CABINET"]),
            ("LEGEND", ["EXISTING WALL", "NEW WALL", "DEMO CABINET"]),
        ]

        top = rect.y + rect.height - 14
        for title, lines in sections:
            page.line(rect.x, top, rect.x + rect.width, top, width=0.5, stroke_rgb=self.dark)
            page.text(rect.x + 6, top - 10, title, 5.8, fill_rgb=self.text)
            cursor = top - 22
            if title == "LEGEND":
                self._draw_sidebar_legend(page, rect.x + 8, cursor + 2)
                cursor -= 40
            else:
                for raw_line in lines:
                    wrapped = _wrap_text(raw_line, 28)
                    for line in wrapped:
                        page.text(rect.x + 8, cursor, line, 5.2, fill_rgb=self.text)
                        cursor -= 7
                cursor -= 4
            top = cursor
            if top <= rect.y + 32:
                break
        page.text(rect.x + 6, rect.y + 8, "CENTRAL TRIM: YES", 5.0, fill_rgb=self.text)

    def _draw_sidebar_legend(self, page: PdfPage, x: float, y: float) -> None:
        swatch_width = 20
        entries = [
            ("EXISTING", self.dark, None),
            ("NEW", self.new, None),
            ("DEMO", self.demo, self.demo),
        ]
        cursor = y
        for label, stroke, fill in entries:
            page.rect(x, cursor, swatch_width, 8, stroke_width=0.7, stroke_rgb=stroke, fill_rgb=fill)
            page.text(x + swatch_width + 6, cursor + 2, label, 5.2, fill_rgb=self.text)
            cursor -= 12

    def _render_room_view(self, page: PdfPage, room: Room, mode: SheetMode, viewport: Rect) -> None:
        if mode == SheetMode.DEMO:
            hatch = Rect(viewport.x + 10, viewport.y + 8, viewport.width * 0.42, viewport.height * 0.28)
            self._draw_hatched_rect(page, hatch, self.mid)

        for wall in room.walls:
            start = self._map_point(room, wall.start, viewport)
            end = self._map_point(room, wall.end, viewport)
            width = 1.8 if wall.status == WallStatus.NEW else 1.2
            color = self.dark
            if wall.status == WallStatus.TO_REMOVE:
                color = self.demo
                width = 2.0
            elif wall.status == WallStatus.NEW:
                color = self.new
            page.line(start.x, start.y, end.x, end.y, width=width, stroke_rgb=color)

        for opening in room.openings:
            wall = next(candidate for candidate in room.walls if candidate.id == opening.wall_id)
            start = self._map_point(room, wall.point_at(opening.position_along_wall), viewport)
            end = self._map_point(room, wall.point_at(opening.position_along_wall + opening.width), viewport)
            page.line(start.x, start.y, end.x, end.y, width=4.0, stroke_rgb=self.bg)
            page.line(start.x, start.y, end.x, end.y, width=0.8, stroke_rgb=self.muted)
            label_x = min(start.x, end.x) + 2
            label_y = max(start.y, end.y) + 6
            page.text(label_x, label_y, opening.kind.value.upper(), 4.8, fill_rgb=self.muted)

        if mode in {SheetMode.LAYOUT, SheetMode.BATH, SheetMode.DEMO}:
            for cabinet in room.cabinets:
                self._render_cabinet(page, room, cabinet, viewport, mode)
            for appliance in room.appliances:
                self._render_appliance(page, room, appliance, viewport)

        for dimension in room.verified_dimensions:
            self._render_verified_dimension(page, room, dimension, viewport)

        label_anchor = self._map_point(
            room,
            Point2D(
                sum(wall.start.x for wall in room.walls) / len(room.walls),
                sum(wall.start.y for wall in room.walls) / len(room.walls),
            ),
            viewport,
        )
        page.text(label_anchor.x - 22, label_anchor.y + 8, room.label.upper(), 7.6, fill_rgb=self.text)
        page.text(label_anchor.x - 6, label_anchor.y - 2, f"{room.room_number:02d}", 6.4, fill_rgb=self.muted)

    def _room_bounds(self, room: Room) -> tuple[float, float, float, float]:
        xs = [wall.start.x for wall in room.walls] + [wall.end.x for wall in room.walls]
        ys = [wall.start.y for wall in room.walls] + [wall.end.y for wall in room.walls]
        return min(xs), min(ys), max(xs), max(ys)

    def _room_transform(self, room: Room, viewport: Rect) -> tuple[float, float, float, float, float]:
        min_x, min_y, max_x, max_y = self._room_bounds(room)
        room_width = max(max_x - min_x, 1.0)
        room_height = max(max_y - min_y, 1.0)
        padding_x = 28.0
        padding_y = 28.0
        scale = min((viewport.width - (padding_x * 2)) / room_width, (viewport.height - (padding_y * 2)) / room_height)
        origin_x = viewport.x + (viewport.width - (room_width * scale)) / 2
        origin_y = viewport.y + (viewport.height - (room_height * scale)) / 2
        return min_x, min_y, scale, origin_x, origin_y

    def _map_point(self, room: Room, point: Point2D, viewport: Rect) -> Point2D:
        min_x, min_y, scale, origin_x, origin_y = self._room_transform(room, viewport)
        return Point2D(
            origin_x + ((point.x - min_x) * scale),
            origin_y + ((point.y - min_y) * scale),
        )

    def _render_cabinet(self, page: PdfPage, room: Room, cabinet, viewport: Rect, mode: SheetMode) -> None:
        wall = next(candidate for candidate in room.walls if candidate.id == cabinet.wall_id)
        start = self._map_point(room, wall.point_at(cabinet.offset_from_wall_start), viewport)
        end = self._map_point(room, wall.point_at(cabinet.offset_from_wall_start + cabinet.catalog_entry.width), viewport)
        bounds = self._room_bounds(room)
        _, _, scale, _, _ = self._room_transform(room, viewport)
        depth = max(12.0, cabinet.catalog_entry.depth * scale)
        is_horizontal = abs(wall.start.y - wall.end.y) < 0.1
        is_top = wall.start.y == bounds[3] and wall.end.y == bounds[3]
        is_right = wall.start.x == bounds[2] and wall.end.x == bounds[2]

        fill = None
        stroke = self.dark
        dash = None
        label = cabinet.kcd_code
        if cabinet.is_upper:
            stroke = self.muted
            dash = (5.0, 4.0)
            if mode == SheetMode.DEMO:
                label = "UPPER"
        elif mode == SheetMode.DEMO:
            fill = self.demo

        if is_horizontal:
            y = start.y - depth if is_top else start.y
            x = min(start.x, end.x)
            width = abs(end.x - start.x)
            page.rect(x, y, width, depth, stroke_width=0.9, stroke_rgb=stroke, fill_rgb=fill, dash=dash)
            if width > 18:
                page.text(x + (width / 2) - (_estimate_text_width(label, 5.2) / 2), y + (depth / 2) - 2, label, 5.2, fill_rgb=self.text)
            return

        x = start.x - depth if is_right else start.x
        y = min(start.y, end.y)
        height = abs(end.y - start.y)
        page.rect(x, y, depth, height, stroke_width=0.9, stroke_rgb=stroke, fill_rgb=fill, dash=dash)
        if height > 18:
            page.text(x + 3, y + (height / 2), label, 5.2, fill_rgb=self.text)

    def _render_appliance(self, page: PdfPage, room: Room, appliance, viewport: Rect) -> None:
        mapped = self._map_point(room, appliance.position, viewport)
        size = 24 if appliance.type.value == "REF" else 18
        page.rect(mapped.x - (size / 2), mapped.y - (size / 2), size, size, stroke_width=0.8, stroke_rgb=self.mid)
        page.text(mapped.x - (_estimate_text_width(appliance.label, 5.4) / 2), mapped.y - 2, appliance.label, 5.4, fill_rgb=self.text)

    def _render_verified_dimension(self, page: PdfPage, room: Room, dimension, viewport: Rect) -> None:
        start = self._map_point(room, dimension.start, viewport)
        end = self._map_point(room, dimension.end, viewport)
        dx = end.x - start.x
        dy = end.y - start.y
        if abs(dx) >= abs(dy):
            y = min(start.y, end.y) - 14
            self._draw_dimension(page, start.x, y, end.x, y, _fmt_inches(dimension.value), vertical=False)
            return
        x = min(start.x, end.x) - 14
        self._draw_dimension(page, x, start.y, x, end.y, _fmt_inches(dimension.value), vertical=True)

    def _draw_dimension(
        self,
        page: PdfPage,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        label: str,
        vertical: bool,
    ) -> None:
        page.line(x1, y1, x2, y2, width=0.45, stroke_rgb=self.muted)
        if vertical:
            page.line(x1 - 4, y1, x1 + 4, y1, width=0.45, stroke_rgb=self.muted)
            page.line(x2 - 4, y2, x2 + 4, y2, width=0.45, stroke_rgb=self.muted)
            page.text(x1 + 6, ((y1 + y2) / 2) - 2, label, 5.2, fill_rgb=self.text)
            return
        page.line(x1, y1 - 4, x1, y1 + 4, width=0.45, stroke_rgb=self.muted)
        page.line(x2, y2 - 4, x2, y2 + 4, width=0.45, stroke_rgb=self.muted)
        page.text(((x1 + x2) / 2) - (_estimate_text_width(label, 5.2) / 2), y1 + 4, label, 5.2, fill_rgb=self.text)

    def _draw_hatched_rect(self, page: PdfPage, rect: Rect, color: tuple[float, float, float]) -> None:
        page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.5, stroke_rgb=self.mid)
        step = 8
        cursor = -rect.height
        while cursor < rect.width:
            x1 = rect.x + max(cursor, 0)
            y1 = rect.y + max(-cursor, 0)
            x2 = rect.x + min(rect.width, cursor + rect.height)
            y2 = rect.y + min(rect.height, rect.height + cursor)
            page.line(x1, y1, x2, y2, width=0.5, stroke_rgb=color)
            cursor += step

    def _draw_demo_legend(self, page: PdfPage, rect: Rect) -> None:
        page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.6, stroke_rgb=self.mid)
        page.rect(rect.x + 10, rect.y + 20, 16, 8, stroke_width=0.7, stroke_rgb=self.mid)
        page.text(rect.x + 32, rect.y + 22, "EXISTING", 5.0, fill_rgb=self.text)
        page.rect(rect.x + 10, rect.y + 7, 16, 8, stroke_width=0.7, stroke_rgb=self.demo, fill_rgb=self.demo)
        page.text(rect.x + 32, rect.y + 9, "DEMO CABINET", 5.0, fill_rgb=self.text)

    def _render_detail_sheet(self, page: PdfPage, project: Project, sheet: Sheet) -> None:
        content = self._content_rect(include_sidebar=False)
        left_col = 250.0
        mid_col = 238.0
        right_col = content.width - left_col - mid_col - (DETAIL_GAP * 2)
        top_height = 236.0
        bottom_height = content.height - top_height - DETAIL_GAP

        door_panel = Rect(content.x, content.y + content.height - top_height, left_col, top_height)
        section_panel = Rect(door_panel.x + door_panel.width + DETAIL_GAP, door_panel.y, mid_col, top_height)
        right_panel = Rect(section_panel.x + section_panel.width + DETAIL_GAP, door_panel.y, right_col, top_height)

        lower_left = Rect(content.x, content.y, left_col, bottom_height)
        lower_mid = Rect(lower_left.x + lower_left.width + DETAIL_GAP, content.y, mid_col, bottom_height)
        lower_right = Rect(lower_mid.x + lower_mid.width + DETAIL_GAP, content.y, right_col, bottom_height)

        for title, rect in [
            ("FRONT FRAME DETAILS", door_panel),
            ("WALL / BASE SECTIONS", section_panel),
            ("PLUMBING / VANITY DETAILS", right_panel),
            ("DOOR OPTIONS", lower_left),
            ("SECTION CUTS", lower_mid),
            ("INSTALLATION NOTES", lower_right),
        ]:
            page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.6, stroke_rgb=self.mid)
            self._draw_box_title(page, rect, title)

        self._draw_door_style_panel(page, door_panel, project)
        self._draw_section_panel(page, section_panel)
        self._draw_vanity_panel(page, right_panel)
        self._draw_options_panel(page, lower_left)
        self._draw_section_cuts_panel(page, lower_mid)
        self._draw_install_panel(page, lower_right)

    def _draw_door_style_panel(self, page: PdfPage, rect: Rect, project: Project) -> None:
        preview = Rect(rect.x + 44, rect.y + 72, 100, 130)
        page.rect(preview.x, preview.y, preview.width, preview.height, stroke_width=1.0, stroke_rgb=self.mid, fill_rgb=self.light)
        inset = 14
        page.rect(
            preview.x + inset,
            preview.y + inset,
            preview.width - (inset * 2),
            preview.height - (inset * 2),
            stroke_width=0.9,
            stroke_rgb=self.mid,
        )
        page.text(rect.x + 44, rect.y + 48, f"{project.kcd_style.upper()} / {project.kcd_color}", 6.0, fill_rgb=self.text)
        page.text(rect.x + 44, rect.y + 36, "PAINTED SHAKER PROFILE", 5.6, fill_rgb=self.muted)

    def _draw_section_panel(self, page: PdfPage, rect: Rect) -> None:
        left = Rect(rect.x + 12, rect.y + 26, rect.width / 2 - 18, rect.height - 44)
        right = Rect(rect.x + rect.width / 2 + 6, rect.y + 26, rect.width / 2 - 18, rect.height - 44)
        self._draw_cabinet_section(page, left, "WALL SECTION")
        self._draw_cabinet_section(page, right, "BASE SECTION")

    def _draw_cabinet_section(self, page: PdfPage, rect: Rect, title: str) -> None:
        page.rect(rect.x, rect.y, rect.width, rect.height, stroke_width=0.5, stroke_rgb=self.mid)
        page.text(rect.x + 6, rect.y + rect.height - 12, title, 5.4, fill_rgb=self.text)
        box = Rect(rect.x + 20, rect.y + 28, rect.width - 42, rect.height - 52)
        page.rect(box.x, box.y, box.width, box.height, stroke_width=0.7, stroke_rgb=self.dark)
        page.line(box.x, box.y + box.height - 18, box.x + box.width, box.y + box.height - 18, width=0.6, stroke_rgb=self.mid)
        page.line(box.x + 14, box.y, box.x + 14, box.y + box.height, width=0.6, stroke_rgb=self.mid)
        page.text(box.x + box.width + 10, box.y + box.height - 12, '3/4"', 5.0, fill_rgb=self.text)
        page.text(box.x + box.width + 10, box.y + box.height - 32, '23"', 5.0, fill_rgb=self.text)

    def _draw_vanity_panel(self, page: PdfPage, rect: Rect) -> None:
        upper = Rect(rect.x + 10, rect.y + rect.height / 2 + 4, rect.width - 20, rect.height / 2 - 20)
        lower = Rect(rect.x + 10, rect.y + 12, rect.width - 20, rect.height / 2 - 18)
        for panel, title in [(upper, "PLUMBING DETAIL"), (lower, "VANITY ELEVATION")]:
            page.rect(panel.x, panel.y, panel.width, panel.height, stroke_width=0.5, stroke_rgb=self.mid)
            page.text(panel.x + 6, panel.y + panel.height - 10, title, 5.2, fill_rgb=self.text)
            inner = Rect(panel.x + 24, panel.y + 18, panel.width - 48, panel.height - 34)
            page.rect(inner.x, inner.y, inner.width, inner.height, stroke_width=0.7, stroke_rgb=self.dark)
            page.line(inner.x + inner.width / 2, inner.y, inner.x + inner.width / 2, inner.y + inner.height, width=0.5, stroke_rgb=self.mid)
            page.text(inner.x + 6, inner.y + inner.height + 4, '24"', 5.0, fill_rgb=self.text)
            page.text(inner.x + inner.width + 6, inner.y + inner.height / 2, '34 1/2"', 5.0, fill_rgb=self.text)

    def _draw_options_panel(self, page: PdfPage, rect: Rect) -> None:
        entries = [
            Rect(rect.x + 18, rect.y + rect.height - 58, 42, 34),
            Rect(rect.x + 78, rect.y + rect.height - 58, 42, 34),
            Rect(rect.x + 18, rect.y + rect.height - 112, 102, 34),
        ]
        for entry in entries:
            page.rect(entry.x, entry.y, entry.width, entry.height, stroke_width=0.7, stroke_rgb=self.mid)
            inset = 6
            page.rect(entry.x + inset, entry.y + inset, entry.width - (inset * 2), entry.height - (inset * 2), stroke_width=0.7, stroke_rgb=self.mid)
        page.text(rect.x + 18, rect.y + 18, "DRAWER FRONT OPTIONS AND MATCHING PANELS", 5.4, fill_rgb=self.text)

    def _draw_section_cuts_panel(self, page: PdfPage, rect: Rect) -> None:
        left = Rect(rect.x + 10, rect.y + 12, rect.width / 2 - 15, rect.height - 24)
        right = Rect(rect.x + rect.width / 2 + 5, rect.y + 12, rect.width / 2 - 15, rect.height - 24)
        self._draw_cabinet_section(page, left, "SINK BASE")
        self._draw_cabinet_section(page, right, "END PANEL")

    def _draw_install_panel(self, page: PdfPage, rect: Rect) -> None:
        bullets = [
            "VERIFY REVEALS PRIOR TO INSTALLATION.",
            "SCRIBES FIELD CUT TO WALL CONDITION.",
            "MAINTAIN 1/8\" EXPANSION AT STONE EDGES.",
            "COORDINATE WITH PLUMBING ROUGH-IN.",
            "USE KCD CODES AS ORDER SOURCE OF TRUTH.",
        ]
        cursor = rect.y + rect.height - 34
        for bullet in bullets:
            lines = _wrap_text(bullet, 30)
            for line in lines:
                page.text(rect.x + 10, cursor, line, 5.4, fill_rgb=self.text)
                cursor -= 8
            cursor -= 4
        note_box = Rect(rect.x + 10, rect.y + 16, rect.width - 20, 40)
        page.rect(note_box.x, note_box.y, note_box.width, note_box.height, stroke_width=0.6, stroke_rgb=self.mid, fill_rgb=self.light)
        page.text(note_box.x + 8, note_box.y + 16, "INSTALL PER MANUFACTURER", 6.0, fill_rgb=self.text)

    def _sheet_to_svg(self, project: Project, sheet: Sheet) -> str:
        return "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(SHEET_WIDTH)}" height="{int(SHEET_HEIGHT)}" viewBox="0 0 {SHEET_WIDTH} {SHEET_HEIGHT}">',
                f'<rect x="0" y="0" width="{SHEET_WIDTH}" height="{SHEET_HEIGHT}" fill="{COLOR_BG}" stroke="{COLOR_BLACK}" />',
                f'<text x="24" y="24" font-size="12">OD Select - {sheet.title}</text>',
                f'<text x="24" y="44" font-size="9">{project.address}</text>',
                f'<text x="{SHEET_WIDTH - 70:.0f}" y="{SHEET_HEIGHT - 18:.0f}" font-size="12">{sheet.sheet_number}</text>',
                "</svg>",
            ]
        )
