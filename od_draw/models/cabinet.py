from __future__ import annotations

from dataclasses import dataclass, field

from od_draw.models.enums import CabinetCategory
from od_draw.models.geometry import Point2D


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    category: CabinetCategory
    width: float
    height: float
    depth: float
    price: float = 0.0
    shelves: int = 0
    drawers: int = 0
    doors: int = 0
    notes: str = ""


@dataclass
class CabinetPlacement:
    id: str
    kcd_code: str
    catalog_entry: CatalogEntry
    wall_id: str
    offset_from_wall_start: float
    position: Point2D
    is_upper: bool = False
    hinge_side: str = "None"
    orientation: str = "standard"
    modifications: list[str] = field(default_factory=list)
