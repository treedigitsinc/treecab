from __future__ import annotations

from od_draw.models.master import (
    Appliance,
    ApplianceType,
    CabinetInstance,
    Dimension,
    LinkedPDF,
    ModelSpace,
    Opening,
    OpeningType,
    PDFCalibration,
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


def point_to_dict(point: Point2D) -> dict:
    return {"x": point.x, "y": point.y}


def point_from_dict(data: dict) -> Point2D:
    return Point2D(x=float(data["x"]), y=float(data["y"]))


def size_to_dict(size: Size2D) -> dict:
    return {"width": size.width, "height": size.height}


def size_from_dict(data: dict) -> Size2D:
    return Size2D(width=float(data["width"]), height=float(data["height"]))


def rect_to_dict(rect: Rect) -> dict:
    return {"x": rect.x, "y": rect.y, "width": rect.width, "height": rect.height}


def rect_from_dict(data: dict) -> Rect:
    return Rect(
        x=float(data["x"]),
        y=float(data["y"]),
        width=float(data["width"]),
        height=float(data["height"]),
    )


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
        "type": opening.type.value,
        "position_along_wall": opening.position_along_wall,
        "width": opening.width,
        "height": opening.height,
        "sill_height": opening.sill_height,
        "trim_width": opening.trim_width,
    }


def opening_from_dict(data: dict) -> Opening:
    return Opening(
        id=data["id"],
        wall_id=data["wall_id"],
        type=OpeningType(data.get("type", OpeningType.DOOR.value)),
        position_along_wall=float(data.get("position_along_wall", 0.0)),
        width=float(data.get("width", 30.0)),
        height=float(data.get("height", 80.0)),
        sill_height=float(data.get("sill_height", 0.0)),
        trim_width=float(data.get("trim_width", 3.5)),
    )


def cabinet_to_dict(cabinet: CabinetInstance) -> dict:
    return {
        "id": cabinet.id,
        "kcd_code": cabinet.kcd_code,
        "base_code": cabinet.base_code,
        "color_prefix": cabinet.color_prefix,
        "wall_id": cabinet.wall_id,
        "position": point_to_dict(cabinet.position),
        "is_upper": cabinet.is_upper,
        "hinge_side": cabinet.hinge_side,
        "modifications": list(cabinet.modifications),
    }


def cabinet_from_dict(data: dict) -> CabinetInstance:
    return CabinetInstance(
        id=data["id"],
        kcd_code=data.get("kcd_code", ""),
        base_code=data.get("base_code", ""),
        color_prefix=data.get("color_prefix", ""),
        wall_id=data.get("wall_id", ""),
        position=point_from_dict(data.get("position", {"x": 0.0, "y": 0.0})),
        is_upper=bool(data.get("is_upper", False)),
        hinge_side=data.get("hinge_side", "None"),
        modifications=list(data.get("modifications", [])),
    )


def appliance_to_dict(appliance: Appliance) -> dict:
    return {
        "id": appliance.id,
        "type": appliance.type.value,
        "position": point_to_dict(appliance.position),
        "width": appliance.width,
        "depth": appliance.depth,
        "label": appliance.label,
    }


def appliance_from_dict(data: dict) -> Appliance:
    return Appliance(
        id=data["id"],
        type=ApplianceType(data.get("type", ApplianceType.SINK.value)),
        position=point_from_dict(data.get("position", {"x": 0.0, "y": 0.0})),
        width=float(data.get("width", 30.0)),
        depth=float(data.get("depth", 24.0)),
        label=data.get("label", ""),
    )


def dimension_to_dict(dimension: Dimension) -> dict:
    return {
        "id": dimension.id,
        "start": point_to_dict(dimension.start),
        "end": point_to_dict(dimension.end),
        "is_vif": dimension.is_vif,
        "vif_label": dimension.vif_label,
        "value": dimension.value,
        "offset": dimension.offset,
    }


def dimension_from_dict(data: dict) -> Dimension:
    value = data.get("value")
    return Dimension(
        id=data["id"],
        start=point_from_dict(data.get("start", {"x": 0.0, "y": 0.0})),
        end=point_from_dict(data.get("end", {"x": 0.0, "y": 0.0})),
        is_vif=bool(data.get("is_vif", False)),
        vif_label=data.get("vif_label", ""),
        value=float(value) if value is not None else None,
        offset=float(data.get("offset", 8.0)),
    )


