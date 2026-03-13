from dataclasses import dataclass

from od_draw.models.enums import ApplianceType
from od_draw.models.geometry import Point2D


@dataclass
class Appliance:
    id: str
    type: ApplianceType
    width: float
    depth: float
    position: Point2D
    wall_id: str
    label: str
