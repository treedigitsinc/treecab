import { useEffect, useRef, useState } from "react";
import { Group, Layer, Line, Rect, Stage, Text } from "react-konva";

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
  openingScreenGeometry,
  polygonBounds,
  roomBounds,
  sampleArcPoints,
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

function newWallFromPoint(point, status, room) {
  const bounds = roomBounds(room);
  const originX = Math.max(point.x, bounds.minX - 24);
  const originY = Math.max(point.y, bounds.minY - 24);
  return {
    id: `wall-${Date.now()}`,
    start: { x: Math.round(originX), y: Math.round(originY) },
    end: { x: Math.round(originX + 96), y: Math.round(originY) },
    thickness: 4.5,
    status,
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

function OpeningSymbol({ opening, geometry, isSelected, onSelect, onContextMenu }) {
  const jambStroke = isSelected ? "#b85635" : "#6f665d";
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
      onMouseDown={onSelect}
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

export default function App() {
  const [backend, setBackend] = useState("loading");
  const [catalog, setCatalog] = useState([]);
  const [projects, setProjects] = useState([]);
  const [project, setProject] = useState(null);
  const [roomId, setRoomId] = useState(null);
  const [generation, setGeneration] = useState(null);
  const [status, setStatus] = useState("Loading...");
  const [roomDirty, setRoomDirty] = useState(false);
  const [selected, setSelected] = useState(null);
  const [catalogCode, setCatalogCode] = useState("B30");
  const [catalogUpper, setCatalogUpper] = useState(false);
  const [existingProjectId, setExistingProjectId] = useState("");
  const [setupForm, setSetupForm] = useState({ projectName: "New Project", projectScope: "Kitchen" });
  const [contextMenu, setContextMenu] = useState(null);
  const [stageSize, setStageSize] = useState({ width: 960, height: 660 });
  const stageHostRef = useRef(null);

  const catalogMap = {};
  for (const entry of catalog) {
    catalogMap[entry.code] = entry;
  }

  const room = project?.rooms.find((item) => item.id === roomId) || null;
  const view = room ? createView(room, stageSize.width, stageSize.height) : null;
  const currentWall = selected?.kind === "wall" ? room?.walls.find((item) => item.id === selected.id) : null;
  const currentOpening = selected?.kind === "opening" ? room?.openings.find((item) => item.id === selected.id) : null;
  const currentCabinet = selected?.kind === "cabinet" ? room?.cabinets.find((item) => item.id === selected.id) : null;

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

  function closeContextMenu() {
    setContextMenu(null);
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
      setGeneration(await generateDrawingSet(loaded.id));
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
      setGeneration(await generateDrawingSet(created.id));
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
      setGeneration(response);
      setStatus(`Generated ${Object.keys(response.sheet_urls).length} sheets.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  function addWallAtPoint(worldPoint, status) {
    if (!room) return;
    mutateRoom((target) => {
      target.walls.push(newWallFromPoint(worldPoint, status, target));
    });
    setStatus("Wall added. Save room geometry to persist.");
  }

  function addOpeningAtPoint(openingKind, width, worldPoint, forcedWallId = null) {
    if (!room) return;
    const targetWall = forcedWallId ? { wall: room.walls.find((item) => item.id === forcedWallId), offset: 12 } : nearestWall(worldPoint, room);
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
    const targetWall = forcedWallId ? { wall: room.walls.find((item) => item.id === forcedWallId), offset: 18 } : nearestWall(worldPoint, room);
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
    });
  }

  function updateSelectedWall(changes) {
    if (!selected || selected.kind !== "wall") return;
    mutateRoom((target) => {
      const wall = target.walls.find((item) => item.id === selected.id);
      if (!wall) return;
      Object.assign(wall, changes);
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
      { label: "Add Existing Wall", onSelect: () => addWallAtPoint(worldPoint, "existing") },
      { label: "Add New Wall", onSelect: () => addWallAtPoint(worldPoint, "new") },
      { label: "Add Demo Wall", onSelect: () => addWallAtPoint(worldPoint, "to_remove") },
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
              <span className="hint">Right-click to place</span>
            </div>
            <div className="stack">
              <p className="hint">Right-click on the plan to add walls, openings, or cabinetry. Right-click an existing element for contextual actions.</p>
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
                <p className="hint">Right-click on empty space to add. Right-click an element to edit or delete it.</p>
              </div>
              <span className={roomDirty ? "dirty-flag active" : "dirty-flag"}>{roomDirty ? "Unsaved room changes" : "Room synced"}</span>
            </div>
            <div ref={stageHostRef} className="stage-host">
              <ContextMenu menu={contextMenu} />
              {room && view ? (
                <Stage
                  width={stageSize.width}
                  height={stageSize.height}
                  onMouseDown={(event) => {
                    closeContextMenu();
                    if (event.target === event.target.getStage()) {
                      setSelected(null);
                    }
                  }}
                  onContextMenu={(event) => {
                    event.evt.preventDefault();
                    const pointer = event.target.getStage().getPointerPosition();
                    if (!pointer || !view) return;
                    buildCanvasMenu(view.screenToWorld(pointer), pointer);
                  }}
                >
                  <Layer>
                    <Rect x={0} y={0} width={stageSize.width} height={stageSize.height} fill="#fffdf9" />
                    {room.walls.map((wall) => {
                      const polygon = wallPolygon(wall, view);
                      const isSelected = selected?.kind === "wall" && selected.id === wall.id;
                      const stroke = isSelected ? "#b85635" : "#1f1a15";
                      const fill = wall.status === "new" ? "#9da3a7" : "#fffdf9";
                      return (
                        <Group
                          key={wall.id}
                          onMouseDown={() => setSelected({ kind: "wall", id: wall.id })}
                          onContextMenu={(event) => {
                            event.evt.preventDefault();
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("wall", wall.id, view.screenToWorld(pointer), pointer);
                          }}
                        >
                          {wall.status === "to_remove" ? <DemoWallPolygon polygon={polygon} stroke={stroke} /> : <Line points={polygon.points} closed fill={fill} stroke={stroke} strokeWidth={isSelected ? 1.8 : 1.2} />}
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
                          onContextMenu={(event) => {
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("opening", opening.id, view.screenToWorld(pointer), pointer);
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
                            event.evt.preventDefault();
                            const pointer = event.target.getStage().getPointerPosition();
                            if (!pointer || !view) return;
                            buildElementMenu("cabinet", cabinet.id, view.screenToWorld(pointer), pointer);
                          }}
                        >
                          <Rect x={rect.x} y={rect.y} width={rect.width} height={rect.height} fill={cabinet.is_upper ? "#fbf6ee" : "#ffffff"} stroke={isSelected ? "#b85635" : "#221c16"} strokeWidth={isSelected ? 2.2 : 1.2} dash={cabinet.is_upper ? [7, 4] : []} />
                          <Text x={rect.x + 4} y={rect.y + rect.height / 2 - 7} text={cabinet.kcd_code} fontSize={10} fill="#221c16" width={Math.max(rect.width - 8, 44)} align="center" />
                        </Group>
                      );
                    })}
                  </Layer>
                </Stage>
              ) : (
                <div className="empty canvas-empty">No room loaded.</div>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Inspector</h2>
              <button type="button" className="danger" onClick={deleteSelectedElement} disabled={!selected}>Delete</button>
            </div>
            {!selected && <p className="empty">Right-click or select a wall, opening, or cabinet to edit it.</p>}
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
              <iframe title="Sheet preview" src={`${generation.sheet_urls["A-02"] || Object.values(generation.sheet_urls)[0]}?t=${Date.now()}`} />
            ) : (
              <div className="empty preview-empty">Generate a drawing set to load the preview.</div>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
