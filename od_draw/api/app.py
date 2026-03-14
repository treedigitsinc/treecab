from __future__ import annotations

import base64
import hmac
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from od_draw.api.schemas import CabinetPayload, CreateProjectPayload, GenerationResponse, RoomPayload
from od_draw.api.master_schemas import (
    CalibrationPayload,
    DimensionVerificationPayload,
    MasterCabinetMovePayload,
    MasterCabinetPlacePayload,
    MasterGenerationResponse,
    MasterProjectCreatePayload,
    MasterSheetCreatePayload,
    MasterViewportPayload,
    MasterWallCreatePayload,
)
from od_draw.catalog.kcd_catalog import CATALOG, COLOR_LINES, get_prefixed_code, lookup
from od_draw.catalog.kcd_export import export_project_tsv
from od_draw.catalog.master_catalog import CATALOG as MASTER_CATALOG
from od_draw.catalog.master_catalog import COLOR_LINES as MASTER_COLOR_LINES
from od_draw.catalog.master_catalog import get_full_code, is_valid_combo, lookup as lookup_master
from od_draw.catalog.master_export import export_project_tsv as export_master_project_tsv
from od_draw.config import (
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    AUTH_COOKIE_VALUE,
    FRONTEND_INDEX_FILE,
    FRONTEND_STATIC_DIR,
    SITE_PASSWORD,
)
from od_draw.master_pipeline import MasterGenerationPipeline
from od_draw.engine.geometry_engine import prepare_project
from od_draw.models.cabinet import CabinetPlacement
from od_draw.models.enums import RoomType
from od_draw.models.geometry import Point2D, Wall
from od_draw.models.master import (
    CabinetInstance,
    LinkedPDF,
    ModelSpace,
    PDFCalibration,
    Point2D as MasterPoint2D,
    Project as MasterProject,
    Rect,
    Room as MasterRoom,
    RoomType as MasterRoomType,
    Sheet as MasterSheet,
    SheetPurpose,
    Size2D,
    Viewport,
    Wall as MasterWall,
    WallStatus,
)
from od_draw.models.project import Project, Room
from od_draw.renderer.pdf_linker import PDFLinker
from od_draw.renderer.viewport_renderer import SCALES
from od_draw.renderer.drawing_renderer import DrawingRenderer
from od_draw.sample_master_project import build_sample_master_project
from od_draw.sample_project import build_sample_project
from od_draw.sheets.sheet_composer import build_default_sheets
from od_draw.storage.factory import resolve_project_store
from od_draw.storage.master_project_store import MasterProjectStore
from od_draw.storage.master_serializer import (
    linked_pdf_to_dict,
    project_to_dict as master_project_to_dict,
)
from od_draw.storage.project_store import ProjectStore
from od_draw.storage.serializer import (
    opening_from_dict,
    project_to_dict as legacy_project_to_dict,
    wall_from_dict,
)

store = resolve_project_store()
master_store = MasterProjectStore()

