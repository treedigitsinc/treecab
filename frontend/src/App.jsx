import { useEffect, useRef, useState } from "react";
import { Circle, Group, Layer, Line, Rect, Stage, Text } from "react-konva";

import {
  addCabinet,
  createProject,
  deleteCabinet,
  generateDrawingSet,
  loadCatalog,
  loadProject,
  loadProjects,
  loadStatus,
  saveRoom,
  updateCabinet,
  updateProject,
} from "./api";
import {
  cabinetScreenRect,
  clamp,
  createView,
  getBaseCode,
  nearestWall,
  pointDistance,
  openingScreenGeometry,
  projectPointToWall,
  roomBounds,
  sampleArcPoints,
  snapWallPoint,
  wallLength,
  wallPolygon,
} from "./geometry";

const DEFAULT_METADATA = {
  address: "New Project",
  project_scope: "Kitchen",
  kcd_color: "BW",
  kcd_style: "Brooklyn White",
  drawer_type: "5-piece",
  uppers_height: 36,
  crown_molding: "Flat",
  designer: "LOCAL",
};

const SCOPE_OPTIONS = ["Kitchen", "Laundry", "Main Bath", "Bath", "Dining", "Kitchen + Baths", "Full Home"];
const MIN_CANVAS_ZOOM = 0.65;
const MAX_CANVAS_ZOOM = 5;
const ZOOM_STEP = 1.14;
const SNAP_INCREMENT = 0.5;
const WALL_DRAFT_MIN_LENGTH = 12;
const OPENING_REHOST_DISTANCE = 18;

function buildRoomPayload(room) {
  return {
    id: room.id,
    label: room.label,
    room_type: room.room_type,
    room_number: room.room_number,
    ceiling_height: Number(room.ceiling_height),
    walls: room.walls.map((wall) => ({
      id: wall.id,
      start: { x: Number(wall.start.x), y: Number(wall.start.y) },
      end: { x: Number(wall.end.x), y: Number(wall.end.y) },
      thickness: Number(wall.thickness || 4.5),
      status: wall.status,
    })),
    openings: room.openings.map((opening) => ({
      id: opening.id,
      wall_id: opening.wall_id,
      kind: opening.kind,
      position_along_wall: Number(opening.position_along_wall),
      width: Number(opening.width),
      height: Number(opening.height || 0),
      sill_height: Number(opening.sill_height || 0),
      trim_width: Number(opening.trim_width || 3.5),
      verify_in_field: Boolean(opening.verify_in_field),
    })),
  };
}

function clampOpeningPlacement(width, wall, offset) {
  return clamp(offset, 0, Math.max(wallLength(wall) - width, 0));
}

function resolveOpeningPlacement(opening, worldPoint, room) {
  const nearest = nearestWall(worldPoint, room);
  const currentWall = room.walls.find((wall) => wall.id === opening.wall_id);
  if (!nearest?.wall && !currentWall) return null;

  if (nearest?.wall && nearest.distance <= OPENING_REHOST_DISTANCE) {
    return {
      wall_id: nearest.wall.id,
      position_along_wall: clampOpeningPlacement(opening.width, nearest.wall, nearest.offset - opening.width / 2),
    };
  }

  if (!currentWall) {
    return {
      wall_id: nearest.wall.id,
      position_along_wall: clampOpeningPlacement(opening.width, nearest.wall, nearest.offset - opening.width / 2),
    };
  }

  const projected = projectPointToWall(worldPoint, currentWall);
  return {
    wall_id: currentWall.id,
    position_along_wall: clampOpeningPlacement(opening.width, currentWall, projected.offset - opening.width / 2),
  };
}

function MetadataForm({ project, onSave }) {
  const [form, setForm] = useState({
    address: project.address,
    project_scope: project.project_scope || "Kitchen",
    kcd_color: project.kcd_color,
    kcd_style: project.kcd_style,
    drawer_type: project.drawer_type,
    uppers_height: project.uppers_height,
    crown_molding: project.crown_molding,
    designer: project.designer,
  });

  useEffect(() => {
    setForm({
      address: project.address,
      project_scope: project.project_scope || "Kitchen",
      kcd_color: project.kcd_color,
      kcd_style: project.kcd_style,
      drawer_type: project.drawer_type,
      uppers_height: project.uppers_height,
      crown_molding: project.crown_molding,
      designer: project.designer,
    });
  }, [project]);

  return (
    <form
      className="stack"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(form);
      }}
    >
      <label>
        Project Name
        <input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
      </label>
      <label>
        Scope
        <select value={form.project_scope} onChange={(event) => setForm({ ...form, project_scope: event.target.value })}>
          {SCOPE_OPTIONS.map((scope) => (
            <option key={scope} value={scope}>
              {scope}
            </option>
          ))}
        </select>
      </label>
      <div className="two-up">
        <label>
          KCD Color
          <input value={form.kcd_color} onChange={(event) => setForm({ ...form, kcd_color: event.target.value })} />
        </label>
        <label>
          KCD Style
          <input value={form.kcd_style} onChange={(event) => setForm({ ...form, kcd_style: event.target.value })} />
        </label>
      </div>
      <div className="two-up">
        <label>
          Drawer Type
          <input value={form.drawer_type} onChange={(event) => setForm({ ...form, drawer_type: event.target.value })} />
        </label>
        <label>
          Uppers Height
          <input
            type="number"
            value={form.uppers_height}
            onChange={(event) => setForm({ ...form, uppers_height: Number(event.target.value) })}
          />
        </label>
      </div>
      <div className="two-up">
        <label>
          Crown Molding
          <input value={form.crown_molding} onChange={(event) => setForm({ ...form, crown_molding: event.target.value })} />
        </label>
        <label>
          Designer
          <input value={form.designer} onChange={(event) => setForm({ ...form, designer: event.target.value })} />
        </label>
      </div>
      <button type="submit">Save Project Details</button>
    </form>
  );
}

function SetupScreen({ projects, existingProjectId, onExistingProjectChange, onOpenExisting, setupForm, setSetupForm, onCreate }) {
  return (
    <section className="setup-shell">
      <div className="setup-card hero-setup">
        <p className="eyebrow">Canvas Workflow</p>
        <h2>Start with the project basics.</h2>
        <p className="setup-text">
          Set the project name and scope first. Once that is saved, the canvas opens and all placement actions happen
          from right-click menus on the plan.
        </p>
        <form
          className="setup-form"
          onSubmit={(event) => {
            event.preventDefault();
            onCreate();
          }}
        >
          <label>
            Project Name
            <input
              value={setupForm.projectName}
              onChange={(event) => setSetupForm((current) => ({ ...current, projectName: event.target.value }))}
              placeholder="Kitchen Remodel - Harbour View"
            />
          </label>
          <label>
            Scope
            <select
              value={setupForm.projectScope}
              onChange={(event) => setSetupForm((current) => ({ ...current, projectScope: event.target.value }))}
            >
              {SCOPE_OPTIONS.map((scope) => (
                <option key={scope} value={scope}>
                  {scope}
                </option>
              ))}
            </select>
          </label>
          <button type="submit">Create Project & Open Canvas</button>
        </form>
      </div>

      <div className="setup-card">
        <div className="section-head">
          <h2>Open Existing</h2>
          <span className="hint">{projects.length} saved project{projects.length === 1 ? "" : "s"}</span>
        </div>
        {projects.length ? (
          <div className="stack">
            <select value={existingProjectId} onChange={(event) => onExistingProjectChange(event.target.value)}>
              {projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.address} ({item.project_scope || "Kitchen"})
                </option>
              ))}
            </select>
            <button type="button" className="ghost" onClick={onOpenExisting}>
              Open Selected Project
            </button>
          </div>
        ) : (
          <p className="empty">No existing project found yet.</p>
        )}
      </div>
    </section>
  );
}

