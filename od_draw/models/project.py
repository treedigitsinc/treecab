from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from od_draw.models.annotation import Annotation, VerifiedDimension
from od_draw.models.appliance import Appliance
from od_draw.models.cabinet import CabinetPlacement
from od_draw.models.enums import RoomType, SheetMode
from od_draw.models.geometry import Opening, Wall


@dataclass
class Room:
    id: str
    room_type: RoomType
    room_number: int
    label: str
    ceiling_height: float
    walls: list[Wall] = field(default_factory=list)
    openings: list[Opening] = field(default_factory=list)
    cabinets: list[CabinetPlacement] = field(default_factory=list)
    appliances: list[Appliance] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    verified_dimensions: list[VerifiedDimension] = field(default_factory=list)


@dataclass
class Sheet:
    sheet_number: str
    title: str
    purpose: str
    scale_label: str
    room_ids: list[str]
    mode: SheetMode
    notes: list[str] = field(default_factory=list)


@dataclass
class Project:
    id: str
    address: str
    kcd_color: str
    kcd_style: str
    drawer_type: str
    uppers_height: int
    crown_molding: str
    designer: str
    created_at: date
    project_scope: str = "Kitchen"
    rooms: list[Room] = field(default_factory=list)
    sheets: list[Sheet] = field(default_factory=list)
