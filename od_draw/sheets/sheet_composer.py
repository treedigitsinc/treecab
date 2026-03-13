from __future__ import annotations

from od_draw.models.enums import SheetMode
from od_draw.models.project import Project, Sheet


def build_default_sheets(project: Project) -> list[Sheet]:
    kitchens = [room for room in project.rooms if room.room_type.value == "kitchen"]
    baths = [room for room in project.rooms if "bath" in room.room_type.value]
    sheets = [
        Sheet(
            sheet_number="CP-00",
            title="Measurement Guide",
            purpose="FOR CONSTRUCTION",
            scale_label="NTS",
            room_ids=[],
            mode=SheetMode.COVER,
            notes=[
                "All dimensions are inches.",
                "Verify openings in field before ordering.",
                "Submit all requested photos with measurements.",
            ],
        )
    ]

    if kitchens:
        kitchen = kitchens[0]
        sheets.extend(
            [
                Sheet(
                    sheet_number="A-01",
                    title="Demo Kitchen Plan",
                    purpose="FOR CONSTRUCTION",
                    scale_label='1/2" = 1\'-0"',
                    room_ids=[kitchen.id],
                    mode=SheetMode.DEMO,
                    notes=["Show demolition extents and confirm field conditions."],
                ),
                Sheet(
                    sheet_number="A-02",
                    title="New Kitchen Layout",
                    purpose="FOR CONSTRUCTION",
                    scale_label='1/2" = 1\'-0"',
                    room_ids=[kitchen.id],
                    mode=SheetMode.LAYOUT,
                    notes=[
                        "DW remains adjacent to sink base.",
                        "Maintain 15 inch landing each side of range.",
                        "Upper cabinet tags centered in each box.",
                    ],
                ),
            ]
        )

    if baths:
        sheets.append(
            Sheet(
                sheet_number="A-03",
                title="Bathroom Demo Plans",
                purpose="FOR CONSTRUCTION",
                scale_label='1/2" = 1\'-0"',
                room_ids=[room.id for room in baths],
                mode=SheetMode.DEMO,
                notes=["Verify plumbing centerlines before vanity ordering."],
            )
        )

    if baths:
        sheets.append(
            Sheet(
                sheet_number="A-04",
                title="Bathroom Layouts",
                purpose="FOR CONSTRUCTION",
                scale_label='1/2" = 1\'-0"',
                room_ids=[room.id for room in baths],
                mode=SheetMode.BATH,
                notes=["Coordinate vanity centerlines with plumbing rough-in."],
            )
        )

    sheets.append(
        Sheet(
            sheet_number="D-01",
            title="Details",
            purpose="FOR CONSTRUCTION",
            scale_label="As indicated",
            room_ids=[],
            mode=SheetMode.DETAILS,
            notes=["Use KCD codes as the order source of truth."],
        )
    )
    project.sheets = sheets
    return project.sheets
