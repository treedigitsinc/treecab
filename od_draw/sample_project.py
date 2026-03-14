from __future__ import annotations

from datetime import date

from od_draw.engine.cabinet_placer import place_run
from od_draw.engine.room_builder import build_rectangular_room
from od_draw.models.appliance import Appliance
from od_draw.models.enums import ApplianceType, OpeningType, RoomType, WallStatus
from od_draw.models.geometry import Opening, Point2D
from od_draw.models.project import Project


def build_sample_project() -> Project:
    kitchen = build_rectangular_room("kitchen-1", RoomType.KITCHEN, 1, "Kitchen", 180, 144)
    main_bath = build_rectangular_room("bath-1", RoomType.MAIN_BATH, 2, "Main Bath", 96, 60)
    secondary_bath = build_rectangular_room("bath-2", RoomType.BATH, 3, "Bath", 72, 60)

    kitchen.walls[0].status = WallStatus.TO_REMOVE
    kitchen.walls[2].status = WallStatus.NEW
    kitchen.openings.extend(
        [
            Opening("k-door", kitchen.walls[3].id, OpeningType.DOOR, 42, 32, verify_in_field=True),
            Opening("k-window", kitchen.walls[2].id, OpeningType.WINDOW, 54, 48, height=48, sill_height=42),
        ]
    )
    main_bath.openings.append(Opening("mb-door", main_bath.walls[3].id, OpeningType.DOOR, 18, 30))
    secondary_bath.openings.append(Opening("sb-door", secondary_bath.walls[3].id, OpeningType.DOOR, 18, 28))

    place_run(kitchen, kitchen.walls[2].id, "BW", ["B30", "SB36", "DB24-3", "B30"], tag_prefix="base")
    place_run(kitchen, kitchen.walls[1].id, "BW", ["ER33", "DB30-3"], start_offset=24, tag_prefix="base-e")
    place_run(kitchen, kitchen.walls[2].id, "BW", ["W3036", "W3636", "W2436", "W3036"], is_upper=True, tag_prefix="upper")
    place_run(main_bath, main_bath.walls[2].id, "OW", ["VSBDL30", "VSBDR30"], tag_prefix="vanity")
    place_run(secondary_bath, secondary_bath.walls[2].id, "OW", ["V30"], tag_prefix="vanity")

    kitchen.appliances.extend(
        [
            Appliance("sink-1", ApplianceType.SINK, 33, 22, Point2D(78, 144), kitchen.walls[2].id, "SINK"),
            Appliance("dw-1", ApplianceType.DW, 24, 24, Point2D(48, 126), kitchen.walls[2].id, "DW"),
            Appliance("rng-1", ApplianceType.RNG, 30, 27, Point2D(142, 126), kitchen.walls[1].id, "RNG"),
            Appliance("ref-1", ApplianceType.REF, 36, 30, Point2D(166, 42), kitchen.walls[1].id, "REF"),
        ]
    )
    main_bath.appliances.append(
        Appliance("mb-sink", ApplianceType.SINK, 24, 18, Point2D(48, 48), main_bath.walls[2].id, "SINK")
    )
    secondary_bath.appliances.append(
        Appliance("sb-sink", ApplianceType.SINK, 24, 18, Point2D(36, 48), secondary_bath.walls[2].id, "SINK")
    )

    return Project(
        id="od-select-sample",
        address="773 Harbor View Rd, Charleston, SC 29412",
        kcd_color="BW",
        kcd_style="Brooklyn White",
        drawer_type="5-piece",
        uppers_height=36,
        crown_molding="Flat",
        designer="LOCAL MVP",
        created_at=date(2026, 3, 13),
        project_scope="Kitchen + Baths",
        rooms=[kitchen, main_bath, secondary_bath],
    )
