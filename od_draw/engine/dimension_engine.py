from __future__ import annotations

from od_draw.models.annotation import VerifiedDimension
from od_draw.models.geometry import Point2D
from od_draw.models.project import Room


def generate_room_dimensions(room: Room) -> list[VerifiedDimension]:
    dimensions: list[VerifiedDimension] = []
    for index, wall in enumerate(room.walls, start=1):
        dimensions.append(
            VerifiedDimension(
                label=f".{index}.",
                value=wall.length,
                start=Point2D(wall.start.x, wall.start.y),
                end=Point2D(wall.end.x, wall.end.y),
                is_verified=index % 2 == 0,
            )
        )
    room.verified_dimensions = dimensions
    return dimensions
