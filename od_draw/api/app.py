from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from od_draw.api.schemas import CabinetPayload, CreateProjectPayload, GenerationResponse, RoomPayload
from od_draw.catalog.kcd_catalog import CATALOG, COLOR_LINES, get_prefixed_code, lookup
from od_draw.catalog.kcd_export import export_project_tsv
from od_draw.config import FRONTEND_DIR
from od_draw.engine.geometry_engine import prepare_project
from od_draw.models.cabinet import CabinetPlacement
from od_draw.models.enums import RoomType
from od_draw.models.geometry import Point2D, Wall
from od_draw.models.project import Project, Room
from od_draw.renderer.drawing_renderer import DrawingRenderer
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets
from od_draw.storage.factory import resolve_project_store
from od_draw.storage.project_store import ProjectStore
from od_draw.storage.serializer import opening_from_dict, project_to_dict, wall_from_dict

store = resolve_project_store()


def build_blank_project(payload: CreateProjectPayload) -> Project:
    project_id = payload.project_id or f"project-{uuid4().hex[:8]}"
    room = Room(
        id="room-1",
        room_type=RoomType.KITCHEN,
        room_number=1,
        label="Kitchen",
        ceiling_height=96.0,
        walls=[],
    )
    room.walls.extend(
        [
            # Clockwise 12' x 10' starter room in inches.
            Wall("room-1-w1", Point2D(0, 0), Point2D(144, 0)),
            Wall("room-1-w2", Point2D(144, 0), Point2D(144, 120)),
            Wall("room-1-w3", Point2D(144, 120), Point2D(0, 120)),
            Wall("room-1-w4", Point2D(0, 120), Point2D(0, 0)),
        ]
    )
    project = Project(
        id=project_id,
        address=payload.address,
        kcd_color=payload.kcd_color,
        kcd_style=payload.kcd_style,
        drawer_type=payload.drawer_type,
        uppers_height=payload.uppers_height,
        crown_molding=payload.crown_molding,
        designer=payload.designer,
        created_at=date.today(),
        rooms=[room],
    )
    prepare_project(project)
    build_default_sheets(project)
    return project


def get_project_or_404(project_id: str) -> Project:
    try:
        return store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def save_project(project: Project) -> Project:
    prepare_project(project)
    build_default_sheets(project)
    store.save(project)
    return project


def generate_outputs(project: Project) -> GenerationResponse:
    output_dir = store.output_dir(project.id)
    renderer = DrawingRenderer()
    pdf_path = renderer.render_project(project, output_dir)
    tsv_path = export_project_tsv(project, output_dir / f"{project.id}.tsv")
    sheet_urls = {
        sheet.sheet_number: f"/api/projects/{project.id}/preview/{sheet.sheet_number}.svg"
        for sheet in project.sheets
    }
    return GenerationResponse(
        project_id=project.id,
        pdf_url=f"/api/projects/{project.id}/download/{pdf_path.name}",
        tsv_url=f"/api/projects/{project.id}/download/{tsv_path.name}",
        sheet_urls=sheet_urls,
    )


def room_from_payload(payload: RoomPayload, existing: Room) -> Room:
    room = Room(
        id=payload.id,
        room_type=RoomType(payload.room_type),
        room_number=payload.room_number,
        label=payload.label,
        ceiling_height=payload.ceiling_height,
        walls=[wall_from_dict(item.model_dump()) for item in payload.walls],
        openings=[opening_from_dict(item.model_dump()) for item in payload.openings],
        cabinets=existing.cabinets,
        appliances=existing.appliances,
        annotations=existing.annotations,
        verified_dimensions=existing.verified_dimensions,
    )
    return room


