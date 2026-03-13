from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from od_draw.catalog.master_catalog import COLOR_LINES, get_full_code, lookup
from od_draw.models.master import Project


def export_order_tsv(project: Project) -> str:
    lines = [
        "Cabinet List",
        "PROJECT DETAILS",
        "",
        f"ID:\t\tCreation Date:\t{project.date}",
        "Dealer",
        "Customer",
        "DESIGN DETAILS",
        "",
        "Sort order:\tBase/Wall/Tall",
    ]

    grouped: dict[str, list] = defaultdict(list)
    for room in project.model.rooms:
        for cabinet in room.cabinets:
            prefix = cabinet.color_prefix or project.kcd_color
            grouped[prefix].append(cabinet)

    item_number = 1
    page_number = 1
    for prefix, cabinets in sorted(grouped.items()):
        lines.extend(
            [
                "",
                f"Print date:\t{project.date}\tPage {page_number} / \t{len(grouped)}",
                f"CATALOG KCD10-{page_number}_1\t0",
                "",
                "Supplier\tKitchen Cabinet Distributors",
                f"Door style\t{project.kcd_style} {COLOR_LINES.get(prefix, prefix)}",
                "#\tQty\tManuf. code\tWidth\tHeight\tDepth\tLeft-Right\tPrice\tHng",
                "",
            ]
        )
        for cabinet in cabinets:
            entry = lookup(cabinet.base_code or cabinet.kcd_code)
            if entry is None:
                continue
            full_code = cabinet.kcd_code or get_full_code(prefix, cabinet.base_code)
            hinge = cabinet.hinge_side if cabinet.hinge_side != "None" else "None"
            lines.append(
                f"{item_number}\t1\t{full_code}\t"
                f'{entry.width} "\t{entry.height} "\t{entry.depth} "\t'
                f"F-F\t0.00\t{hinge}"
            )
            item_number += 1
        lines.append(f"Number of items for this catalog:\t{len(cabinets)}")
        page_number += 1

    return "\r\n".join(lines)


def export_project_tsv(project: Project, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.write_bytes(export_order_tsv(project).encode("utf-8"))
    return path
