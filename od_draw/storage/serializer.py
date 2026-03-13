from __future__ import annotations

from datetime import date

from od_draw.catalog.kcd_catalog import lookup
from od_draw.models.annotation import Annotation, VerifiedDimension
from od_draw.models.appliance import Appliance
from od_draw.models.cabinet import CabinetPlacement
from od_draw.models.enums import ApplianceType, OpeningType, RoomType, SheetMode, WallStatus
from od_draw.models.geometry import Opening, Point2D, Wall
from od_draw.models.project import Project, Room, Sheet


def point_to_dict(point: Point2D) -> dict:
    return {"x": point.x, "y": point.y}


def point_from_dict(data: dict) -> Point2D:
    return Point2D(x=float(data["x"]), y=float(data["y"]))


def wall_to_dict(wall: Wall) -> dict:
    return {
        "id": wall.id,
        "start": point_to_dict(wall.start),
        "end": point_to_dict(wall.end),
        "thickness": wall.thickness,
        "status": wall.status.value,
    }


def wall_from_dict(data: dict) -> Wall:
    return Wall(
        id=data["id"],
        start=point_from_dict(data["start"]),
        end=point_from_dict(data["end"]),
        thickness=float(data.get("thickness", 4.5)),
        status=WallStatus(data.get("status", WallStatus.EXISTING.value)),
    )


def opening_to_dict(opening: Opening) -> dict:
    return {
        "id": opening.id,
        "wall_id": opening.wall_id,
        "kind": opening.kind.value,
        "position_along_wall": opening.position_along_wall,
        "width": opening.width,
        "height": opening.height,
        "sill_height": opening.sill_height,
        "trim_width": opening.trim_width,
        "verify_in_field": opening.verify_in_field,
    }


def opening_from_dict(data: dict) -> Opening:
    return Opening(
        id=data["id"],
        wall_id=data["wall_id"],
        kind=OpeningType(data["kind"]),
        position_along_wall=float(data["position_along_wall"]),
        width=float(data["width"]),
        height=float(data.get("height", 0.0)),
        sill_height=float(data.get("sill_height", 0.0)),
        trim_width=float(data.get("trim_width", 3.5)),
        verify_in_field=bool(data.get("verify_in_field", False)),
    )


def cabinet_to_dict(cabinet: CabinetPlacement) -> dict:
    return {
        "id": cabinet.id,
        "kcd_code": cabinet.kcd_code,
        "wall_id": cabinet.wall_id,
        "offset_from_wall_start": cabinet.offset_from_wall_start,
        "position": point_to_dict(cabinet.position),
        "is_upper": cabinet.is_upper,
        "hinge_side": cabinet.hinge_side,
        "orientation": cabinet.orientation,
        "modifications": list(cabinet.modifications),
    }


def cabinet_from_dict(data: dict) -> CabinetPlacement:
    return CabinetPlacement(
        id=data["id"],
        kcd_code=data["kcd_code"],
        catalog_entry=lookup(data["kcd_code"]),
        wall_id=data["wall_id"],
        offset_from_wall_start=float(data["offset_from_wall_start"]),
        position=point_from_dict(data["position"]),
        is_upper=bool(data.get("is_upper", False)),
        hinge_side=data.get("hinge_side", "None"),
        orientation=data.get("orientation", "standard"),
        modifications=list(data.get("modifications", [])),
    )


def appliance_to_dict(appliance: Appliance) -> dict:
    return {
        "id": appliance.id,
        "type": appliance.type.value,
        "width": appliance.width,
        "depth": appliance.depth,
        "position": point_to_dict(appliance.position),
        "wall_id": appliance.wall_id,
        "label": appliance.label,
    }


def appliance_from_dict(data: dict) -> Appliance:
    return Appliance(
        id=data["id"],
        type=ApplianceType(data["type"]),
        width=float(data["width"]),
        depth=float(data["depth"]),
        position=point_from_dict(data["position"]),
        wall_id=data["wall_id"],
        label=data["label"],
    )


def annotation_to_dict(annotation: Annotation) -> dict:
    return {
        "kind": annotation.kind,
        "position": point_to_dict(annotation.position),
        "text": annotation.text,
        "color": annotation.color,
        "font_size": annotation.font_size,
    }


