from od_draw.models.enums import RoomType, WallStatus
from od_draw.models.geometry import Point2D, Wall
from od_draw.models.project import Room


def build_rectangular_room(
    room_id: str,
    room_type: RoomType,
    room_number: int,
    label: str,
    width: float,
    depth: float,
    ceiling_height: float = 96.0,
    origin: Point2D = Point2D(0, 0),
) -> Room:
    x0, y0 = origin.x, origin.y
    corners = [
        Point2D(x0, y0),
        Point2D(x0 + width, y0),
        Point2D(x0 + width, y0 + depth),
        Point2D(x0, y0 + depth),
    ]
    walls = [
        Wall(f"{room_id}-w1", corners[0], corners[1], status=WallStatus.EXISTING),
        Wall(f"{room_id}-w2", corners[1], corners[2], status=WallStatus.EXISTING),
        Wall(f"{room_id}-w3", corners[2], corners[3], status=WallStatus.EXISTING),
        Wall(f"{room_id}-w4", corners[3], corners[0], status=WallStatus.EXISTING),
    ]
    return Room(
        id=room_id,
        room_type=room_type,
        room_number=room_number,
        label=label,
        ceiling_height=ceiling_height,
        walls=walls,
    )
