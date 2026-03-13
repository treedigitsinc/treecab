from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from od_draw.catalog.kcd_catalog import COLOR_LINES, lookup
from od_draw.models.project import Project


def format_inches(value: float) -> str:
    whole = int(value)
    remainder = round(value - whole, 2)
    if abs(remainder - 0.5) < 0.01:
        return f'{whole} 1/2 "' if whole else '1/2 "'
    if abs(remainder - 0.25) < 0.01:
        return f'{whole} 1/4 "' if whole else '1/4 "'
    return f'{value:g} "'


def export_project_tsv(project: Project, output_path: str | Path) -> Path:
    output = Path(output_path)
    grouped = defaultdict(list)
    for room in project.rooms:
        for cabinet in room.cabinets:
            prefix = cabinet.kcd_code.split("-", 1)[0]
            grouped[prefix].append(cabinet)

    lines = [
        "Cabinet List",
        "PROJECT DETAILS",
        "",
        f"ID:\t{project.id}\tCreation Date:\t{project.created_at.isoformat()}",
        f"Dealer\t{project.designer}",
        f"Customer\t{project.address}",
        "DESIGN DETAILS",
        "",
        "Sort order:\tWall/Base/Tall",
    ]

    item_number = 1
    for prefix in sorted(grouped):
        lines.extend(
            [
                "",
                f"CATALOG {prefix}-LOCAL\t0",
                "",
                "Supplier\tKitchen Cabinet Distributors",
                "Door style\t" + COLOR_LINES.get(prefix, prefix),
                "#\tQty\tManuf. code\tWidth\tHeight\tDepth\tLeft-Right\tPrice\tHng",
                "",
            ]
        )
        for cabinet in grouped[prefix]:
            entry = lookup(cabinet.kcd_code)
            lines.append(
                "\t".join(
                    [
                        str(item_number),
                        "1",
                        cabinet.kcd_code,
                        format_inches(entry.width),
                        format_inches(entry.height),
                        format_inches(entry.depth),
                        "F-F",
                        f"{entry.price:.2f}",
                        cabinet.hinge_side,
                    ]
                )
            )
            item_number += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\r\n".join(lines), encoding="utf-8")
    return output
