from dataclasses import dataclass

from od_draw.models.geometry import Point2D


@dataclass
class Annotation:
    kind: str
    position: Point2D
    text: str
    color: str = "#000000"
    font_size: float = 8.0


@dataclass
class VerifiedDimension:
    label: str
    value: float
    start: Point2D
    end: Point2D
    is_verified: bool = False
