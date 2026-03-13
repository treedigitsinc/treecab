from __future__ import annotations

from od_draw.models.master import (
    Appliance,
    ApplianceType,
    CabinetInstance,
    Dimension,
    ModelSpace,
    Opening,
    OpeningType,
    Point2D,
    Project,
    Rect,
    Room,
    RoomTag,
    RoomType,
    Sheet,
    SheetPurpose,
    Size2D,
    Viewport,
    Wall,
    WallStatus,
)


def build_sample_master_project() -> Project:
    room = Room(
        room_type=RoomType.KITCHEN,
        room_number=1,
        ceiling_height=96.0,
        walls=[
            Wall(start=Point2D(0, 0), end=Point2D(180, 0), status=WallStatus.EXISTING),
            Wall(start=Point2D(180, 0), end=Point2D(180, 144), status=WallStatus.NEW),
            Wall(start=Point2D(180, 144), end=Point2D(0, 144), status=WallStatus.EXISTING),
            Wall(start=Point2D(0, 144), end=Point2D(0, 0), status=WallStatus.TO_REMOVE),
        ],
        openings=[
            Opening(wall_id="", type=OpeningType.DOOR, position_along_wall=42, width=32),
            Opening(wall_id="", type=OpeningType.WINDOW, position_along_wall=54, width=48, height=48, sill_height=42),
        ],
        cabinets=[
            CabinetInstance(kcd_code="OW-B30", base_code="B30", color_prefix="OW", position=Point2D(12, 24)),
            CabinetInstance(kcd_code="OW-SB36", base_code="SB36", color_prefix="OW", position=Point2D(48, 24)),
            CabinetInstance(kcd_code="OW-DB24-3", base_code="DB24-3", color_prefix="OW", position=Point2D(90, 24)),
            CabinetInstance(
                kcd_code="OW-W3036",
                base_code="W3036",
                color_prefix="OW",
                position=Point2D(12, 102),
                is_upper=True,
            ),
        ],
        appliances=[
            Appliance(type=ApplianceType.SINK, position=Point2D(66, 36), width=33, depth=22, label="SINK"),
            Appliance(type=ApplianceType.DW, position=Point2D(102, 36), width=24, depth=24, label="DW"),
        ],
        dimensions=[
            Dimension(start=Point2D(0, 0), end=Point2D(180, 0), is_vif=True, vif_label="1"),
            Dimension(start=Point2D(180, 0), end=Point2D(180, 144), value=144),
        ],
        tags=[RoomTag(position=Point2D(92, 76), room_type=RoomType.KITCHEN, room_number=1, label="KITCHEN")],
    )

    room.openings[0].wall_id = room.walls[3].id
    room.openings[1].wall_id = room.walls[2].id
    room.cabinets[0].wall_id = room.walls[0].id
    room.cabinets[1].wall_id = room.walls[0].id
    room.cabinets[2].wall_id = room.walls[0].id
    room.cabinets[3].wall_id = room.walls[2].id

    model = ModelSpace(rooms=[room])
    viewport = Viewport(
        label="1  NEW KITCHEN LAYOUT",
        crop_rect=Rect(-12, -12, 204, 168),
        scale='1/2" = 1\'-0"',
        scale_factor=0.5 / 12,
        position_on_sheet=Point2D(48, 88),
        size_on_sheet=Size2D(720, 520),
    )
    sheet = Sheet(
        sheet_number="A-02",
        description="NEW KITCHEN LAYOUT",
        purpose=SheetPurpose.CONSTRUCTION,
        scale=viewport.scale,
        date="2026-03-13",
        designer="YES",
        viewports=[viewport],
    )

    return Project(
        address="773 Harbor View Rd Charleston, SC 29412",
        project_type="Kitchen",
        kcd_color="OW",
        kcd_style="Oslo",
        drawer_type="slab",
        uppers_height=36,
        crown_molding="Flat",
        status="A4_Construction",
        model=model,
        sheets=[sheet],
        date="2026-03-13",
    )