def room_tag_to_dict(tag: RoomTag) -> dict:
    return {
        "id": tag.id,
        "position": point_to_dict(tag.position),
        "room_type": tag.room_type.value,
        "room_number": tag.room_number,
        "label": tag.label,
        "note": tag.note,
    }


def room_tag_from_dict(data: dict) -> RoomTag:
    return RoomTag(
        id=data["id"],
        position=point_from_dict(data.get("position", {"x": 0.0, "y": 0.0})),
        room_type=RoomType(data.get("room_type", RoomType.KITCHEN.value)),
        room_number=int(data.get("room_number", 1)),
        label=data.get("label", "KITCHEN"),
        note=data.get("note", ""),
    )


def calibration_to_dict(calibration: PDFCalibration) -> dict:
    return {
        "pdf_point_a": point_to_dict(calibration.pdf_point_a),
        "pdf_point_b": point_to_dict(calibration.pdf_point_b),
        "model_point_a": point_to_dict(calibration.model_point_a),
        "model_point_b": point_to_dict(calibration.model_point_b),
        "known_distance": calibration.known_distance,
    }


def calibration_from_dict(data: dict) -> PDFCalibration:
    return PDFCalibration(
        pdf_point_a=point_from_dict(data["pdf_point_a"]),
        pdf_point_b=point_from_dict(data["pdf_point_b"]),
        model_point_a=point_from_dict(data["model_point_a"]),
        model_point_b=point_from_dict(data["model_point_b"]),
        known_distance=float(data["known_distance"]),
    )


def linked_pdf_to_dict(linked_pdf: LinkedPDF) -> dict:
    return {
        "id": linked_pdf.id,
        "file_path": linked_pdf.file_path,
        "page_number": linked_pdf.page_number,
        "calibration": calibration_to_dict(linked_pdf.calibration) if linked_pdf.calibration else None,
        "opacity": linked_pdf.opacity,
        "visible": linked_pdf.visible,
        "locked": linked_pdf.locked,
    }


def linked_pdf_from_dict(data: dict) -> LinkedPDF:
    calibration = data.get("calibration")
    return LinkedPDF(
        id=data["id"],
        file_path=data.get("file_path", ""),
        page_number=int(data.get("page_number", 0)),
        calibration=calibration_from_dict(calibration) if calibration else None,
        opacity=float(data.get("opacity", 0.3)),
        visible=bool(data.get("visible", True)),
        locked=bool(data.get("locked", False)),
    )


def room_to_dict(room: Room) -> dict:
    return {
        "id": room.id,
        "room_type": room.room_type.value,
        "room_number": room.room_number,
        "walls": [wall_to_dict(wall) for wall in room.walls],
        "openings": [opening_to_dict(opening) for opening in room.openings],
        "cabinets": [cabinet_to_dict(cabinet) for cabinet in room.cabinets],
        "appliances": [appliance_to_dict(appliance) for appliance in room.appliances],
        "dimensions": [dimension_to_dict(dimension) for dimension in room.dimensions],
        "tags": [room_tag_to_dict(tag) for tag in room.tags],
        "ceiling_height": room.ceiling_height,
    }


def room_from_dict(data: dict) -> Room:
    return Room(
        id=data["id"],
        room_type=RoomType(data.get("room_type", RoomType.KITCHEN.value)),
        room_number=int(data.get("room_number", 1)),
        walls=[wall_from_dict(item) for item in data.get("walls", [])],
        openings=[opening_from_dict(item) for item in data.get("openings", [])],
        cabinets=[cabinet_from_dict(item) for item in data.get("cabinets", [])],
        appliances=[appliance_from_dict(item) for item in data.get("appliances", [])],
        dimensions=[dimension_from_dict(item) for item in data.get("dimensions", [])],
        tags=[room_tag_from_dict(item) for item in data.get("tags", [])],
        ceiling_height=float(data.get("ceiling_height", 96.0)),
    )