def annotation_from_dict(data: dict) -> Annotation:
    return Annotation(
        kind=data["kind"],
        position=point_from_dict(data["position"]),
        text=data["text"],
        color=data.get("color", "#000000"),
        font_size=float(data.get("font_size", 8.0)),
    )


def verified_dimension_to_dict(dimension: VerifiedDimension) -> dict:
    return {
        "label": dimension.label,
        "value": dimension.value,
        "start": point_to_dict(dimension.start),
        "end": point_to_dict(dimension.end),
        "is_verified": dimension.is_verified,
    }


def verified_dimension_from_dict(data: dict) -> VerifiedDimension:
    return VerifiedDimension(
        label=data["label"],
        value=float(data["value"]),
        start=point_from_dict(data["start"]),
        end=point_from_dict(data["end"]),
        is_verified=bool(data.get("is_verified", False)),
    )


def room_to_dict(room: Room) -> dict:
    return {
        "id": room.id,
        "room_type": room.room_type.value,
        "room_number": room.room_number,
        "label": room.label,
        "ceiling_height": room.ceiling_height,
        "walls": [wall_to_dict(wall) for wall in room.walls],
        "openings": [opening_to_dict(opening) for opening in room.openings],
        "cabinets": [cabinet_to_dict(cabinet) for cabinet in room.cabinets],
        "appliances": [appliance_to_dict(appliance) for appliance in room.appliances],
        "annotations": [annotation_to_dict(annotation) for annotation in room.annotations],
        "verified_dimensions": [
            verified_dimension_to_dict(dimension) for dimension in room.verified_dimensions
        ],
    }


def room_from_dict(data: dict) -> Room:
    return Room(
        id=data["id"],
        room_type=RoomType(data["room_type"]),
        room_number=int(data["room_number"]),
        label=data["label"],
        ceiling_height=float(data["ceiling_height"]),
        walls=[wall_from_dict(wall) for wall in data.get("walls", [])],
        openings=[opening_from_dict(opening) for opening in data.get("openings", [])],
        cabinets=[cabinet_from_dict(cabinet) for cabinet in data.get("cabinets", [])],
        appliances=[appliance_from_dict(appliance) for appliance in data.get("appliances", [])],
        annotations=[annotation_from_dict(annotation) for annotation in data.get("annotations", [])],
        verified_dimensions=[
            verified_dimension_from_dict(dimension) for dimension in data.get("verified_dimensions", [])
        ],
    )


def sheet_to_dict(sheet: Sheet) -> dict:
    return {
        "sheet_number": sheet.sheet_number,
        "title": sheet.title,
        "purpose": sheet.purpose,
        "scale_label": sheet.scale_label,
        "room_ids": list(sheet.room_ids),
        "mode": sheet.mode.value,
        "notes": list(sheet.notes),
    }


def sheet_from_dict(data: dict) -> Sheet:
    return Sheet(
        sheet_number=data["sheet_number"],
        title=data["title"],
        purpose=data["purpose"],
        scale_label=data["scale_label"],
        room_ids=list(data.get("room_ids", [])),
        mode=SheetMode(data["mode"]),
        notes=list(data.get("notes", [])),
    )


def project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "address": project.address,
        "kcd_color": project.kcd_color,
        "kcd_style": project.kcd_style,
        "drawer_type": project.drawer_type,
        "uppers_height": project.uppers_height,
        "crown_molding": project.crown_molding,
        "designer": project.designer,
        "created_at": project.created_at.isoformat(),
        "rooms": [room_to_dict(room) for room in project.rooms],
        "sheets": [sheet_to_dict(sheet) for sheet in project.sheets],
    }


def project_from_dict(data: dict) -> Project:
    return Project(
        id=data["id"],
        address=data["address"],
        kcd_color=data["kcd_color"],
        kcd_style=data["kcd_style"],
        drawer_type=data["drawer_type"],
        uppers_height=int(data["uppers_height"]),
        crown_molding=data["crown_molding"],
        designer=data["designer"],
        created_at=date.fromisoformat(data["created_at"]),
        rooms=[room_from_dict(room) for room in data.get("rooms", [])],
        sheets=[sheet_from_dict(sheet) for sheet in data.get("sheets", [])],
    )
