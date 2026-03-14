from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import atan2, hypot
from typing import Iterable
from uuid import uuid4


class WallStatus(str, Enum):
    EXISTING = "existing"
    TO_REMOVE = "to_remove"
    NEW = "new"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    CASED = "cased"


class ApplianceType(str, Enum):
    DW = "DW"
    REF = "REF"
    RNG = "RNG"
    MW = "MW"
    WO = "WO"
    SINK = "SINK"


class RoomType(str, Enum):
    KITCHEN = "Kitchen"
    DINING_AREA = "DiningArea"
    LAUNDRY = "Laundry"
    MAIN_BATH = "MainBath"
    BATH = "Bath"


class SheetPurpose(str, Enum):
    BID = "FOR BID"
    CONSTRUCTION = "FOR CONSTRUCTION"


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


@dataclass(frozen=True)
class Size2D:
    width: float
    height: float


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains_point(self, point: Point2D) -> bool:
        return self.x <= point.x <= self.right and self.y <= point.y <= self.bottom

    def intersects_rect(self, other: "Rect") -> bool:
        return not (
            self.right < other.x or other.right < self.x or self.bottom < other.y or other.bottom < self.y
        )


@dataclass
class Wall:
    id: str = field(default_factory=lambda: str(uuid4()))
    start: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    end: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    thickness: float = 4.5
    status: WallStatus = WallStatus.EXISTING

    @property
    def length(self) -> float:
        return hypot(self.end.x - self.start.x, self.end.y - self.start.y)

    @property
    def angle(self) -> float:
        return atan2(self.end.y - self.start.y, self.end.x - self.start.x)

    @property
    def bounds(self) -> Rect:
        x1, x2 = sorted((self.start.x, self.end.x))
        y1, y2 = sorted((self.start.y, self.end.y))
        pad = self.thickness / 2
        return Rect(x1 - pad, y1 - pad, max(x2 - x1, 0.0) + pad * 2, max(y2 - y1, 0.0) + pad * 2)


@dataclass
class Opening:
    id: str = field(default_factory=lambda: str(uuid4()))
    wall_id: str = ""
    type: OpeningType = OpeningType.DOOR
    position_along_wall: float = 0.0
    width: float = 30.0
    height: float = 80.0
    sill_height: float = 0.0
    trim_width: float = 3.5


@dataclass
class CabinetInstance:
    id: str = field(default_factory=lambda: str(uuid4()))
    kcd_code: str = ""
    base_code: str = ""
    color_prefix: str = ""
    wall_id: str = ""
    position: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    is_upper: bool = False
    hinge_side: str = "None"
    modifications: list[str] = field(default_factory=list)


@dataclass
class Appliance:
    id: str = field(default_factory=lambda: str(uuid4()))
    type: ApplianceType = ApplianceType.SINK
    position: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    width: float = 30.0
    depth: float = 24.0
    label: str = ""


@dataclass
class Dimension:
    id: str = field(default_factory=lambda: str(uuid4()))
    start: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    end: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    is_vif: bool = False
    vif_label: str = ""
    value: float | None = None
    offset: float = 8.0


@dataclass
class RoomTag:
    id: str = field(default_factory=lambda: str(uuid4()))
    position: Point2D = field(default_factory=lambda: Point2D(0.0, 0.0))
    room_type: RoomType = RoomType.KITCHEN
    room_number: int = 1
    label: str = "KITCHEN"
    note: str = ""


@dataclass
class PDFCalibration:
    pdf_point_a: Point2D
    pdf_point_b: Point2D
    model_point_a: Point2D
    model_point_b: Point2D
    known_distance: float

    @property
    def pixels_per_inch(self) -> float:
        pixel_distance = hypot(
            self.pdf_point_b.x - self.pdf_point_a.x,
            self.pdf_point_b.y - self.pdf_point_a.y,
        )
        return pixel_distance / self.known_distance if self.known_distance else 0.0

    @property
    def transform_matrix(self) -> tuple[float, float, float, float, float, float]:
        ppi = self.pixels_per_inch or 1.0
        scale = 1 / ppi
        return (
            scale,
            0.0,
            0.0,
            scale,
            self.model_point_a.x - self.pdf_point_a.x * scale,
            self.model_point_a.y - self.pdf_point_a.y * scale,
        )


@dataclass
class LinkedPDF:
    id: str = field(default_factory=lambda: str(uuid4()))
    file_path: str = ""
    page_number: int = 0
    calibration: PDFCalibration | None = None
    opacity: float = 0.3
    visible: bool = True
    locked: bool = False


