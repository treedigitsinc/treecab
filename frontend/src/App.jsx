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
  openingScreenLine,
  roomBounds,
  wallLength,
} from "./geometry";
import { openingPalette, wallPalette } from "./palette";

const DEFAULT_METADATA = {
  address: "New Project",
  kcd_color: "BW",
  kcd_style: "Brooklyn White",
  drawer_type: "5-piece",
  uppers_height: 36,
  crown_molding: "Flat",
  designer: "LOCAL",
};

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
        Address
        <input value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
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
      <button type="submit">Save Metadata</button>
    </form>
  );
}

function PaletteItem({ item, onDragStart }) {
  return (
    <div className="palette-item" draggable onDragStart={(event) => onDragStart(event, item)}>
      <span>{item.label}</span>
      <small>drag</small>
    </div>
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
  const [stageSize, setStageSize] = useState({ width: 960, height: 660 });
  const stageHostRef = useRef(null);

  const catalogMap = {};
  for (const entry of catalog) {
    catalogMap[entry.code] = entry;
  }

  const room = project?.rooms.find((item) => item.id === roomId) || null;
  const view = room ? createView(room, stageSize.width, stageSize.height) : null;

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
    async function boot() {
      try {
        const [statusResponse, catalogResponse, projectList] = await Promise.all([
          loadStatus(),
          loadCatalog(),
          loadProjects(),
        ]);
        setBackend(statusResponse.backend);
        setCatalog(catalogResponse.entries);
        setProjects(projectList);
        if (catalogResponse.entries[0]) {
          setCatalogCode(catalogResponse.entries[0].code);
        }
        if (projectList[0]?.id) {
          const loaded = await loadProject(projectList[0].id);
          setProject(loaded);
          setRoomId(loaded.rooms[0]?.id || null);
          setGeneration(await generateDrawingSet(loaded.id));
          setStatus("Canvas editor ready.");
        } else {
          setStatus("Create a project to begin.");
        }
      } catch (error) {
        setStatus(error.message);
      }
    }
    boot();
  }, []);

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
    if (!preserveRoom || !loaded.rooms.some((item) => item.id === roomId)) {
      setRoomId(loaded.rooms[0]?.id || null);
    }
    setRoomDirty(false);
    return loaded;
  }

  async function handleProjectChange(nextId) {
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

  async function handleCreateProject(useSample) {
    try {
      setStatus("Creating project...");
      const created = await createProject({
        ...DEFAULT_METADATA,
        use_sample: useSample,
      });
      setProject(created);
      setProjects((current) =>
        [created, ...current.filter((item) => item.id !== created.id)].sort((a, b) => a.id.localeCompare(b.id)),
      );
      setRoomId(created.rooms[0]?.id || null);
      setGeneration(await generateDrawingSet(created.id));
      setRoomDirty(false);
      setSelected(null);
      setStatus("Project created.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function handleSaveMetadata(formData) {
    if (!project) return;
    try {
      setStatus("Saving metadata...");
      const updated = await updateProject(project.id, {
        ...formData,
        use_sample: false,
      });
      setProject(updated);
      setStatus("Metadata saved.");
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

  function beginDragItem(event, item) {
    event.dataTransfer.setData("application/treecab-palette", JSON.stringify(item));
    event.dataTransfer.effectAllowed = "copy";
  }

  async function handleCanvasDrop(event) {
    event.preventDefault();
    if (!project || !room || !view) return;
    try {
      const raw = event.dataTransfer.getData("application/treecab-palette");
      if (!raw) return;
      const item = JSON.parse(raw);
      const rect = stageHostRef.current.getBoundingClientRect();
      const worldPoint = view.screenToWorld({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      });

      if (item.kind === "wall") {
        mutateRoom((target) => {
          target.walls.push(newWallFromPoint(worldPoint, item.status, target));
        });
        setStatus("Wall added. Save room geometry to persist.");
        return;
      }

      const targetWall = nearestWall(worldPoint, room);
      if (!targetWall) {
        setStatus("Drop closer to a wall.");
        return;
      }

      if (item.kind === "opening") {
        mutateRoom((target) => {
          target.openings.push({
            id: `opening-${Date.now()}`,
            wall_id: targetWall.wall.id,
            kind: item.openingKind,
            position_along_wall: clamp(
              targetWall.offset - item.width / 2,
              0,
              Math.max(wallLength(targetWall.wall) - item.width, 0),
            ),
            width: item.width,
            height: item.openingKind === "window" ? 48 : 0,
            sill_height: item.openingKind === "window" ? 42 : 0,
            trim_width: 3.5,
            verify_in_field: false,
          });
        });
        setStatus("Opening added. Save room geometry to persist.");
        return;
      }

      if (item.kind === "cabinet") {
        if (roomDirty) {
          setStatus("Save room geometry before placing cabinets.");
          return;
        }
        const entry = catalogMap[item.code];
        if (!entry) {
          setStatus("Choose a valid cabinet preset first.");
          return;
        }
        const offset = clamp(
          targetWall.offset - entry.width / 2,
          0,
          Math.max(wallLength(targetWall.wall) - entry.width, 0),
        );
        const updated = await addCabinet(project.id, {
          kcd_code: item.code,
          wall_id: targetWall.wall.id,
          offset_from_wall_start: offset,
          is_upper: Boolean(item.isUpper),
          hinge_side: "None",
          orientation: "standard",
          modifications: [],
        });
        setProject(updated);
        setStatus(`${item.code} placed.`);
      }
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
        offset_from_wall_start:
          changes.offset_from_wall_start === undefined
            ? cabinet.offset_from_wall_start
            : changes.offset_from_wall_start,
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
    });
    setSelected(null);
    setStatus("Element removed. Save room geometry to persist.");
  }

  async function moveCabinet(cabinet, pointer) {
    if (!project || !room || roomDirty || !view) {
      setStatus("Save room geometry before moving cabinets.");
      return;
    }
    const world = view.screenToWorld(pointer);
    const targetWall = nearestWall(world, room);
    if (!targetWall) return;
    const entry = catalogMap[getBaseCode(cabinet.kcd_code)];
    const offset = clamp(
      targetWall.offset - entry.width / 2,
      0,
      Math.max(wallLength(targetWall.wall) - entry.width, 0),
    );
    await updateSelectedCabinet({
      wall_id: targetWall.wall.id,
      offset_from_wall_start: offset,
    });
  }

  function moveOpening(opening, pointer) {
    if (!room || !view) return;
    const world = view.screenToWorld(pointer);
    const targetWall = nearestWall(world, room);
    if (!targetWall) return;
    updateSelectedOpening({
      wall_id: targetWall.wall.id,
      position_along_wall: clamp(
        targetWall.offset - opening.width / 2,
        0,
        Math.max(wallLength(targetWall.wall) - opening.width, 0),
      ),
    });
    setStatus("Opening moved. Save room geometry to persist.");
  }

  const currentWall = selected?.kind === "wall" ? room?.walls.find((item) => item.id === selected.id) : null;
  const currentOpening =
    selected?.kind === "opening" ? room?.openings.find((item) => item.id === selected.id) : null;
  const currentCabinet =
    selected?.kind === "cabinet" ? room?.cabinets.find((item) => item.id === selected.id) : null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">OD Select Drawing Engine</p>
          <h1>treecab studio</h1>
          <p className="hero-text">
            Graphical plan editor for cabinets, walls, openings, and viewport-driven drawing sets.
          </p>
        </div>
        <div className="header-meta">
          <span className="badge">Backend: {backend}</span>
          <button
            type="button"
            className="secondary"
            onClick={() => fetch("/auth/logout", { method: "POST" }).then(() => window.location.replace("/"))}
          >
            Lock Site
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar">
          <section className="panel">
            <div className="section-head">
              <h2>Projects</h2>
              <button type="button" onClick={() => handleCreateProject(false)}>
                New Blank
              </button>
            </div>
            <div className="stack">
              <button type="button" className="ghost" onClick={() => handleCreateProject(true)}>
                New From Sample
              </button>
              <select value={project?.id || ""} onChange={(event) => handleProjectChange(event.target.value)}>
                {projects.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.id}
                  </option>
                ))}
              </select>
            </div>
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Metadata</h2>
              <button type="button" onClick={handleGenerate}>
                Generate
              </button>
            </div>
            {project ? (
              <MetadataForm key={project.id} project={project} onSave={handleSaveMetadata} />
            ) : (
              <p className="empty">No project loaded.</p>
            )}
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
                  <input
                    value={room.label}
                    onChange={(event) =>
                      mutateRoom((target) => {
                        target.label = event.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Ceiling Height
                  <input
                    type="number"
                    step="0.25"
                    value={room.ceiling_height}
                    onChange={(event) =>
                      mutateRoom((target) => {
                        target.ceiling_height = Number(event.target.value);
                      })
                    }
                  />
                </label>
              </div>
            ) : (
              <p className="empty">Choose a room to edit.</p>
            )}
          </section>

          <section className="panel">
            <div className="section-head">
              <h2>Palette</h2>
              <span className="hint">Drag into canvas</span>
            </div>
            <div className="palette-grid">
              {wallPalette.map((item) => (
                <PaletteItem key={item.id} item={item} onDragStart={beginDragItem} />
              ))}
              {openingPalette.map((item) => (
                <PaletteItem key={item.id} item={item} onDragStart={beginDragItem} />
              ))}
            </div>
            <div className="stack top-gap">
              <label>
                Cabinet Preset
                <select value={catalogCode} onChange={(event) => setCatalogCode(event.target.value)}>
                  {catalog
                    .filter((entry) => ["base", "wall", "vanity", "tall"].includes(entry.category))
                    .map((entry) => (
                      <option key={entry.code} value={entry.code}>
                        {entry.code} ({entry.width} x {entry.height})
                      </option>
                    ))}
                </select>
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={catalogUpper}
                  onChange={(event) => setCatalogUpper(event.target.checked)}
                />
                Place as upper cabinet
              </label>
              <PaletteItem
                item={{
                  id: "cabinet",
                  label: `Cabinet ${catalogCode}`,
                  kind: "cabinet",
                  code: catalogCode,
                  isUpper: catalogUpper,
                }}
                onDragStart={beginDragItem}
              />
            </div>
          </section>
        </aside>

        <section className="canvas-column">
          <section className="panel canvas-panel">
            <div className="section-head">
              <div>
                <h2>Plan Canvas</h2>
                <p className="hint">Drag palette items into the stage. Drag endpoints to reshape walls.</p>
              </div>
              <span className={roomDirty ? "dirty-flag active" : "dirty-flag"}>
                {roomDirty ? "Unsaved room changes" : "Room synced"}
              </span>
            </div>
            <div
              ref={stageHostRef}
              className="stage-host"
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleCanvasDrop}
            >
              {room && view ? (
                <Stage
                  width={stageSize.width}
                  height={stageSize.height}
                  onMouseDown={(event) => {
                    if (event.target === event.target.getStage()) {
                      setSelected(null);
                    }
                  }}
                >
                  <Layer>
                    <Rect x={0} y={0} width={stageSize.width} height={stageSize.height} fill="#fcf8f1" />
                    {room.walls.map((wall) => {
                      const start = view.worldToScreen(wall.start);
                      const end = view.worldToScreen(wall.end);
                      const color =
                        wall.status === "new" ? "#6f7862" : wall.status === "to_remove" ? "#d39f5f" : "#231f1a";
                      const isSelected = selected?.kind === "wall" && selected.id === wall.id;
                      return (
                        <Group key={wall.id}>
                          <Line
                            points={[start.x, start.y, end.x, end.y]}
                            stroke={color}
                            strokeWidth={isSelected ? 6 : 4}
                            lineCap="round"
                            onMouseDown={() => setSelected({ kind: "wall", id: wall.id })}
                          />
                          {isSelected && (
                            <>
                              <Circle
                                x={start.x}
                                y={start.y}
                                radius={8}
                                fill="#c85e3d"
                                draggable
                                onDragMove={(event) => {
                                  const world = view.screenToWorld({ x: event.target.x(), y: event.target.y() });
                                  mutateRoom((target) => {
                                    const nextWall = target.walls.find((item) => item.id === wall.id);
                                    if (!nextWall) return;
                                    nextWall.start = {
                                      x: Math.round(world.x * 4) / 4,
                                      y: Math.round(world.y * 4) / 4,
                                    };
                                  });
                                }}
                              />
                              <Circle
                                x={end.x}
                                y={end.y}
                                radius={8}
                                fill="#c85e3d"
                                draggable
                                onDragMove={(event) => {
                                  const world = view.screenToWorld({ x: event.target.x(), y: event.target.y() });
                                  mutateRoom((target) => {
                                    const nextWall = target.walls.find((item) => item.id === wall.id);
                                    if (!nextWall) return;
                                    nextWall.end = {
                                      x: Math.round(world.x * 4) / 4,
                                      y: Math.round(world.y * 4) / 4,
                                    };
                                  });
                                }}
                              />
                            </>
                          )}
                        </Group>
                      );
                    })}
                    {room.openings.map((opening) => {
                      const line = openingScreenLine(opening, room, view);
                      if (!line) return null;
                      const isSelected = selected?.kind === "opening" && selected.id === opening.id;
                      const midX = (line.start.x + line.end.x) / 2;
                      const midY = (line.start.y + line.end.y) / 2;
                      return (
                        <Group key={opening.id}>
                          <Line
                            points={[line.start.x, line.start.y, line.end.x, line.end.y]}
                            stroke="#f5f0e7"
                            strokeWidth={9}
                            lineCap="round"
                            onMouseDown={() => setSelected({ kind: "opening", id: opening.id })}
                          />
                          <Line
                            points={[line.start.x, line.start.y, line.end.x, line.end.y]}
                            stroke="#3f6475"
                            strokeWidth={2}
                            lineCap="round"
                            onMouseDown={() => setSelected({ kind: "opening", id: opening.id })}
                          />
                          <Text
                            x={midX + 6}
                            y={midY - 10}
                            text={opening.kind.toUpperCase()}
                            fontSize={11}
                            fill="#3f6475"
                          />
                          {isSelected && (
                            <Circle
                              x={midX}
                              y={midY}
                              radius={8}
                              fill="#3f6475"
                              draggable
                              onDragEnd={(event) =>
                                moveOpening(opening, { x: event.target.x(), y: event.target.y() })
                              }
                            />
                          )}
                        </Group>
                      );
                    })}
                    {room.cabinets.map((cabinet) => {
                      const rect = cabinetScreenRect(cabinet, room, view, catalogMap);
                      if (!rect) return null;
                      const isSelected = selected?.kind === "cabinet" && selected.id === cabinet.id;
                      return (
                        <Group key={cabinet.id}>
                          <Rect
                            x={rect.x}
                            y={rect.y}
                            width={rect.width}
                            height={rect.height}
                            fill={cabinet.is_upper ? "#f6efe2" : "#ffffff"}
                            stroke={isSelected ? "#c85e3d" : "#29231c"}
                            strokeWidth={isSelected ? 2.2 : 1.2}
                            dash={cabinet.is_upper ? [8, 4] : []}
                            draggable
                            onMouseDown={() => setSelected({ kind: "cabinet", id: cabinet.id })}
                            onDragEnd={(event) =>
                              moveCabinet(cabinet, {
                                x: event.target.x() + rect.width / 2,
                                y: event.target.y() + rect.height / 2,
                              })
                            }
                          />
                          <Text
                            x={rect.x + 6}
                            y={rect.y + rect.height / 2 - 7}
                            text={cabinet.kcd_code}
                            fontSize={11}
                            fill="#29231c"
                            width={Math.max(rect.width - 12, 40)}
                          />
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
              <button type="button" className="danger" onClick={deleteSelectedElement} disabled={!selected}>
                Delete
              </button>
            </div>
            {!selected && <p className="empty">Select a wall, opening, or cabinet.</p>}
            {currentWall && (
              <div className="stack">
                <p className="inspector-title">Wall {currentWall.id}</p>
                <label>
                  Status
                  <select
                    value={currentWall.status}
                    onChange={(event) => updateSelectedWall({ status: event.target.value })}
                  >
                    <option value="existing">existing</option>
                    <option value="new">new</option>
                    <option value="to_remove">to_remove</option>
                  </select>
                </label>
                <p className="hint">Drag the red endpoints to reshape this wall.</p>
              </div>
            )}
            {currentOpening && (
              <div className="stack">
                <p className="inspector-title">Opening {currentOpening.id}</p>
                <label>
                  Kind
                  <select
                    value={currentOpening.kind}
                    onChange={(event) => updateSelectedOpening({ kind: event.target.value })}
                  >
                    <option value="door">door</option>
                    <option value="window">window</option>
                    <option value="cased">cased</option>
                  </select>
                </label>
                <label>
                  Width
                  <input
                    type="number"
                    step="0.25"
                    value={currentOpening.width}
                    onChange={(event) => updateSelectedOpening({ width: Number(event.target.value) })}
                  />
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(currentOpening.verify_in_field)}
                    onChange={(event) => updateSelectedOpening({ verify_in_field: event.target.checked })}
                  />
                  Verify in field
                </label>
              </div>
            )}
            {currentCabinet && (
              <div className="stack">
                <p className="inspector-title">Cabinet {currentCabinet.id}</p>
                <label>
                  Code
                  <select
                    value={getBaseCode(currentCabinet.kcd_code)}
                    onChange={(event) => updateSelectedCabinet({ kcd_code: event.target.value })}
                    disabled={roomDirty}
                  >
                    {catalog
                      .filter((entry) => ["base", "wall", "vanity", "tall"].includes(entry.category))
                      .map((entry) => (
                        <option key={entry.code} value={entry.code}>
                          {entry.code}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={Boolean(currentCabinet.is_upper)}
                    onChange={(event) => updateSelectedCabinet({ is_upper: event.target.checked })}
                    disabled={roomDirty}
                  />
                  Upper cabinet
                </label>
                <p className="hint">Drag the cabinet block to relocate it along the nearest wall.</p>
              </div>
            )}
          </section>

          <section className="panel preview-panel">
            <div className="section-head">
              <h2>Outputs</h2>
              <div className="inline-actions">
                <button type="button" className="ghost" onClick={handleGenerate}>
                  Refresh Output
                </button>
                {generation?.pdf_url && (
                  <a href={generation.pdf_url} target="_blank" rel="noreferrer">
                    PDF
                  </a>
                )}
                {generation?.tsv_url && (
                  <a href={generation.tsv_url} target="_blank" rel="noreferrer">
                    TSV
                  </a>
                )}
              </div>
            </div>
            <p className="status-line">{status}</p>
            {generation?.sheet_urls ? (
              <iframe
                title="Sheet preview"
                src={`${generation.sheet_urls["A-02"] || Object.values(generation.sheet_urls)[0]}?t=${Date.now()}`}
              />
            ) : (
              <div className="empty preview-empty">Generate a drawing set to load the preview.</div>
            )}
          </section>
        </section>
      </main>
    </div>
  );
}