function ContextMenu({ menu }) {
  if (!menu) return null;
  return (
    <div className="context-menu" style={{ left: menu.x, top: menu.y }}>
      {menu.title && <p className="context-menu-title">{menu.title}</p>}
      {menu.items.map((item) => (
        <button key={item.label} type="button" className={item.tone === "danger" ? "danger ghost" : "ghost"} onClick={() => item.onSelect()}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

function DemoWallPolygon({ polygon, stroke }) {
  const hatch = [];
  for (let cursor = polygon.bounds.minX - polygon.bounds.maxY; cursor < polygon.bounds.maxX + polygon.bounds.maxY; cursor += 12) {
    hatch.push(
      <Line
        key={cursor}
        points={[cursor, polygon.bounds.maxY + 24, cursor + polygon.bounds.maxY, polygon.bounds.minY - 24]}
        stroke="#f0b08a"
        strokeWidth={1}
        listening={false}
      />,
    );
  }

  return (
    <Group>
      <Line points={polygon.points} closed fill="#f7c3a0" stroke={stroke} strokeWidth={1.2} />
      <Group
        clipFunc={(ctx) => {
          ctx.beginPath();
          ctx.moveTo(polygon.points[0], polygon.points[1]);
          for (let index = 2; index < polygon.points.length; index += 2) {
            ctx.lineTo(polygon.points[index], polygon.points[index + 1]);
          }
          ctx.closePath();
        }}
      >
        {hatch}
      </Group>
      <Line points={polygon.points} closed stroke={stroke} strokeWidth={1.2} listening={false} />
    </Group>
  );
}

function OpeningSymbol({ opening, geometry, isSelected, onSelect, onContextMenu, onDragStart }) {
  const jambStroke = isSelected ? "#2d6cdf" : "#5c6570";
  const lineWeight = opening.kind === "window" ? 1.2 : 1.4;
  const jambA = [
    geometry.start.x - geometry.normal.x * (geometry.thickness / 2),
    geometry.start.y - geometry.normal.y * (geometry.thickness / 2),
    geometry.start.x + geometry.normal.x * (geometry.thickness / 2),
    geometry.start.y + geometry.normal.y * (geometry.thickness / 2),
  ];
  const jambB = [
    geometry.end.x - geometry.normal.x * (geometry.thickness / 2),
    geometry.end.y - geometry.normal.y * (geometry.thickness / 2),
    geometry.end.x + geometry.normal.x * (geometry.thickness / 2),
    geometry.end.y + geometry.normal.y * (geometry.thickness / 2),
  ];
  const openingLength = Math.hypot(geometry.end.x - geometry.start.x, geometry.end.y - geometry.start.y);

  let symbol = null;
  if (opening.kind === "door") {
    const hinge = geometry.start;
    const leafEnd = {
      x: hinge.x + geometry.interior.x * openingLength,
      y: hinge.y + geometry.interior.y * openingLength,
    };
    symbol = (
      <>
        <Line points={[hinge.x, hinge.y, leafEnd.x, leafEnd.y]} stroke={jambStroke} strokeWidth={1.1} />
        <Line
          points={sampleArcPoints(hinge, openingLength, Math.atan2(geometry.end.y - hinge.y, geometry.end.x - hinge.x), Math.atan2(leafEnd.y - hinge.y, leafEnd.x - hinge.x))}
          stroke={jambStroke}
          strokeWidth={0.9}
        />
      </>
    );
  } else if (opening.kind === "window") {
    const inset = geometry.thickness * 0.18;
    symbol = (
      <>
        <Line
          points={[
            geometry.start.x - geometry.normal.x * inset,
            geometry.start.y - geometry.normal.y * inset,
            geometry.end.x - geometry.normal.x * inset,
            geometry.end.y - geometry.normal.y * inset,
          ]}
          stroke={jambStroke}
          strokeWidth={lineWeight}
        />
        <Line
          points={[
            geometry.start.x + geometry.normal.x * inset,
            geometry.start.y + geometry.normal.y * inset,
            geometry.end.x + geometry.normal.x * inset,
            geometry.end.y + geometry.normal.y * inset,
          ]}
          stroke={jambStroke}
          strokeWidth={lineWeight}
        />
      </>
    );
  }

  return (
    <Group
      onMouseDown={(event) => {
        onSelect(event);
        onDragStart?.(event);
      }}
      onContextMenu={(event) => {
        event.evt.preventDefault();
        onContextMenu(event);
      }}
    >
      <Line points={geometry.gap} closed fill="#fcfbf8" stroke="#fcfbf8" />
      <Line points={jambA} stroke={jambStroke} strokeWidth={lineWeight} />
      <Line points={jambB} stroke={jambStroke} strokeWidth={lineWeight} />
      {symbol}
      {opening.kind === "cased" && (
        <Line points={[geometry.start.x, geometry.start.y, geometry.end.x, geometry.end.y]} stroke={jambStroke} strokeWidth={0.8} dash={[5, 4]} />
      )}
    </Group>
  );
}

function snapWorldPoint(point, increment = SNAP_INCREMENT) {
  if (!point) return null;
  return {
    x: Math.round(point.x / increment) * increment,
    y: Math.round(point.y / increment) * increment,
  };
}

function formatDraftValue(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return Number(value).toFixed(1).replace(/\.0$/, "");
}

function describeSelection(selected, room) {
  if (!selected || !room) return "Nothing selected";
  if (selected.kind === "wall") {
    const wall = room.walls.find((item) => item.id === selected.id);
    return wall ? `Wall ${wall.id}` : "Wall";
  }
  if (selected.kind === "opening") {
    const opening = room.openings.find((item) => item.id === selected.id);
    return opening ? `${opening.kind} ${opening.id}` : "Opening";
  }
  const cabinet = room.cabinets.find((item) => item.id === selected.id);
  return cabinet ? `Cabinet ${cabinet.kcd_code}` : "Cabinet";
}

function DraftingGrid({ room, view }) {
  const bounds = roomBounds(room);
  const minorStep = view.scale >= 4 ? 6 : 12;
  const majorEvery = 4;
  const padding = minorStep * 2;
  const minX = Math.floor((bounds.minX - padding) / minorStep) * minorStep;
  const maxX = Math.ceil((bounds.maxX + padding) / minorStep) * minorStep;
  const minY = Math.floor((bounds.minY - padding) / minorStep) * minorStep;
  const maxY = Math.ceil((bounds.maxY + padding) / minorStep) * minorStep;
  const lines = [];

  let index = 0;
  for (let x = minX; x <= maxX; x += minorStep) {
    const start = view.worldToScreen({ x, y: minY });
    const end = view.worldToScreen({ x, y: maxY });
    const major = index % majorEvery === 0;
    lines.push(
      <Line
        key={`grid-x-${x}`}
        points={[start.x, start.y, end.x, end.y]}
        stroke={major ? "#d6dde6" : "#ecf1f5"}
        strokeWidth={major ? 1 : 0.65}
        listening={false}
      />,
    );
    index += 1;
  }

  index = 0;
  for (let y = minY; y <= maxY; y += minorStep) {
    const start = view.worldToScreen({ x: minX, y });
    const end = view.worldToScreen({ x: maxX, y });
    const major = index % majorEvery === 0;
    lines.push(
      <Line
        key={`grid-y-${y}`}
        points={[start.x, start.y, end.x, end.y]}
        stroke={major ? "#d6dde6" : "#ecf1f5"}
        strokeWidth={major ? 1 : 0.65}
        listening={false}
      />,
    );
    index += 1;
  }

  return <Group>{lines}</Group>;
}

function ViewCropBox({ room, view }) {
  const bounds = roomBounds(room);
  const padding = 18;
  const topLeft = view.worldToScreen({ x: bounds.minX - padding, y: bounds.minY - padding });
  const bottomRight = view.worldToScreen({ x: bounds.maxX + padding, y: bounds.maxY + padding });
  return (
    <Rect
      x={Math.min(topLeft.x, bottomRight.x)}
      y={Math.min(topLeft.y, bottomRight.y)}
      width={Math.abs(bottomRight.x - topLeft.x)}
      height={Math.abs(bottomRight.y - topLeft.y)}
      stroke="#7e8896"
      strokeWidth={1}
      dash={[10, 8]}
      listening={false}
    />
  );
}

function CursorCrosshair({ cursorScreen, stageSize }) {
  if (!cursorScreen) return null;
  return (
    <Group listening={false}>
      <Line points={[cursorScreen.x, 0, cursorScreen.x, stageSize.height]} stroke="#7d9fcb" strokeWidth={1} dash={[8, 8]} />
      <Line points={[0, cursorScreen.y, stageSize.width, cursorScreen.y]} stroke="#7d9fcb" strokeWidth={1} dash={[8, 8]} />
    </Group>
  );
}

export default function App() {
  const [backend, setBackend] = useState("loading");
  const [catalog, setCatalog] = useState([]);
  const [projects, setProjects] = useState([]);
  const [project, setProject] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [generation, setGeneration] = useState(null);
  const [previewNonce, setPreviewNonce] = useState(0);
  const [status, setStatus] = useState("Loading...");
  const [roomDirty, setRoomDirty] = useState(false);
  const [selected, setSelected] = useState(null);
  const [catalogCode, setCatalogCode] = useState("B30");
  const [catalogUpper, setCatalogUpper] = useState(false);
  const [existingProjectId, setExistingProjectId] = useState("");
  const [setupForm, setSetupForm] = useState({ projectName: "New Project", projectScope: "Kitchen" });
  const [contextMenu, setContextMenu] = useState(null);
  const [stageSize, setStageSize] = useState({ width: 960, height: 660 });
  const [canvasCamera, setCanvasCamera] = useState({ zoom: 1, panX: 0, panY: 0 });
  const [cursorScreen, setCursorScreen] = useState(null);
  const [isPanning, setIsPanning] = useState(false);
  const [draftMode, setDraftMode] = useState(null);
  const [dragInteraction, setDragInteraction] = useState(null);
  const stageHostRef = useRef(null);
  const panPointerRef = useRef(null);
  const dragMovedRef = useRef(false);

  const catalogMap = {};
  for (const entry of catalog) {
    catalogMap[entry.code] = entry;
  }

  const room = project?.rooms.find((item) => item.id === roomId) || null;
  const view = room ? createView(room, stageSize.width, stageSize.height, canvasCamera) : null;
  const cursorWorld = room && view && cursorScreen ? snapWorldPoint(view.screenToWorld(cursorScreen)) : null;
  const selectionDescription = describeSelection(selected, room);
  const currentWall = selected?.kind === "wall" ? room?.walls.find((item) => item.id === selected.id) : null;
  const currentOpening = selected?.kind === "opening" ? room?.openings.find((item) => item.id === selected.id) : null;
  const currentCabinet = selected?.kind === "cabinet" ? room?.cabinets.find((item) => item.id === selected.id) : null;
  const currentOpeningGeometry = currentOpening && view ? openingScreenGeometry(currentOpening, room, view) : null;
  const roomTag = room ? `${String(room.room_number).padStart(2, "0")} ${room.label}` : "";
  const canvasModeLabel = draftMode ? "Wall sketch" : isPanning ? "Panning view" : dragInteraction ? "Editing selection" : "Drafting view";
  const draftEndPoint = room && draftMode?.kind === "wall" && cursorWorld
    ? snapWallPoint(cursorWorld, draftMode.start, room)
    : null;

  useEffect(() => {
    if (!stageHostRef.current) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      const nextWidth = Math.max(Math.floor(entry.contentRect.width), 480);
      const nextHeight = Math.max(Math.floor(entry.contentRect.height), 420);
      setStageSize({ width: nextWidth, height: nextHeight });
    });
    observer.observe(stageHostRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const close = () => setContextMenu(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, []);

  useEffect(() => {
    async function boot() {
      try {
        const [statusResponse, catalogResponse, projectList] = await Promise.all([loadStatus(), loadCatalog(), loadProjects()]);
        setBackend(statusResponse.backend);
        setCatalog(catalogResponse.entries);
        setProjects(projectList);
        setExistingProjectId(projectList[0]?.id || "");
        if (catalogResponse.entries[0]) {
          setCatalogCode(catalogResponse.entries[0].code);
        }
        setStatus("Set a project name and scope to begin.");
      } catch (error) {
        setStatus(error.message);
      }
    }
    boot();
  }, []);

  useEffect(() => {
    panPointerRef.current = null;
    dragMovedRef.current = false;
    setIsPanning(false);
    setCursorScreen(null);
    setCanvasCamera({ zoom: 1, panX: 0, panY: 0 });
    setDraftMode(null);
    setDragInteraction(null);
  }, [project?.id, roomId]);

  function closeContextMenu() {
    setContextMenu(null);
  }

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key !== "Escape") return;
      closeContextMenu();
      if (draftMode) {
        setDraftMode(null);
        setStatus("Wall sketch canceled.");
      }
      if (dragInteraction) {
        dragMovedRef.current = false;
        setDragInteraction(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [draftMode, dragInteraction]);

  function updateGeneration(nextGeneration) {
    setGeneration(nextGeneration);
    setPreviewNonce((current) => current + 1);
  }

  function resetCanvasView() {
    panPointerRef.current = null;
    dragMovedRef.current = false;
    setIsPanning(false);
    setCursorScreen(null);
    setCanvasCamera({ zoom: 1, panX: 0, panY: 0 });
  }

  function beginWallDraft(worldPoint, status) {
    if (!room) return;
    const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
    const start = snapWallPoint(snappedPoint, null, room);
    setDraftMode({ kind: "wall", status, start });
    setSelected(null);
    setStatus("Wall sketch started. Click the plan to place the end point. Endpoints snap together automatically.");
  }

  function finalizeWallDraft(worldPoint) {
    if (!room || !draftMode || draftMode.kind !== "wall") return;
    const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
    const end = snapWallPoint(snappedPoint, draftMode.start, room);
    if (pointDistance(draftMode.start, end) < WALL_DRAFT_MIN_LENGTH) {
      setStatus("Stretch the wall farther before placing it.");
      return;
    }
    const wallId = `wall-${Date.now()}`;
    mutateRoom((target) => {
      target.walls.push({
        id: wallId,
        start: { x: draftMode.start.x, y: draftMode.start.y },
        end: { x: end.x, y: end.y },
        thickness: 4.5,
        status: draftMode.status,
      });
    });
    setDraftMode(null);
    setSelected({ kind: "wall", id: wallId });
    setStatus("Wall drafted. Drag the blue grips to tune or join corners.");
  }

  function updateWallChildren(target, wall) {
    const nextWallLength = wallLength(wall);
    for (const opening of target.openings.filter((item) => item.wall_id === wall.id)) {
      opening.position_along_wall = clamp(opening.position_along_wall, 0, Math.max(nextWallLength - opening.width, 0));
    }
    for (const cabinet of target.cabinets.filter((item) => item.wall_id === wall.id)) {
      const entry = catalogMap[getBaseCode(cabinet.kcd_code)];
      if (!entry) continue;
      cabinet.offset_from_wall_start = clamp(cabinet.offset_from_wall_start, 0, Math.max(nextWallLength - entry.width, 0));
    }
  }

  function moveWallEndpoint(wallId, endpointKey, worldPoint) {
    mutateRoom((target) => {
      const wall = target.walls.find((item) => item.id === wallId);
      if (!wall) return;
      const anchorKey = endpointKey === "start" ? "end" : "start";
      const anchor = wall[anchorKey];
      const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
      const nextPoint = snapWallPoint(snappedPoint, anchor, target, wall.id);
      if (pointDistance(anchor, nextPoint) < WALL_DRAFT_MIN_LENGTH) return;
      wall[endpointKey] = nextPoint;
      updateWallChildren(target, wall);
    });
  }

  function moveOpening(openingId, worldPoint) {
    mutateRoom((target) => {
      const opening = target.openings.find((item) => item.id === openingId);
      if (!opening) return;
      const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
      const placement = resolveOpeningPlacement(opening, snappedPoint, target);
      if (!placement) return;
      opening.wall_id = placement.wall_id;
      opening.position_along_wall = placement.position_along_wall;
    });
  }

  function setCanvasZoom(nextZoom, pointer = null) {
    if (!room) return;
    setCanvasCamera((current) => {
      const zoom = clamp(nextZoom, MIN_CANVAS_ZOOM, MAX_CANVAS_ZOOM);
      if (!pointer) {
        return { ...current, zoom };
      }
      const currentView = createView(room, stageSize.width, stageSize.height, current);
      const worldPoint = currentView.screenToWorld(pointer);
      const nextView = createView(room, stageSize.width, stageSize.height, { ...current, zoom });
      const nextScreen = nextView.worldToScreen(worldPoint);
      return {
        zoom,
        panX: current.panX + (pointer.x - nextScreen.x),
        panY: current.panY + (pointer.y - nextScreen.y),
      };
    });
  }

  function panCanvasBy(dx, dy) {
    setCanvasCamera((current) => ({
      ...current,
      panX: current.panX + dx,
      panY: current.panY + dy,
    }));
  }

  function openContextMenu(screenPoint, title, items) {
    if (!stageHostRef.current) return;
    const hostWidth = stageHostRef.current.clientWidth;
    const hostHeight = stageHostRef.current.clientHeight;
    setContextMenu({
      x: clamp(screenPoint.x, 12, Math.max(hostWidth - 220, 12)),
      y: clamp(screenPoint.y, 12, Math.max(hostHeight - 220, 12)),
      title,
      items: items.map((item) => ({
        ...item,
        onSelect: async () => {
          closeContextMenu();
          await item.onSelect();
        },
      })),
    });
  }

  function mutateRoom(mutator) {
    setProject((current) => {
      if (!current) return current;
      const nextProject = structuredClone(current);
      const target = nextProject.rooms.find((item) => item.id === roomId);
      if (!target) return current;
      mutator(target);
      return nextProject;
    });
    setRoomDirty(true);
  }

  async function refreshProject(projectId, preserveRoom = true) {
    const loaded = await loadProject(projectId);
    setProject(loaded);
    setExistingProjectId(loaded.id);
    if (!preserveRoom || !loaded.rooms.some((item) => item.id === roomId)) {
      setRoomId(loaded.rooms[0]?.id || null);
    }
    setRoomDirty(false);
    return loaded;
  }

  async function handleProjectChange(nextId) {
    if (!nextId) return;
    try {
      setStatus("Loading project...");
      const loaded = await refreshProject(nextId, false);
      updateGeneration(await generateDrawingSet(loaded.id));
      setStatus("Project loaded.");
      setSelected(null);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function handleCreateProject() {
    try {
      setStatus("Creating project...");
      const created = await createProject({
        ...DEFAULT_METADATA,
        address: setupForm.projectName || "New Project",
        project_scope: setupForm.projectScope,
        use_sample: false,
      });
      setProject(created);
      setProjects((current) => [created, ...current.filter((item) => item.id !== created.id)].sort((a, b) => a.id.localeCompare(b.id)));
      setExistingProjectId(created.id);
      setRoomId(created.rooms[0]?.id || null);
      updateGeneration(await generateDrawingSet(created.id));
      setRoomDirty(false);
      setSelected(null);
      setStatus("Project created. Right-click on the canvas to add elements.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function handleSaveMetadata(formData) {
    if (!project) return;
    try {
      setStatus("Saving project details...");
      const updated = await updateProject(project.id, { ...formData, use_sample: false });
      setProject(updated);
      setProjects((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setStatus("Project details saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function handleSaveRoom() {
    if (!project || !room) return;
    try {
      setStatus("Saving room geometry...");
      const updated = await saveRoom(project.id, room.id, buildRoomPayload(room));
      setProject(updated);
      setRoomDirty(false);
      setStatus("Room geometry saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function handleGenerate() {
    if (!project) return;
    try {
      setStatus("Generating drawing set...");
      const response = await generateDrawingSet(project.id);
      updateGeneration(response);
      setStatus(`Generated ${Object.keys(response.sheet_urls).length} sheets.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function addWallAtPoint(worldPoint, status) {
    beginWallDraft(worldPoint, status);
  }

  function addOpeningAtPoint(openingKind, width, worldPoint, forcedWallId = null) {
    if (!room) return;
    const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
    const targetWall = forcedWallId ? { wall: room.walls.find((item) => item.id === forcedWallId), offset: 12 } : nearestWall(snappedPoint, room);
    if (!targetWall?.wall) {
      setStatus("Right-click closer to a wall to place an opening.");
      return;
    }
    mutateRoom((target) => {
      const wall = target.walls.find((item) => item.id === targetWall.wall.id);
      if (!wall) return;
      target.openings.push({
        id: `opening-${Date.now()}`,
        wall_id: wall.id,
        kind: openingKind,
        position_along_wall: clamp(targetWall.offset - width / 2, 0, Math.max(wallLength(wall) - width, 0)),
        width,
        height: openingKind === "window" ? 48 : 0,
        sill_height: openingKind === "window" ? 42 : 0,
        trim_width: 3.5,
        verify_in_field: false,
      });
    });
    setStatus(`${openingKind} added. Save room geometry to persist.`);
  }

  async function addCabinetAtPoint(worldPoint, forcedWallId = null) {
    if (!project || !room) return;
    if (roomDirty) {
      setStatus("Save room geometry before placing cabinets.");
      return;
    }
    const snappedPoint = snapWorldPoint(worldPoint) || worldPoint;
    const targetWall = forcedWallId ? { wall: room.walls.find((item) => item.id === forcedWallId), offset: 18 } : nearestWall(snappedPoint, room);
    if (!targetWall?.wall) {
      setStatus("Right-click closer to a wall to place a cabinet.");
      return;
    }
    const entry = catalogMap[catalogCode];
    if (!entry) {
      setStatus("Choose a valid cabinet preset first.");
      return;
    }
    try {
      const offset = clamp(targetWall.offset - entry.width / 2, 0, Math.max(wallLength(targetWall.wall) - entry.width, 0));
      const updated = await addCabinet(project.id, {
        kcd_code: catalogCode,
        wall_id: targetWall.wall.id,
        offset_from_wall_start: offset,
        is_upper: catalogUpper,
        hinge_side: "None",
        orientation: "standard",
        modifications: [],
      });
      setProject(updated);
      setStatus(`${catalogCode} placed.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function updateSelectedOpening(changes) {
    if (!selected || selected.kind !== "opening") return;
    mutateRoom((target) => {
      const opening = target.openings.find((item) => item.id === selected.id);
      if (!opening) return;
      Object.assign(opening, changes);
      const wall = target.walls.find((item) => item.id === opening.wall_id);
      if (!wall) return;
      opening.position_along_wall = clampOpeningPlacement(opening.width, wall, opening.position_along_wall);
    });
  }

  function updateSelectedWall(changes) {
    if (!selected || selected.kind !== "wall") return;
    mutateRoom((target) => {
      const wall = target.walls.find((item) => item.id === selected.id);
      if (!wall) return;
      Object.assign(wall, changes);
      updateWallChildren(target, wall);
    });
  }

  async function updateSelectedCabinet(changes) {
    if (!selected || selected.kind !== "cabinet" || !project || roomDirty) return;
    const cabinet = room?.cabinets.find((item) => item.id === selected.id);
    if (!cabinet) return;
    try {
      const updated = await updateCabinet(project.id, cabinet.id, {
        id: cabinet.id,
        kcd_code: changes.kcd_code || getBaseCode(cabinet.kcd_code),
        wall_id: changes.wall_id || cabinet.wall_id,
        offset_from_wall_start: changes.offset_from_wall_start === undefined ? cabinet.offset_from_wall_start : changes.offset_from_wall_start,
        is_upper: changes.is_upper === undefined ? cabinet.is_upper : changes.is_upper,
        hinge_side: "None",
        orientation: "standard",
        modifications: cabinet.modifications || [],
      });
      setProject(updated);
      setStatus("Cabinet updated.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function deleteSelectedElement() {
    if (!selected || !project) return;
    if (selected.kind === "cabinet") {
      try {
        const updated = await deleteCabinet(project.id, selected.id);
        setProject(updated);
        setSelected(null);
        setStatus("Cabinet deleted.");
      } catch (error) {
        setStatus(error.message);
      }
      return;
    }
    mutateRoom((target) => {
      if (selected.kind === "opening") {
        target.openings = target.openings.filter((item) => item.id !== selected.id);
        return;
      }
      target.walls = target.walls.filter((item) => item.id !== selected.id);
      target.openings = target.openings.filter((item) => item.wall_id !== selected.id);
      target.cabinets = target.cabinets.filter((item) => item.wall_id !== selected.id);
    });
    setSelected(null);
    setStatus("Element removed. Save room geometry to persist.");
  }

  function buildCanvasMenu(worldPoint, screenPoint) {
    const items = [
      { label: "Sketch Existing Wall", onSelect: () => addWallAtPoint(worldPoint, "existing") },
      { label: "Sketch New Wall", onSelect: () => addWallAtPoint(worldPoint, "new") },
      { label: "Sketch Demo Wall", onSelect: () => addWallAtPoint(worldPoint, "to_remove") },
    ];
    if (room?.walls.length) {
      items.push(
        { label: "Add Door Here", onSelect: () => addOpeningAtPoint("door", 30, worldPoint) },
        { label: "Add Window Here", onSelect: () => addOpeningAtPoint("window", 36, worldPoint) },
        { label: "Add Cased Opening Here", onSelect: () => addOpeningAtPoint("cased", 36, worldPoint) },
        { label: `Place ${catalogCode}${catalogUpper ? " (Upper)" : ""}`, onSelect: () => addCabinetAtPoint(worldPoint) },
      );
    }
    openContextMenu(screenPoint, "Canvas Actions", items);
  }

  function buildElementMenu(kind, id, worldPoint, screenPoint) {
    setSelected({ kind, id });
    if (kind === "wall") {
      openContextMenu(screenPoint, "Wall Actions", [
        { label: "Mark Existing", onSelect: () => updateSelectedWall({ status: "existing" }) },
        { label: "Mark New", onSelect: () => updateSelectedWall({ status: "new" }) },
        { label: "Mark Demo", onSelect: () => updateSelectedWall({ status: "to_remove" }) },
        { label: "Add Door to Wall", onSelect: () => addOpeningAtPoint("door", 30, worldPoint, id) },
        { label: "Add Window to Wall", onSelect: () => addOpeningAtPoint("window", 36, worldPoint, id) },
        { label: "Add Cabinet to Wall", onSelect: () => addCabinetAtPoint(worldPoint, id) },
        { label: "Delete Wall", onSelect: deleteSelectedElement, tone: "danger" },
      ]);
      return;
    }
    if (kind === "opening") {
      openContextMenu(screenPoint, "Opening Actions", [
        { label: "Convert to Door", onSelect: () => updateSelectedOpening({ kind: "door" }) },
        { label: "Convert to Window", onSelect: () => updateSelectedOpening({ kind: "window" }) },
        { label: "Convert to Cased Opening", onSelect: () => updateSelectedOpening({ kind: "cased" }) },
        { label: "Delete Opening", onSelect: deleteSelectedElement, tone: "danger" },
      ]);
      return;
    }
    const cabinet = room?.cabinets.find((item) => item.id === id);
    openContextMenu(screenPoint, "Cabinet Actions", [
      { label: cabinet?.is_upper ? "Convert to Base Cabinet" : "Convert to Upper Cabinet", onSelect: () => updateSelectedCabinet({ is_upper: !cabinet?.is_upper }) },
      { label: "Delete Cabinet", onSelect: deleteSelectedElement, tone: "danger" },
    ]);
  }

  function startWallEndpointDrag(event, wallId, endpointKey) {
    if (event.evt.button !== 0) return;
    event.cancelBubble = true;
    closeContextMenu();
    dragMovedRef.current = false;
    setSelected({ kind: "wall", id: wallId });
    setDragInteraction({ type: "wall-endpoint", wallId, endpointKey });
  }

  function startOpeningDrag(event, openingId) {
    if (event.evt.button !== 0) return;
    event.cancelBubble = true;
    closeContextMenu();
    dragMovedRef.current = false;
    setSelected({ kind: "opening", id: openingId });
    setDragInteraction({ type: "opening", openingId });
  }

  function stopPanning() {
    if (dragInteraction && dragMovedRef.current) {
      setStatus(dragInteraction.type === "opening" ? "Opening moved. Save room geometry to persist." : "Wall updated. Save room geometry to persist.");
    }
    dragMovedRef.current = false;
    setDragInteraction(null);
    panPointerRef.current = null;
    setIsPanning(false);
  }

  function handleStageMouseDown(event) {
    closeContextMenu();
    const stage = event.target.getStage();
    const pointer = stage?.getPointerPosition();
    if (draftMode && pointer && event.evt.button === 0) {
      event.evt.preventDefault();
      finalizeWallDraft(view.screenToWorld(pointer));
      return;
    }
    if (event.evt.button === 1 && pointer) {
      event.evt.preventDefault();
      panPointerRef.current = pointer;
      setIsPanning(true);
      return;
    }
    if (event.target === stage) {
      setSelected(null);
    }
  }

  function handleStageMouseMove(event) {
    const stage = event.target.getStage();
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    setCursorScreen(pointer);
    if (dragInteraction && view) {
      const worldPoint = view.screenToWorld(pointer);
      if (dragInteraction.type === "wall-endpoint") {
        moveWallEndpoint(dragInteraction.wallId, dragInteraction.endpointKey, worldPoint);
      }
      if (dragInteraction.type === "opening") {
        moveOpening(dragInteraction.openingId, worldPoint);
      }
      dragMovedRef.current = true;
      return;
    }
    if (!panPointerRef.current) return;
    const deltaX = pointer.x - panPointerRef.current.x;
    const deltaY = pointer.y - panPointerRef.current.y;
    panPointerRef.current = pointer;
    panCanvasBy(deltaX, deltaY);
  }

  function handleStageWheel(event) {
    event.evt.preventDefault();
    const stage = event.target.getStage();
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    const factor = event.evt.deltaY > 0 ? 1 / ZOOM_STEP : ZOOM_STEP;
    setCanvasZoom(canvasCamera.zoom * factor, pointer);
  }

  if (!project) {
    return (
      <div className="app-shell">
        <header className="app-header">
          <div>
            <p className="eyebrow">OD Select Drawing Engine</p>
            <h1>treecab studio</h1>
            <p className="hero-text">Start with the project basics, then build the plan with right-click actions and sample-matched graphics.</p>
          </div>
          <div className="header-meta">
            <span className="badge">Backend: {backend}</span>
            <button type="button" className="secondary" onClick={() => fetch("/auth/logout", { method: "POST" }).then(() => window.location.replace("/"))}>
              Lock Site
            </button>
          </div>
        </header>
        <SetupScreen
          projects={projects}
          existingProjectId={existingProjectId}
          onExistingProjectChange={setExistingProjectId}
          onOpenExisting={() => handleProjectChange(existingProjectId)}
          setupForm={setupForm}
          setSetupForm={setSetupForm}
          onCreate={handleCreateProject}
        />
        <section className="panel">
          <p className="status-line">{status}</p>
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">OD Select Drawing Engine</p>
          <h1>treecab studio</h1>
          <p className="hero-text">Right-click driven plan editor with wall bodies, opening symbols, and cabinet graphics aligned to the sample construction set.</p>
        </div>
        <div className="header-meta">
          <span className="badge">Backend: {backend}</span>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              resetCanvasView();
              setProject(null);
              setGeneration(null);
              setSelected(null);
              setStatus("Set a project name and scope to begin.");
            }}
          >
            New Project
          </button>
          <button type="button" className="secondary" onClick={() => fetch("/auth/logout", { method: "POST" }).then(() => window.location.replace("/"))}>
            Lock Site
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar">
          <section className="panel">
            <div className="section-head">
              <h2>Projects</h2>
              <span className="hint">Switch project</span>
            </div>
            <select value={project?.id || ""} onChange={(event) => handleProjectChange(event.target.value)}>
              {projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.address} ({item.project_scope || "Kitchen"})
                </option>
              ))}
            </select>
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Project Details</h2>
              <button type="button" onClick={handleGenerate}>Generate</button>
            </div>
            <MetadataForm key={project.id} project={project} onSave={handleSaveMetadata} />
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Room</h2>
              <button type="button" className={roomDirty ? "warning" : "ghost"} onClick={handleSaveRoom}>
                {roomDirty ? "Save Room" : "Room Saved"}
              </button>
            </div>
            {room ? (
              <div className="stack">
                <select value={roomId || ""} onChange={(event) => setRoomId(event.target.value)}>
                  {project.rooms.map((item) => (
                    <option key={item.id} value={item.id}>
                      {String(item.room_number).padStart(2, "0")} {item.label}
                    </option>
                  ))}
                </select>
                <label>
                  Label
                  <input value={room.label} onChange={(event) => mutateRoom((target) => { target.label = event.target.value; })} />
                </label>
                <label>
                  Ceiling Height
                  <input
                    type="number"
                    step="0.25"
                    value={room.ceiling_height}
                    onChange={(event) => mutateRoom((target) => { target.ceiling_height = Number(event.target.value); })}
                  />
                </label>
              </div>
            ) : (
              <p className="empty">Choose a room to edit.</p>
            )}
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Canvas Actions</h2>
              <span className="hint">Right-click to sketch</span>
            </div>
            <div className="stack">
              <p className="hint">Right-click on the plan to sketch walls or place elements. Drag blue wall grips to join corners and drag openings to slide them within walls.</p>
              <label>
                Cabinet Preset
                <select value={catalogCode} onChange={(event) => setCatalogCode(event.target.value)}>
                  {catalog.filter((entry) => ["base", "wall", "vanity", "tall"].includes(entry.category)).map((entry) => (
                    <option key={entry.code} value={entry.code}>
                      {entry.code} ({entry.width} x {entry.height})
                    </option>
                  ))}
                </select>
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={catalogUpper} onChange={(event) => setCatalogUpper(event.target.checked)} />
                Place as upper cabinet
              </label>
            </div>
          </section>
        </aside>

        <section className="canvas-column">
          <section className="panel canvas-panel">
            <div className="section-head">
              <div>
                <h2>Plan Canvas</h2>
                <p className="hint">Wheel to zoom, middle mouse to pan, right-click to sketch/place, and drag wall grips or openings to refine the plan.</p>
              </div>
              <span className={roomDirty ? "dirty-flag active" : "dirty-flag"}>{roomDirty ? "Unsaved room changes" : "Room synced"}</span>
            </div>
            <div ref={stageHostRef} className={`stage-host ${isPanning ? "is-panning" : ""} ${draftMode ? "is-drafting" : ""}`}>
              <div className="canvas-toolbar">
                <div className="canvas-toolbar-group">
                  <span className="canvas-chip canvas-chip-strong">Level 1</span>
                  <span className="canvas-chip">{roomTag}</span>
                  <span className="canvas-chip">{canvasModeLabel}</span>
                </div>
                <div className="canvas-toolbar-group">
                  <button type="button" className="canvas-tool" onClick={() => setCanvasZoom(canvasCamera.zoom / ZOOM_STEP)}>
                    -
                  </button>
                  <button type="button" className="canvas-tool" onClick={() => setCanvasZoom(1)}>
                    100%
                  </button>
                  <button type="button" className="canvas-tool" onClick={() => setCanvasZoom(canvasCamera.zoom * ZOOM_STEP)}>
                    +
                  </button>
                  <button type="button" className="canvas-tool" onClick={resetCanvasView}>
                    Fit
                  </button>
                </div>
              </div>
              <ContextMenu menu={contextMenu} />
              {room && view ? (
                <Stage
                  width={stageSize.width}
                  height={stageSize.height}
                  onMouseDown={handleStageMouseDown}
                  onMouseMove={handleStageMouseMove}
                  onMouseUp={stopPanning}
                  onMouseLeave={() => {
                    setCursorScreen(null);
                    stopPanning();
                  }}
                  onWheel={handleStageWheel}
                  onContextMenu={(event) => {
                    event.evt.preventDefault();
                    const pointer = event.target.getStage().getPointerPosition();
                    if (!pointer || !view) return;
                    if (draftMode) {
                      openContextMenu(pointer, "Wall Sketch", [
                        { label: "Finish Wall Here", onSelect: () => finalizeWallDraft(view.screenToWorld(pointer)) },
                        {
                          label: "Cancel Sketch",
                          onSelect: () => {
                            setDraftMode(null);
                            setStatus("Wall sketch canceled.");
                          },
                        },
                      ]);
                      return;
                    }
                    buildCanvasMenu(snapWorldPoint(view.screenToWorld(pointer)) || view.screenToWorld(pointer), pointer);
                  }}
                >
                  <Layer>
                    <Rect x={0} y={0} width={stageSize.width} height={stageSize.height} fill="#bcc4cd" />
                    <Rect x={18} y={18} width={stageSize.width - 36} height={stageSize.height - 36} fill="#fbfcfe" stroke="#7d8793" strokeWidth={1.2} shadowColor="rgba(20, 30, 40, 0.18)" shadowBlur={18} shadowOffsetY={8} />
                    <DraftingGrid room={room} view={view} />
                    <ViewCropBox room={room} view={view} />
                    <CursorCrosshair cursorScreen={cursorScreen} stageSize={stageSize} />
                    {draftMode?.kind === "wall" && draftEndPoint && (
                      <Line
                        points={[
                          view.worldToScreen(draftMode.start).x,
                          view.worldToScreen(draftMode.start).y,
                          view.worldToScreen(draftEndPoint).x,
                          view.worldToScreen(draftEndPoint).y,
                        ]}
                        stroke="#2d6cdf"
                        strokeWidth={2}
                        dash={[10, 8]}
                        listening={false}
                      />
                    )}
                    {room.walls.map((wall) => {
                      const polygon = wallPolygon(wall, room, view);
                      const isSelected = selected?.kind === "wall" && selected.id === wall.id;
                      const stroke = isSelected ? "#2d6cdf" : "#262b33";
                      const fill = wall.status === "new" ? "#8e99a5" : "#fbfcfe";
                      return (
                        <Group
                          key={wall.id}
                          onMouseDown={() => setSelected({ kind: "wall", id: wall.id })}
                          onContextMenu={(event) => {
                            if (draftMode) return;
                            event.evt.preventDefault();
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("wall", wall.id, snapWorldPoint(view.screenToWorld(pointer)) || view.screenToWorld(pointer), pointer);
                          }}
                        >
                          {wall.status === "to_remove" ? <DemoWallPolygon polygon={polygon} stroke={stroke} /> : <Line points={polygon.points} closed fill={fill} stroke={stroke} strokeWidth={isSelected ? 2 : 1.2} />}
                        </Group>
                      );
                    })}
                    {room.openings.map((opening) => {
                      const geometry = openingScreenGeometry(opening, room, view);
                      if (!geometry) return null;
                      return (
                        <OpeningSymbol
                          key={opening.id}
                          opening={opening}
                          geometry={geometry}
                          isSelected={selected?.kind === "opening" && selected.id === opening.id}
                          onSelect={() => setSelected({ kind: "opening", id: opening.id })}
                          onDragStart={(event) => startOpeningDrag(event, opening.id)}
                          onContextMenu={(event) => {
                            if (draftMode) return;
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("opening", opening.id, snapWorldPoint(view.screenToWorld(pointer)) || view.screenToWorld(pointer), pointer);
                          }}
                        />
                      );
                    })}
                    {room.cabinets.map((cabinet) => {
                      const rect = cabinetScreenRect(cabinet, room, view, catalogMap);
                      if (!rect) return null;
                      const isSelected = selected?.kind === "cabinet" && selected.id === cabinet.id;
                      return (
                        <Group
                          key={cabinet.id}
                          onMouseDown={() => setSelected({ kind: "cabinet", id: cabinet.id })}
                          onContextMenu={(event) => {
                            if (draftMode) return;
                            event.evt.preventDefault();
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("cabinet", cabinet.id, snapWorldPoint(view.screenToWorld(pointer)) || view.screenToWorld(pointer), pointer);
                          }}
                        >
                          <Rect x={rect.x} y={rect.y} width={rect.width} height={rect.height} fill={cabinet.is_upper ? "#f4f7fb" : "#ffffff"} stroke={isSelected ? "#2d6cdf" : "#20252c"} strokeWidth={isSelected ? 2.2 : 1.2} dash={cabinet.is_upper ? [7, 4] : []} />
                          <Text x={rect.x + 4} y={rect.y + rect.height / 2 - 7} text={cabinet.kcd_code} fontSize={10} fill="#20252c" width={Math.max(rect.width - 8, 44)} align="center" />
                        </Group>
                      );
                    })}
                    {currentWall && (
                      <>
                        {["start", "end"].map((endpointKey) => {
                          const point = view.worldToScreen(currentWall[endpointKey]);
                          return (
                            <Circle
                              key={`${currentWall.id}-${endpointKey}`}
                              x={point.x}
                              y={point.y}
                              radius={8}
                              fill="#ffffff"
                              stroke="#2d6cdf"
                              strokeWidth={2.4}
                              onMouseDown={(event) => startWallEndpointDrag(event, currentWall.id, endpointKey)}
                            />
                          );
                        })}
                      </>
                    )}
                    {currentOpeningGeometry && (
                      <Circle
                        x={currentOpeningGeometry.center.x}
                        y={currentOpeningGeometry.center.y}
                        radius={7}
                        fill="#ffffff"
                        stroke="#2d6cdf"
                        strokeWidth={2}
                        dash={[4, 3]}
                        onMouseDown={(event) => startOpeningDrag(event, currentOpening.id)}
                      />
                    )}
                  </Layer>
                </Stage>
              ) : (
                <div className="empty canvas-empty">No room loaded.</div>
              )}
              <div className="canvas-statusbar">
                <span>Zoom {Math.round(canvasCamera.zoom * 100)}%</span>
                <span>X {formatDraftValue(cursorWorld?.x)}</span>
                <span>Y {formatDraftValue(cursorWorld?.y)}</span>
                <span>{selectionDescription}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Inspector</h2>
              <button type="button" className="danger" onClick={deleteSelectedElement} disabled={!selected}>Delete</button>
            </div>
            {!selected && <p className="empty">Select a wall or opening to drag it directly, or right-click to add/edit elements.</p>}
            {currentWall && (
              <div className="stack">
                <p className="inspector-title">Wall {currentWall.id}</p>
                <label>
                  Status
                  <select value={currentWall.status} onChange={(event) => updateSelectedWall({ status: event.target.value })}>
                    <option value="existing">existing</option>
                    <option value="new">new</option>
                    <option value="to_remove">to_remove</option>
                  </select>
                </label>
                <label>
                  Thickness
                  <input type="number" step="0.25" value={currentWall.thickness || 4.5} onChange={(event) => updateSelectedWall({ thickness: Number(event.target.value) })} />
                </label>
                <div className="two-up">
                  <label>
                    Start X
                    <input type="number" step="0.25" value={currentWall.start.x} onChange={(event) => updateSelectedWall({ start: { ...currentWall.start, x: Number(event.target.value) } })} />
                  </label>
                  <label>
                    Start Y
                    <input type="number" step="0.25" value={currentWall.start.y} onChange={(event) => updateSelectedWall({ start: { ...currentWall.start, y: Number(event.target.value) } })} />
                  </label>
                </div>
                <div className="two-up">
                  <label>
                    End X
                    <input type="number" step="0.25" value={currentWall.end.x} onChange={(event) => updateSelectedWall({ end: { ...currentWall.end, x: Number(event.target.value) } })} />
                  </label>
                  <label>
                    End Y
                    <input type="number" step="0.25" value={currentWall.end.y} onChange={(event) => updateSelectedWall({ end: { ...currentWall.end, y: Number(event.target.value) } })} />
                  </label>
                </div>
              </div>
            )}
            {currentOpening && (
              <div className="stack">
                <p className="inspector-title">Opening {currentOpening.id}</p>
                <label>
                  Kind
                  <select value={currentOpening.kind} onChange={(event) => updateSelectedOpening({ kind: event.target.value })}>
                    <option value="door">door</option>
                    <option value="window">window</option>
                    <option value="cased">cased</option>
                  </select>
                </label>
                <label>
                  Wall
                  <select value={currentOpening.wall_id} onChange={(event) => updateSelectedOpening({ wall_id: event.target.value })}>
                    {room?.walls.map((wall) => <option key={wall.id} value={wall.id}>{wall.id}</option>)}
                  </select>
                </label>
                <div className="two-up">
                  <label>
                    Offset
                    <input type="number" step="0.25" value={currentOpening.position_along_wall} onChange={(event) => updateSelectedOpening({ position_along_wall: Number(event.target.value) })} />
                  </label>
                  <label>
                    Width
                    <input type="number" step="0.25" value={currentOpening.width} onChange={(event) => updateSelectedOpening({ width: Number(event.target.value) })} />
                  </label>
                </div>
                <div className="two-up">
                  <label>
                    Height
                    <input type="number" step="0.25" value={currentOpening.height || 0} onChange={(event) => updateSelectedOpening({ height: Number(event.target.value) })} />
                  </label>
                  <label>
                    Sill Height
                    <input type="number" step="0.25" value={currentOpening.sill_height || 0} onChange={(event) => updateSelectedOpening({ sill_height: Number(event.target.value) })} />
                  </label>
                </div>
                <label className="checkbox">
                  <input type="checkbox" checked={Boolean(currentOpening.verify_in_field)} onChange={(event) => updateSelectedOpening({ verify_in_field: event.target.checked })} />
                  Verify in field
                </label>
              </div>
            )}
            {currentCabinet && (
              <div className="stack">
                <p className="inspector-title">Cabinet {currentCabinet.id}</p>
                <label>
                  Code
                  <select value={getBaseCode(currentCabinet.kcd_code)} onChange={(event) => updateSelectedCabinet({ kcd_code: event.target.value })} disabled={roomDirty}>
                    {catalog.filter((entry) => ["base", "wall", "vanity", "tall"].includes(entry.category)).map((entry) => <option key={entry.code} value={entry.code}>{entry.code}</option>)}
                  </select>
                </label>
                <label>
                  Wall
                  <select value={currentCabinet.wall_id} onChange={(event) => updateSelectedCabinet({ wall_id: event.target.value })} disabled={roomDirty}>
                    {room?.walls.map((wall) => <option key={wall.id} value={wall.id}>{wall.id}</option>)}
                  </select>
                </label>
                <label>
                  Offset from Wall Start
                  <input type="number" step="0.25" value={currentCabinet.offset_from_wall_start} onChange={(event) => updateSelectedCabinet({ offset_from_wall_start: Number(event.target.value) })} disabled={roomDirty} />
                </label>
                <label className="checkbox">
                  <input type="checkbox" checked={Boolean(currentCabinet.is_upper)} onChange={(event) => updateSelectedCabinet({ is_upper: event.target.checked })} disabled={roomDirty} />
                  Upper cabinet
                </label>
              </div>
            )}
          </section>

          <section className="panel preview-panel">
            <div className="section-head">
              <h2>Outputs</h2>
              <div className="inline-actions">
                <button type="button" className="ghost" onClick={handleGenerate}>Refresh Output</button>
                {generation?.pdf_url && <a href={generation.pdf_url} target="_blank" rel="noreferrer">PDF</a>}
                {generation?.tsv_url && <a href={generation.tsv_url} target="_blank" rel="noreferrer">TSV</a>}
              </div>
            </div>
            <p className="status-line">{status}</p>
            {generation?.sheet_urls ? (
              <iframe title="Sheet preview" src={`${generation.sheet_urls["A-02"] || Object.values(generation.sheet_urls)[0]}?v=${previewNonce}`} />
            ) : (
              <div className="empty preview-empty">Generate a drawing set to load the preview.</div>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