LOGIN_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>treecab access</title>
    <style>
      :root {
        --bg: #ede9df;
        --card: rgba(255, 255, 255, 0.9);
        --line: rgba(36, 31, 23, 0.14);
        --ink: #1f1b15;
        --muted: #665f55;
        --accent: #1f1b15;
        --danger: #9f2d2d;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
        color: var(--ink);
        background:
          radial-gradient(circle at top, rgba(79, 93, 64, 0.18), transparent 40%),
          linear-gradient(135deg, #ddd5c4 0%, #f3efe7 48%, #e7dece 100%);
        font-family: Georgia, "Times New Roman", serif;
      }
      .card {
        width: min(100%, 420px);
        padding: 32px;
        border: 1px solid var(--line);
        border-radius: 24px;
        background: var(--card);
        box-shadow: 0 24px 80px rgba(31, 27, 21, 0.14);
        backdrop-filter: blur(18px);
      }
      .eyebrow {
        margin: 0 0 10px;
        font: 600 11px/1.2 "Segoe UI", sans-serif;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--muted);
      }
      h1 {
        margin: 0 0 10px;
        font-size: clamp(34px, 8vw, 48px);
      }
      p {
        margin: 0 0 24px;
        color: var(--muted);
        font: 400 16px/1.6 "Segoe UI", sans-serif;
      }
      form { display: grid; gap: 14px; }
      label {
        display: grid;
        gap: 8px;
        font: 600 12px/1.2 "Segoe UI", sans-serif;
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }
      input, button {
        width: 100%;
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid var(--line);
        font: 500 16px/1.2 "Segoe UI", sans-serif;
      }
      input { background: rgba(255, 255, 255, 0.92); }
      button {
        border-color: transparent;
        background: var(--accent);
        color: white;
        cursor: pointer;
      }
      .status {
        min-height: 24px;
        margin: 0;
        color: var(--danger);
        font: 500 14px/1.4 "Segoe UI", sans-serif;
      }
    </style>
  </head>
  <body>
    <main class="card">
      <p class="eyebrow">Protected Workspace</p>
      <h1>treecab</h1>
      <p>Enter the site password to load the editor and unlock API access.</p>
      <form id="login-form">
        <label>
          Password
          <input id="password" name="password" type="password" autocomplete="current-password" required />
        </label>
        <button type="submit">Enter Site</button>
        <p id="status" class="status"></p>
      </form>
    </main>
    <script>
      const form = document.getElementById("login-form");
      const password = document.getElementById("password");
      const status = document.getElementById("status");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        status.textContent = "";
        const response = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: password.value }),
        });
        if (response.ok) {
          window.location.replace("/");
          return;
        }
        const payload = await response.json().catch(() => ({ detail: "Access denied" }));
        status.textContent = payload.detail || "Access denied";
        password.select();
      });
    </script>
  </body>