@dataclass
class Room:
    id: str = field(default_factory=lambda: str(uuid4()))
    room_type: RoomType = RoomType.KITCHEN
    room_number: int = 1
    walls: list[Wall] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    cabinets: list[CabinetInstance] = field(default_factory=list)
    appliances: list[Appliance] = field(default_factory=list)
    dimensions: list[Dimension] = field(default_factory=list)
    tags: list[RoomTag] = field(default_factory=list)
    ceiling_height: float = 96.0

    def all_geometry(self) -> Iterable[object]:
        yield from self.walls
        yield from self.openings
        yield from self.cabinets
        yield from self.appliances
        yield from self.dimensions
        yield from self.tags


@dataclass
class Viewport:
    id: str = field(default_factory=lambda: str(uuid4()))
    label: str = ""
    crop_rect: Rect = field(default_factory=lambda: Rect(0.0, 0.0, 240.0, 180.0))
    scale: str = '1/2" = 1\'-0"'
    scale_factor: float = 0.5 / 12
    position_on_sheet: Point2D = field(default_factory=lambda: Point2D(18.0, 18.0))
    size_on_sheet: Size2D = field(default_factory=lambda: Size2D(720.0, 540.0))
    render_layers: list[str] = field(
        default_factory=lambda: ["underlay", "walls", "openings", "cabinets", "appliances", "dimensions", "annotations"]
    )
    is_active: bool = False


@dataclass
class Sheet:
    id: str = field(default_factory=lambda: str(uuid4()))
    sheet_number: str = "A-01"
    description: str = "DEMO KITCHEN PLAN"
    purpose: SheetPurpose = SheetPurpose.BID
    scale: str = '1/2" = 1\'-0"'
    date: str = ""
    designer: str = "YES"
    viewports: list[Viewport] = field(default_factory=list)
    has_notes_sidebar: bool = True
    notes_template: str = "kitchen_bid"


def _line_intersects_rect(start: Point2D, end: Point2D, rect: Rect) -> bool:
    line_bounds = Rect(
        min(start.x, end.x),
        min(start.y, end.y),
        abs(end.x - start.x),
        abs(end.y - start.y),
    )
    if rect.contains_point(start) or rect.contains_point(end):
        return True
    return rect.intersects_rect(line_bounds)


@dataclass
class ModelSpace:
    rooms: list[Room] = field(default_factory=list)
    linked_pdfs: list[LinkedPDF] = field(default_factory=list)

    def get_walls_in_rect(self, rect: Rect) -> list[Wall]:
        walls: list[Wall] = []
        for room in self.rooms:
            for wall in room.walls:
                if _line_intersects_rect(wall.start, wall.end, rect):
                    walls.append(wall)
        return walls

    def get_openings_in_rect(self, rect: Rect) -> list[Opening]:
        results: list[Opening] = []
        for room in self.rooms:
            wall_map = {wall.id: wall for wall in room.walls}
            for opening in room.openings:
                wall = wall_map.get(opening.wall_id)
                if wall and wall.bounds.intersects_rect(rect):
                    results.append(opening)
        return results

    def get_cabinets_in_rect(self, rect: Rect) -> list[CabinetInstance]:
        return [
            cabinet
            for room in self.rooms
            for cabinet in room.cabinets
            if rect.contains_point(cabinet.position)
        ]

    def get_appliances_in_rect(self, rect: Rect) -> list[Appliance]:
        return [
            appliance
            for room in self.rooms
            for appliance in room.appliances
            if rect.contains_point(appliance.position)
        ]

    def get_dimensions_in_rect(self, rect: Rect) -> list[Dimension]:
        results: list[Dimension] = []
        for room in self.rooms:
            for dimension in room.dimensions:
                if rect.contains_point(dimension.start) or rect.contains_point(dimension.end):
                    results.append(dimension)
        return results

    def get_annotations_in_rect(self, rect: Rect) -> list[RoomTag]:
        return [
            tag
            for room in self.rooms
            for tag in room.tags
            if rect.contains_point(tag.position)
        ]


@dataclass
class Project:
    id: str = field(default_factory=lambda: str(uuid4()))
    project_name: str = ""
    address: str = ""
    project_type: str = "Kitchen"
    kcd_color: str = "OW"
    kcd_style: str = "Oslo"
    drawer_type: str = "slab"
    uppers_height: int = 36
    crown_molding: str = "Flat"
    status: str = "A1_Request"
    model: ModelSpace = field(default_factory=ModelSpace)
    sheets: list[Sheet] = field(default_factory=list)
    date: str = ""