def create_app(store_override: ProjectStore | None = None) -> FastAPI:
    global store
    store = store_override or resolve_project_store()
    app = FastAPI(title="OD Draw Local App", version="0.2.0")

    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        store.ensure_sample()
        return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/api/catalog")
    def list_catalog() -> dict:
        return {
            "colors": COLOR_LINES,
            "entries": [
                {
                    "code": entry.code,
                    "category": entry.category.value,
                    "width": entry.width,
                    "height": entry.height,
                    "depth": entry.depth,
                    "price": entry.price,
                    "notes": entry.notes,
                }
                for entry in sorted(CATALOG.values(), key=lambda item: (item.category.value, item.code))
            ],
        }

    @app.get("/api/status")
    def status() -> dict:
        return {"backend": getattr(store, "backend_name", "unknown")}

    @app.get("/api/projects")
    def list_projects() -> list[dict]:
        store.ensure_sample()
        return store.list_projects()

    @app.post("/api/projects")
    def create_project(payload: CreateProjectPayload) -> dict:
        if payload.use_sample:
            project = build_sample_project()
            if payload.project_id:
                project.id = payload.project_id
            project.address = payload.address
            project.kcd_color = payload.kcd_color
            project.kcd_style = payload.kcd_style
            project.drawer_type = payload.drawer_type
            project.uppers_height = payload.uppers_height
            project.crown_molding = payload.crown_molding
            project.designer = payload.designer
            project.created_at = date.today()
        else:
            project = build_blank_project(payload)
        save_project(project)
        return project_to_dict(project)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = save_project(get_project_or_404(project_id))
        return project_to_dict(project)

    @app.put("/api/projects/{project_id}")
    def update_project(project_id: str, payload: CreateProjectPayload) -> dict:
        project = get_project_or_404(project_id)
        project.address = payload.address
        project.kcd_color = payload.kcd_color
        project.kcd_style = payload.kcd_style
        project.drawer_type = payload.drawer_type
        project.uppers_height = payload.uppers_height
        project.crown_molding = payload.crown_molding
        project.designer = payload.designer
        save_project(project)
        return project_to_dict(project)

    @app.put("/api/projects/{project_id}/rooms/{room_id}")
    def update_room(project_id: str, room_id: str, payload: RoomPayload) -> dict:
        project = get_project_or_404(project_id)
        for index, room in enumerate(project.rooms):
            if room.id == room_id:
                project.rooms[index] = room_from_payload(payload, room)
                save_project(project)
                return project_to_dict(project)
        raise HTTPException(status_code=404, detail="Room not found")

    @app.post("/api/projects/{project_id}/cabinets")
    def add_cabinet(project_id: str, payload: CabinetPayload) -> dict:
        project = get_project_or_404(project_id)
        room = next((item for item in project.rooms if any(wall.id == payload.wall_id for wall in item.walls)), None)
        if room is None:
            raise HTTPException(status_code=400, detail="Wall not found in project")
        wall = next(wall for wall in room.walls if wall.id == payload.wall_id)
        entry = lookup(payload.kcd_code)
        full_code = payload.kcd_code
        if "-" not in full_code:
            full_code = get_prefixed_code(project.kcd_color, payload.kcd_code)
        center = wall.point_at(payload.offset_from_wall_start + entry.width / 2)
        room.cabinets.append(
            CabinetPlacement(
                id=payload.id or f"cab-{uuid4().hex[:8]}",
                kcd_code=full_code,
                catalog_entry=lookup(full_code),
                wall_id=payload.wall_id,
                offset_from_wall_start=payload.offset_from_wall_start,
                position=Point2D(center.x, center.y),
                is_upper=payload.is_upper,
                hinge_side=payload.hinge_side,
                orientation=payload.orientation,
                modifications=payload.modifications,
            )
        )
        save_project(project)
        return project_to_dict(project)

    @app.put("/api/projects/{project_id}/cabinets/{cabinet_id}")
    def update_cabinet(project_id: str, cabinet_id: str, payload: CabinetPayload) -> dict:
        project = get_project_or_404(project_id)
        for room in project.rooms:
            for cabinet in room.cabinets:
                if cabinet.id != cabinet_id:
                    continue
                wall = next((item for item in room.walls if item.id == payload.wall_id), None)
                if wall is None:
                    raise HTTPException(status_code=400, detail="Wall not found in room")
                full_code = payload.kcd_code if "-" in payload.kcd_code else get_prefixed_code(project.kcd_color, payload.kcd_code)
                entry = lookup(full_code)
                center = wall.point_at(payload.offset_from_wall_start + entry.width / 2)
                cabinet.kcd_code = full_code
                cabinet.catalog_entry = entry
                cabinet.wall_id = payload.wall_id
                cabinet.offset_from_wall_start = payload.offset_from_wall_start
                cabinet.position = Point2D(center.x, center.y)
                cabinet.is_upper = payload.is_upper
                cabinet.hinge_side = payload.hinge_side
                cabinet.orientation = payload.orientation
                cabinet.modifications = payload.modifications
                save_project(project)
                return project_to_dict(project)
        raise HTTPException(status_code=404, detail="Cabinet not found")

    @app.delete("/api/projects/{project_id}/cabinets/{cabinet_id}")
    def delete_cabinet(project_id: str, cabinet_id: str) -> dict:
        project = get_project_or_404(project_id)
        for room in project.rooms:
            original = len(room.cabinets)
            room.cabinets = [cabinet for cabinet in room.cabinets if cabinet.id != cabinet_id]
            if len(room.cabinets) != original:
                save_project(project)
                return project_to_dict(project)
        raise HTTPException(status_code=404, detail="Cabinet not found")

    @app.post("/api/projects/{project_id}/generate-cd", response_model=GenerationResponse)
    def generate_cd(project_id: str) -> GenerationResponse:
        project = save_project(get_project_or_404(project_id))
        return generate_outputs(project)

    @app.post("/api/projects/{project_id}/generate-bid", response_model=GenerationResponse)
    def generate_bid(project_id: str) -> GenerationResponse:
        project = save_project(get_project_or_404(project_id))
        return generate_outputs(project)

    @app.get("/api/projects/{project_id}/preview/{sheet_number}.svg")
    def preview_sheet(project_id: str, sheet_number: str):
        project = save_project(get_project_or_404(project_id))
        generate_outputs(project)
        path = store.output_dir(project_id) / f"{sheet_number}.svg"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Sheet not found")
        return FileResponse(path, media_type="image/svg+xml")

    @app.get("/api/projects/{project_id}/download/{filename}")
    def download_output(project_id: str, filename: str):
        project = save_project(get_project_or_404(project_id))
        generate_outputs(project)
        path = store.output_dir(project_id) / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        media_type = "application/octet-stream"
        if path.suffix == ".pdf":
            media_type = "application/pdf"
        elif path.suffix == ".tsv":
            media_type = "text/tab-separated-values"
        elif path.suffix == ".svg":
            media_type = "image/svg+xml"
        return FileResponse(path, media_type=media_type, filename=filename)

    @app.get("/api/projects/{project_id}/export-tsv")
    def export_tsv(project_id: str):
        project = save_project(get_project_or_404(project_id))
        generate_outputs(project)
        filename = f"{project.id}.tsv"
        path = store.output_dir(project_id) / filename
        return FileResponse(path, media_type="text/tab-separated-values", filename=filename)

    return app