def viewport_to_dict(viewport: Viewport) -> dict:
    return {
        "id": viewport.id,
        "label": viewport.label,
        "crop_rect": rect_to_dict(viewport.crop_rect),
        "scale": viewport.scale,
        "scale_factor": viewport.scale_factor,
        "position_on_sheet": point_to_dict(viewport.position_on_sheet),
        "size_on_sheet": size_to_dict(viewport.size_on_sheet),
        "render_layers": list(viewport.render_layers),
        "is_active": viewport.is_active,
    }


def viewport_from_dict(data: dict) -> Viewport:
    return Viewport(
        id=data["id"],
        label=data.get("label", ""),
        crop_rect=rect_from_dict(data.get("crop_rect", {"x": 0.0, "y": 0.0, "width": 240.0, "height": 180.0})),
        scale=data.get("scale", '1/2" = 1\'-0"'),
        scale_factor=float(data.get("scale_factor", 0.5 / 12)),
        position_on_sheet=point_from_dict(data.get("position_on_sheet", {"x": 18.0, "y": 18.0})),
        size_on_sheet=size_from_dict(data.get("size_on_sheet", {"width": 720.0, "height": 540.0})),
        render_layers=list(data.get("render_layers", [])) or [
            "underlay",
            "walls",
            "openings",
            "cabinets",
            "appliances",
            "dimensions",
            "annotations",
        ],
        is_active=bool(data.get("is_active", False)),
    )


def sheet_to_dict(sheet: Sheet) -> dict:
    return {
        "id": sheet.id,
        "sheet_number": sheet.sheet_number,
        "description": sheet.description,
        "purpose": sheet.purpose.value,
        "scale": sheet.scale,
        "date": sheet.date,
        "designer": sheet.designer,
        "viewports": [viewport_to_dict(viewport) for viewport in sheet.viewports],
        "has_notes_sidebar": sheet.has_notes_sidebar,
        "notes_template": sheet.notes_template,
    }


def sheet_from_dict(data: dict) -> Sheet:
    return Sheet(
        id=data["id"],
        sheet_number=data.get("sheet_number", "A-01"),
        description=data.get("description", "DEMO KITCHEN PLAN"),
        purpose=SheetPurpose(data.get("purpose", SheetPurpose.BID.value)),
        scale=data.get("scale", '1/2" = 1\'-0"'),
        date=data.get("date", ""),
        designer=data.get("designer", "YES"),
        viewports=[viewport_from_dict(item) for item in data.get("viewports", [])],
        has_notes_sidebar=bool(data.get("has_notes_sidebar", True)),
        notes_template=data.get("notes_template", "kitchen_bid"),
    )


def model_to_dict(model: ModelSpace) -> dict:
    return {
        "rooms": [room_to_dict(room) for room in model.rooms],
        "linked_pdfs": [linked_pdf_to_dict(linked_pdf) for linked_pdf in model.linked_pdfs],
    }


def model_from_dict(data: dict) -> ModelSpace:
    return ModelSpace(
        rooms=[room_from_dict(item) for item in data.get("rooms", [])],
        linked_pdfs=[linked_pdf_from_dict(item) for item in data.get("linked_pdfs", [])],
    )


def project_to_dict(project: Project) -> dict:
    return {
        "id": project.id,
        "project_name": project.project_name,
        "address": project.address,
        "project_type": project.project_type,
        "kcd_color": project.kcd_color,
        "kcd_style": project.kcd_style,
        "drawer_type": project.drawer_type,
        "uppers_height": project.uppers_height,
        "crown_molding": project.crown_molding,
        "status": project.status,
        "model": model_to_dict(project.model),
        "sheets": [sheet_to_dict(sheet) for sheet in project.sheets],
        "date": project.date,
    }


def project_from_dict(data: dict) -> Project:
    return Project(
        id=data["id"],
        project_name=data.get("project_name", data.get("address", "")),
        address=data.get("address", ""),
        project_type=data.get("project_type", "Kitchen"),
        kcd_color=data.get("kcd_color", "OW"),
        kcd_style=data.get("kcd_style", "Oslo"),
        drawer_type=data.get("drawer_type", "slab"),
        uppers_height=int(data.get("uppers_height", 36)),
        crown_molding=data.get("crown_molding", "Flat"),
        status=data.get("status", "A1_Request"),
        model=model_from_dict(data.get("model", {})),
        sheets=[sheet_from_dict(item) for item in data.get("sheets", [])],
        date=data.get("date", ""),
    )
