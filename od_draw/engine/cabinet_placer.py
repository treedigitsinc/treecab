from __future__ import annotations

from od_draw.catalog.kcd_catalog import get_prefixed_code, lookup
from od_draw.models.cabinet import CabinetPlacement
from od_draw.models.geometry import Point2D
from od_draw.models.project import Room


def place_run(
    room: Room,
    wall_id: str,
    color_prefix: str,
    codes: list[str],
    start_offset: float = 0.0,
    is_upper: bool = False,
    tag_prefix: str = "",
) -> list[CabinetPlacement]:
    wall = next(wall for wall in room.walls if wall.id == wall_id)
    placements: list[CabinetPlacement] = []
    cursor = start_offset
    for index, code in enumerate(codes, start=1):
        entry = lookup(code)
        point = wall.point_at(cursor + entry.width / 2)
        placement = CabinetPlacement(
            id=f"{room.id}-{tag_prefix or 'cab'}-{index}",
            kcd_code=get_prefixed_code(color_prefix, code),
            catalog_entry=entry,
            wall_id=wall.id,
            offset_from_wall_start=cursor,
            position=Point2D(point.x, point.y),
            is_upper=is_upper,
            hinge_side="Both" if entry.doors > 1 else "None",
        )
        placements.append(placement)
        cursor += entry.width
    room.cabinets.extend(placements)
    return placements