</html>
"""


def scope_to_room_defaults(scope: str) -> tuple[RoomType, str]:
    normalized = scope.strip().lower()
    if "laundry" in normalized:
        return RoomType.LAUNDRY, "Laundry"
    if "main bath" in normalized:
        return RoomType.MAIN_BATH, "Main Bath"
    if "bath" in normalized:
        return RoomType.BATH, "Bath"
    if "dining" in normalized:
        return RoomType.DINING, "Dining"
    return RoomType.KITCHEN, "Kitchen"


def build_blank_project(payload: CreateProjectPayload) -> Project:
    project_id = payload.project_id or f"project-{uuid4().hex[:8]}"
    room_type, room_label = scope_to_room_defaults(payload.project_scope)
    room = Room(
        id="room-1",
        room_type=room_type,
        room_number=1,
        label=room_label,
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
        project_scope=payload.project_scope,
        rooms=[room],
    )
    prepare_project(project)
    build_default_sheets(project)
    return project


def today_iso() -> str:
    return date.today().isoformat()


def build_blank_master_project(payload: MasterProjectCreatePayload) -> MasterProject:
    project_id = payload.project_id or f"master-{uuid4().hex[:8]}"
    room = MasterRoom(
        id="room-1",
        room_type=MasterRoomType.KITCHEN,
        room_number=1,
        ceiling_height=96.0,
        walls=[
            MasterWall("room-1-w1", MasterPoint2D(0.0, 0.0), MasterPoint2D(144.0, 0.0)),
            MasterWall("room-1-w2", MasterPoint2D(144.0, 0.0), MasterPoint2D(144.0, 120.0)),
            MasterWall("room-1-w3", MasterPoint2D(144.0, 120.0), MasterPoint2D(0.0, 120.0)),
            MasterWall("room-1-w4", MasterPoint2D(0.0, 120.0), MasterPoint2D(0.0, 0.0)),
        ],
    )
    viewport = Viewport(
        label="1  KITCHEN PLAN",
        crop_rect=Rect(-12.0, -12.0, 168.0, 144.0),
        scale='1/2" = 1\'-0"',
        scale_factor=0.5 / 12,
        position_on_sheet=MasterPoint2D(48.0, 88.0),
        size_on_sheet=Size2D(720.0, 520.0),
    )
    sheet = MasterSheet(
        sheet_number="A-01",
        description="KITCHEN PLAN",
        purpose=SheetPurpose.BID,
        scale=viewport.scale,
        date=payload.date or today_iso(),
        designer="YES",
        viewports=[viewport],
    )
    return MasterProject(
        id=project_id,
        address=payload.address,
        project_type=payload.project_type,
        kcd_color=payload.kcd_color,
        kcd_style=payload.kcd_style,
        drawer_type=payload.drawer_type,
        uppers_height=payload.uppers_height,
        crown_molding=payload.crown_molding,
        status=payload.status,
        model=ModelSpace(rooms=[room]),
        sheets=[sheet],
        date=payload.date or today_iso(),
    )


def get_project_or_404(project_id: str) -> Project:
    try:
        return store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc


def get_master_project_or_404(project_id: str) -> MasterProject:
    try:
        return master_store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Master project not found") from exc


def save_project(project: Project) -> Project:
    prepare_project(project)
    build_default_sheets(project)
    store.save(project)
    return project


def save_master_project(project: MasterProject) -> MasterProject:
    master_store.save(project)
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


def generate_master_outputs(project: MasterProject, drawing_type: str) -> MasterGenerationResponse:
    output_dir = master_store.output_dir(project.id)
    artifacts = MasterGenerationPipeline().generate(project, output_dir, drawing_type)
    tsv_path = export_master_project_tsv(project, output_dir / f"{project.id}.tsv")

    warnings: list[str] = []
    if artifacts.merged_pdf_path is None:
        warnings.append("Typst is not installed in PATH; generated viewport SVG and Typst source artifacts only.")

    viewport_svg_urls: dict[str, str] = {}
    for sheet in project.sheets:
        for viewport in sheet.viewports:
            filename = artifacts.viewport_svg_paths[viewport.id].name
            viewport_svg_urls[viewport.id] = f"/api/master/projects/{project.id}/download/{filename}"

    sheet_typst_urls = {
        sheet_number: f"/api/master/projects/{project.id}/download/{path.name}"
        for sheet_number, path in artifacts.sheet_typst_paths.items()
    }
    sheet_pdf_urls = {
        sheet_number: f"/api/master/projects/{project.id}/download/{path.name}"
        for sheet_number, path in artifacts.sheet_pdf_paths.items()
    }

    return MasterGenerationResponse(
        project_id=project.id,
        drawing_type=drawing_type,
        pdf_url=(
            f"/api/master/projects/{project.id}/download/{artifacts.merged_pdf_path.name}"
            if artifacts.merged_pdf_path is not None
            else None
        ),
        tsv_url=f"/api/master/projects/{project.id}/download/{tsv_path.name}",
        sheet_pdf_urls=sheet_pdf_urls,
        sheet_typst_urls=sheet_typst_urls,
        viewport_svg_urls=viewport_svg_urls,
        warnings=warnings,
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


def normalize_master_scale(scale: str, scale_factor: float | None) -> float:
    if scale_factor is not None:
        return scale_factor
    if scale not in SCALES:
        raise HTTPException(status_code=400, detail=f"Unsupported scale: {scale}")
    return SCALES[scale]


def resolve_master_cabinet(project: MasterProject, payload: MasterCabinetPlacePayload) -> tuple[str, str, str]:
    supplied_prefix = payload.color_prefix or project.kcd_color
    if "-" in payload.kcd_code:
        prefix, base_code = payload.kcd_code.split("-", 1)
        full_code = payload.kcd_code
    else:
        prefix = supplied_prefix
        base_code = payload.kcd_code
        full_code = get_full_code(prefix, base_code)
    if lookup_master(base_code) is None:
        raise HTTPException(status_code=400, detail=f"Unknown KCD code: {base_code}")
    if not is_valid_combo(prefix, base_code):
        raise HTTPException(status_code=400, detail=f"{prefix} is not valid for {base_code}")
    return prefix, base_code, full_code


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    try:
        return [to_jsonable(item) for item in value]
    except TypeError:
        return str(value)


def is_authorized(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME, "")
    return hmac.compare_digest(token, AUTH_COOKIE_VALUE)


def create_app(
    store_override: ProjectStore | None = None,
    master_store_override: MasterProjectStore | None = None,
) -> FastAPI:
    global store, master_store
    store = store_override or resolve_project_store()
    master_store = master_store_override or MasterProjectStore()
    app = FastAPI(title="OD Draw Local App", version="0.2.0")
    pdf_linker = PDFLinker()

    @app.middleware("http")
    async def require_site_password(request: Request, call_next):
        path = request.url.path
        if path == "/auth/login":
            return await call_next(request)
        if is_authorized(request):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return HTMLResponse(LOGIN_PAGE, status_code=401)

    frontend_available = FRONTEND_INDEX_FILE.exists()
    if frontend_available:
        app.mount("/frontend", StaticFiles(directory=str(FRONTEND_STATIC_DIR)), name="frontend")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        store.ensure_sample()
        if frontend_available:
            return FRONTEND_INDEX_FILE.read_text(encoding="utf-8")
        return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>OD Draw</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 40px; color: #141414; background: #f6f5f1; }
      .card { max-width: 720px; background: white; border: 1px solid #d8d6cf; border-radius: 12px; padding: 24px; }
      a { color: #141414; }
      code { background: #f1f1ed; padding: 2px 6px; border-radius: 6px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>OD Draw</h1>
      <p>The API is running, but the local static editor bundle is not present in this deployment package.</p>
      <p>Check <a href="/api/status">/api/status</a> and <a href="/api/projects">/api/projects</a>.</p>
    </div>
  </body>
</html>
"""

    @app.post("/auth/login")
    async def login(request: Request) -> Response:
        payload = await request.json()
        password = str(payload.get("password", ""))
        if not hmac.compare_digest(password, SITE_PASSWORD):
            return JSONResponse({"detail": "Incorrect password"}, status_code=401)
        response = JSONResponse({"ok": True})
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=AUTH_COOKIE_VALUE,
            httponly=True,
            samesite="lax",
            secure=AUTH_COOKIE_SECURE,
            max_age=60 * 60 * 24 * 30,
        )
        return response

    @app.post("/auth/logout")
    def logout() -> Response:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(AUTH_COOKIE_NAME)
        return response

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
            project.project_scope = payload.project_scope
            project.created_at = date.today()
        else:
            project = build_blank_project(payload)
        save_project(project)
        return legacy_project_to_dict(project)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict:
        project = save_project(get_project_or_404(project_id))
        return legacy_project_to_dict(project)

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
        project.project_scope = payload.project_scope
        save_project(project)
        return legacy_project_to_dict(project)

    @app.put("/api/projects/{project_id}/rooms/{room_id}")
    def update_room(project_id: str, room_id: str, payload: RoomPayload) -> dict:
        project = get_project_or_404(project_id)
        for index, room in enumerate(project.rooms):
            if room.id == room_id:
                project.rooms[index] = room_from_payload(payload, room)
                save_project(project)
                return legacy_project_to_dict(project)
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
        return legacy_project_to_dict(project)

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
                return legacy_project_to_dict(project)
        raise HTTPException(status_code=404, detail="Cabinet not found")

    @app.delete("/api/projects/{project_id}/cabinets/{cabinet_id}")
    def delete_cabinet(project_id: str, cabinet_id: str) -> dict:
        project = get_project_or_404(project_id)
        for room in project.rooms:
            original = len(room.cabinets)
            room.cabinets = [cabinet for cabinet in room.cabinets if cabinet.id != cabinet_id]
            if len(room.cabinets) != original:
                save_project(project)
                return legacy_project_to_dict(project)
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

    @app.get("/api/master/catalog")
    def list_master_catalog() -> dict:
        return {
            "colors": MASTER_COLOR_LINES,
            "entries": [
                {
                    "code": entry.code,
                    "category": entry.category,
                    "width": entry.width,
                    "height": entry.height,
                    "depth": entry.depth,
                    "notes": entry.notes,
                }
                for entry in sorted(MASTER_CATALOG.values(), key=lambda item: (item.category, item.code))
            ],
        }

    @app.get("/api/master/projects")
    def list_master_projects() -> list[dict]:
        master_store.ensure_sample()
        return master_store.list_projects()

    @app.post("/api/master/projects")
    def create_master_project(payload: MasterProjectCreatePayload) -> dict:
        if payload.use_sample:
            project = build_sample_master_project()
            if payload.project_id:
                project.id = payload.project_id
            project.address = payload.address
            project.project_type = payload.project_type
            project.kcd_color = payload.kcd_color
            project.kcd_style = payload.kcd_style
            project.drawer_type = payload.drawer_type
            project.uppers_height = payload.uppers_height
            project.crown_molding = payload.crown_molding
            project.status = payload.status
            project.date = payload.date or today_iso()
        else:
            project = build_blank_master_project(payload)
        save_master_project(project)
        return master_project_to_dict(project)

    @app.get("/api/master/projects/{project_id}")
    def get_master_project(project_id: str) -> dict:
        project = save_master_project(get_master_project_or_404(project_id))
        return master_project_to_dict(project)

    @app.post("/api/master/projects/{project_id}/link-pdf")
    async def link_master_pdf(project_id: str, file: UploadFile = File(...), page: int = 0) -> dict:
        project = get_master_project_or_404(project_id)
        suffix = Path(file.filename or "linked.pdf").suffix.lower()
        if suffix != ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
        pdf_id = f"pdf-{uuid4().hex[:8]}"
        destination = master_store.asset_dir(project_id) / f"{pdf_id}{suffix}"
        destination.write_bytes(await file.read())

        linked_pdf = LinkedPDF(id=pdf_id, file_path=str(destination), page_number=page)
        project.model.linked_pdfs.append(linked_pdf)
        save_master_project(project)

        png_bytes, pixel_width, pixel_height = pdf_linker.rasterize_page(str(destination), page)
        return {
            "linked_pdf": linked_pdf_to_dict(linked_pdf),
            "preview_png_base64": base64.b64encode(png_bytes).decode("ascii"),
            "pixel_width": pixel_width,
            "pixel_height": pixel_height,
        }

    @app.post("/api/master/projects/{project_id}/calibrate-pdf/{pdf_id}")
    def calibrate_master_pdf(project_id: str, pdf_id: str, payload: CalibrationPayload) -> dict:
        project = get_master_project_or_404(project_id)
        linked_pdf = next((item for item in project.model.linked_pdfs if item.id == pdf_id), None)
        if linked_pdf is None:
            raise HTTPException(status_code=404, detail="Linked PDF not found")
        linked_pdf.calibration = PDFCalibration(
            pdf_point_a=MasterPoint2D(payload.pdf_point_a.x, payload.pdf_point_a.y),
            pdf_point_b=MasterPoint2D(payload.pdf_point_b.x, payload.pdf_point_b.y),
            model_point_a=MasterPoint2D(payload.model_point_a.x, payload.model_point_a.y),
            model_point_b=MasterPoint2D(payload.model_point_b.x, payload.model_point_b.y),
            known_distance=payload.known_distance,
        )
        save_master_project(project)
        return linked_pdf_to_dict(linked_pdf)

    @app.post("/api/master/projects/{project_id}/extract-vectors/{pdf_id}")
    def extract_master_vectors(project_id: str, pdf_id: str) -> dict:
        project = get_master_project_or_404(project_id)
        linked_pdf = next((item for item in project.model.linked_pdfs if item.id == pdf_id), None)
        if linked_pdf is None:
            raise HTTPException(status_code=404, detail="Linked PDF not found")
        return {"paths": to_jsonable(pdf_linker.extract_vectors(linked_pdf.file_path, linked_pdf.page_number))}

    @app.post("/api/master/projects/{project_id}/rooms/{room_id}/walls")
    def add_master_wall(project_id: str, room_id: str, payload: MasterWallCreatePayload) -> dict:
        project = get_master_project_or_404(project_id)
        room = next((item for item in project.model.rooms if item.id == room_id), None)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        room.walls.append(
            MasterWall(
                id=payload.id or f"wall-{uuid4().hex[:8]}",
                start=MasterPoint2D(payload.start.x, payload.start.y),
                end=MasterPoint2D(payload.end.x, payload.end.y),
                thickness=payload.thickness,
                status=WallStatus(payload.status),
            )
        )
        save_master_project(project)
        return master_project_to_dict(project)

    @app.post("/api/master/projects/{project_id}/rooms/{room_id}/cabinets")
    def place_master_cabinet(project_id: str, room_id: str, payload: MasterCabinetPlacePayload) -> dict:
        project = get_master_project_or_404(project_id)
        room = next((item for item in project.model.rooms if item.id == room_id), None)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        prefix, base_code, full_code = resolve_master_cabinet(project, payload)
        room.cabinets.append(
            CabinetInstance(
                id=payload.id or f"cab-{uuid4().hex[:8]}",
                kcd_code=full_code,
                base_code=base_code,
                color_prefix=prefix,
                wall_id=payload.wall_id,
                position=MasterPoint2D(payload.position.x, payload.position.y),
                is_upper=payload.is_upper,
                hinge_side=payload.hinge_side,
                modifications=payload.modifications,
            )
        )
        save_master_project(project)
        return master_project_to_dict(project)

    @app.put("/api/master/projects/{project_id}/rooms/{room_id}/cabinets/{cabinet_id}")
    def move_master_cabinet(
        project_id: str,
        room_id: str,
        cabinet_id: str,
        payload: MasterCabinetMovePayload,
    ) -> dict:
        project = get_master_project_or_404(project_id)
        room = next((item for item in project.model.rooms if item.id == room_id), None)
        if room is None:
            raise HTTPException(status_code=404, detail="Room not found")
        cabinet = next((item for item in room.cabinets if item.id == cabinet_id), None)
        if cabinet is None:
            raise HTTPException(status_code=404, detail="Cabinet not found")
        cabinet.position = MasterPoint2D(payload.position.x, payload.position.y)
        cabinet.wall_id = payload.wall_id
        cabinet.hinge_side = payload.hinge_side
        cabinet.modifications = payload.modifications
        save_master_project(project)
        return master_project_to_dict(project)

    @app.post("/api/master/projects/{project_id}/sheets")
    def create_master_sheet(project_id: str, payload: MasterSheetCreatePayload) -> dict:
        project = get_master_project_or_404(project_id)
        project.sheets.append(
            MasterSheet(
                id=f"sheet-{uuid4().hex[:8]}",
                sheet_number=payload.sheet_number,
                description=payload.description,
                purpose=SheetPurpose(payload.purpose),
                scale=payload.scale,
                date=payload.date or project.date or today_iso(),
                designer=payload.designer,
                has_notes_sidebar=payload.has_notes_sidebar,
                notes_template=payload.notes_template,
            )
        )
        save_master_project(project)
        return master_project_to_dict(project)

    @app.post("/api/master/projects/{project_id}/sheets/{sheet_id}/viewports")
    def add_master_viewport(project_id: str, sheet_id: str, payload: MasterViewportPayload) -> dict:
        project = get_master_project_or_404(project_id)
        sheet = next((item for item in project.sheets if item.id == sheet_id), None)
        if sheet is None:
            raise HTTPException(status_code=404, detail="Sheet not found")
        viewport = Viewport(
            id=payload.id or f"vp-{uuid4().hex[:8]}",
            label=payload.label,
            crop_rect=Rect(payload.crop_rect.x, payload.crop_rect.y, payload.crop_rect.width, payload.crop_rect.height),
            scale=payload.scale,
            scale_factor=normalize_master_scale(payload.scale, payload.scale_factor),
            position_on_sheet=MasterPoint2D(payload.position_on_sheet.x, payload.position_on_sheet.y),
            size_on_sheet=Size2D(payload.size_on_sheet.width, payload.size_on_sheet.height),
            render_layers=payload.render_layers,
            is_active=payload.is_active,
        )
        sheet.viewports.append(viewport)
        sheet.scale = payload.scale
        save_master_project(project)
        return master_project_to_dict(project)

    @app.put("/api/master/projects/{project_id}/sheets/{sheet_id}/viewports/{viewport_id}")
    def update_master_viewport(project_id: str, sheet_id: str, viewport_id: str, payload: MasterViewportPayload) -> dict:
        project = get_master_project_or_404(project_id)
        sheet = next((item for item in project.sheets if item.id == sheet_id), None)
        if sheet is None:
            raise HTTPException(status_code=404, detail="Sheet not found")
        for index, viewport in enumerate(sheet.viewports):
            if viewport.id != viewport_id:
                continue
            sheet.viewports[index] = Viewport(
                id=viewport.id,
                label=payload.label,
                crop_rect=Rect(payload.crop_rect.x, payload.crop_rect.y, payload.crop_rect.width, payload.crop_rect.height),
                scale=payload.scale,
                scale_factor=normalize_master_scale(payload.scale, payload.scale_factor),
                position_on_sheet=MasterPoint2D(payload.position_on_sheet.x, payload.position_on_sheet.y),
                size_on_sheet=Size2D(payload.size_on_sheet.width, payload.size_on_sheet.height),
                render_layers=payload.render_layers,
                is_active=payload.is_active,
            )
            sheet.scale = payload.scale
            save_master_project(project)
            return master_project_to_dict(project)
        raise HTTPException(status_code=404, detail="Viewport not found")

    @app.put("/api/master/projects/{project_id}/verify-dimensions")
    def verify_master_dimensions(project_id: str, payload: list[DimensionVerificationPayload]) -> dict:
        project = get_master_project_or_404(project_id)
        values = {item.id: item.value for item in payload}
        for room in project.model.rooms:
            for dimension in room.dimensions:
                if dimension.id in values:
                    dimension.value = values[dimension.id]
        save_master_project(project)
        return master_project_to_dict(project)

    @app.post("/api/master/projects/{project_id}/generate-bid", response_model=MasterGenerationResponse)
    def generate_master_bid(project_id: str) -> MasterGenerationResponse:
        project = save_master_project(get_master_project_or_404(project_id))
        return generate_master_outputs(project, "bid")

    @app.post("/api/master/projects/{project_id}/generate-construction", response_model=MasterGenerationResponse)
    def generate_master_construction(project_id: str) -> MasterGenerationResponse:
        project = save_master_project(get_master_project_or_404(project_id))
        return generate_master_outputs(project, "construction")

    @app.get("/api/master/projects/{project_id}/preview/{sheet_number}")
    def preview_master_sheet(project_id: str, sheet_number: str):
        project = save_master_project(get_master_project_or_404(project_id))
        artifacts = MasterGenerationPipeline().generate(project, master_store.output_dir(project_id), "preview")
        if not artifacts.sheet_pdf_paths:
            raise HTTPException(status_code=503, detail="Typst is not installed in PATH")
        path = artifacts.sheet_pdf_paths.get(sheet_number)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="Sheet not found")
        return FileResponse(path, media_type="application/pdf", filename=path.name)

    @app.get("/api/master/projects/{project_id}/download/{filename}")
    def download_master_output(project_id: str, filename: str):
        get_master_project_or_404(project_id)
        path = master_store.output_dir(project_id) / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        media_type = "application/octet-stream"
        if path.suffix == ".pdf":
            media_type = "application/pdf"
        elif path.suffix == ".svg":
            media_type = "image/svg+xml"
        elif path.suffix == ".typ":
            media_type = "text/plain; charset=utf-8"
        elif path.suffix == ".tsv":
            media_type = "text/tab-separated-values"
        return FileResponse(path, media_type=media_type, filename=filename)

    @app.get("/api/master/projects/{project_id}/export-tsv")
    def export_master_tsv(project_id: str):
        project = save_master_project(get_master_project_or_404(project_id))
        path = export_master_project_tsv(project, master_store.output_dir(project_id) / f"{project.id}.tsv")
        return FileResponse(path, media_type="text/tab-separated-values", filename=path.name)

    return app
