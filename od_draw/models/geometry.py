from __future__ import annotations

from dataclasses import dataclass
from math import atan2, hypot

from od_draw.models.enums import OpeningType, WallStatus


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def translate(self, dx: float = 0.0, dy: float = 0.0) -> "Point2D":
        return Point2D(self.x + dx, self.y + dy)


@dataclass
class Wall:
    id: str
    start: Point2D
    end: Point2D
    thickness: float = 4.5
    status: WallStatus = WallStatus.EXISTING

    @property
    def length(self) -> float:
        return hypot(self.end.x - self.start.x, self.end.y - self.start.y)

    @property
    def angle_radians(self) -> float:
        return atan2(self.end.y - self.start.y, self.end.x - self.start.x)

    def point_at(self, offset: float) -> Point2D:
        if self.length == 0:
            return self.start
        ratio = offset / self.length
        return Point2D(
            self.start.x + (self.end.x - self.start.x) * ratio,
            self.start.y + (self.end.y - self.start.y) * ratio,
        )


@dataclass
class Opening:
    id: str
    wall_id: str
    kind: OpeningType
    position_along_wall: float
    width: float
    height: float = 0.0
    sill_height: float = 0.0
    trim_width: float = 3.5
    verify_in_field: bool = False


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float
