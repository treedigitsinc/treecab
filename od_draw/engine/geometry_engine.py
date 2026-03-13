from __future__ import annotations

from od_draw.engine.dimension_engine import generate_room_dimensions
from od_draw.models.geometry import Point2D
from od_draw.models.project import Project


def sync_cabinets(project: Project) -> Project:
    for room in project.rooms:
        wall_map = {wall.id: wall for wall in room.walls}
        for cabinet in room.cabinets:
            wall = wall_map.get(cabinet.wall_id)
            if wall is None:
                continue
            center_offset = cabinet.offset_from_wall_start + cabinet.catalog_entry.width / 2
            point = wall.point_at(center_offset)
            cabinet.position = Point2D(point.x, point.y)
        for appliance in room.appliances:
            if appliance.wall_id not in wall_map:
                continue
    return project


def prepare_project(project: Project) -> Project:
    sync_cabinets(project)
    for room in project.rooms:
        generate_room_dimensions(room)
    return project
