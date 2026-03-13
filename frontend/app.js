const state = {
  catalog: [],
  colors: {},
  projects: [],
  project: null,
  currentRoomId: null,
  selectedCabinetId: null,
  generation: null,
};

const qs = (selector) => document.querySelector(selector);

function setStatus(message) {
  qs("#status").textContent = message;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function currentRoom() {
  return state.project?.rooms.find((room) => room.id === state.currentRoomId) || null;
}

function populateProjectForm() {
  if (!state.project) return;
  const form = qs("#project-form");
  for (const field of ["address", "kcd_color", "kcd_style", "drawer_type", "uppers_height", "crown_molding", "designer"]) {
    form.elements[field].value = state.project[field] ?? "";
  }
}

function renderProjectSelect() {
  const select = qs("#project-select");
  select.innerHTML = "";
  state.projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = `${project.id} - ${project.address}`;
    if (state.project && state.project.id === project.id) option.selected = true;
    select.appendChild(option);
  });
}

function renderRoomSelect() {
  const select = qs("#room-select");
  select.innerHTML = "";
  if (!state.project) return;
  state.project.rooms.forEach((room) => {
    const option = document.createElement("option");
    option.value = room.id;
    option.textContent = `${String(room.room_number).padStart(2, "0")} ${room.label}`;
    if (room.id === state.currentRoomId) option.selected = true;
    select.appendChild(option);
  });
}

function renderWalls() {
  const room = currentRoom();
  const tbody = qs("#walls-body");
  tbody.innerHTML = "";
  if (!room) return;
  qs("#room-label").value = room.label;
  qs("#room-type").value = room.room_type;
  qs("#room-ceiling").value = room.ceiling_height;
  room.walls.forEach((wall) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${wall.id}</td>
      <td><input data-field="start.x" data-id="${wall.id}" value="${wall.start.x}" /></td>
      <td><input data-field="start.y" data-id="${wall.id}" value="${wall.start.y}" /></td>
      <td><input data-field="end.x" data-id="${wall.id}" value="${wall.end.x}" /></td>
      <td><input data-field="end.y" data-id="${wall.id}" value="${wall.end.y}" /></td>
      <td>
        <select data-field="status" data-id="${wall.id}">
          <option value="existing" ${wall.status === "existing" ? "selected" : ""}>existing</option>
          <option value="to_remove" ${wall.status === "to_remove" ? "selected" : ""}>to_remove</option>
          <option value="new" ${wall.status === "new" ? "selected" : ""}>new</option>
        </select>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderOpenings() {
  const room = currentRoom();
  const tbody = qs("#openings-body");
  tbody.innerHTML = "";
  if (!room) return;
  room.openings.forEach((opening) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input data-opening="${opening.id}" data-field="id" value="${opening.id}" /></td>
      <td><select data-opening="${opening.id}" data-field="wall_id">${room.walls
        .map((wall) => `<option value="${wall.id}" ${wall.id === opening.wall_id ? "selected" : ""}>${wall.id}</option>`)
        .join("")}</select></td>
      <td><select data-opening="${opening.id}" data-field="kind">
          <option value="door" ${opening.kind === "door" ? "selected" : ""}>door</option>
          <option value="window" ${opening.kind === "window" ? "selected" : ""}>window</option>
          <option value="cased" ${opening.kind === "cased" ? "selected" : ""}>cased</option>
      </select></td>
      <td><input data-opening="${opening.id}" data-field="position_along_wall" value="${opening.position_along_wall}" /></td>
      <td><input data-opening="${opening.id}" data-field="width" value="${opening.width}" /></td>
      <td><input type="checkbox" data-opening="${opening.id}" data-field="verify_in_field" ${opening.verify_in_field ? "checked" : ""} /></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCabinetControls() {
  const room = currentRoom();
  const wallSelect = qs("#cabinet-wall");
  wallSelect.innerHTML = "";
  qs("#cabinet-list").innerHTML = "";
  if (!room) return;
  room.walls.forEach((wall) => {
    const option = document.createElement("option");
    option.value = wall.id;
    option.textContent = wall.id;
    wallSelect.appendChild(option);
  });
  room.cabinets.forEach((cabinet) => {
    const option = document.createElement("option");
    option.value = cabinet.id;
    option.textContent = `${cabinet.kcd_code} @ ${cabinet.wall_id} + ${cabinet.offset_from_wall_start}"`;
    if (cabinet.id === state.selectedCabinetId) option.selected = true;
    qs("#cabinet-list").appendChild(option);
  });
}

function renderSheetSelect() {
  const select = qs("#sheet-select");
  select.innerHTML = "";
  if (!state.project) return;
  state.project.sheets.forEach((sheet) => {
    const option = document.createElement("option");
    option.value = sheet.sheet_number;
    option.textContent = `${sheet.sheet_number} ${sheet.title}`;
    select.appendChild(option);
  });
}

function renderCatalogSelect() {
  const select = qs("#cabinet-code");
  select.innerHTML = "";
  state.catalog
    .filter((entry) => ["base", "wall", "vanity", "tall"].includes(entry.category))
    .forEach((entry) => {
      const option = document.createElement("option");
      option.value = entry.code;
      option.textContent = `${entry.code} (${entry.width}x${entry.height})`;
      select.appendChild(option);
    });
}

function renderAll() {
  renderProjectSelect();
  populateProjectForm();
  renderRoomSelect();
  renderWalls();
  renderOpenings();
  renderCabinetControls();
  renderSheetSelect();
}

async function loadCatalog() {
  const response = await api("/api/catalog");
  state.catalog = response.entries;
  state.colors = response.colors;
  renderCatalogSelect();
}

async function loadStatus() {
  const response = await api("/api/status");
  qs("#backend-badge").textContent = `Backend: ${response.backend}`;
}

async function loadProjects(preferredId = null) {
  state.projects = await api("/api/projects");
  renderProjectSelect();
  const projectId = preferredId || state.project?.id || state.projects[0]?.id;
  if (projectId) {
    await loadProject(projectId);
  }
}

async function loadProject(projectId) {
  state.project = await api(`/api/projects/${projectId}`);
  state.currentRoomId = state.project.rooms[0]?.id || null;
  state.selectedCabinetId = null;
  renderAll();
  await generateAndRefresh(false);
}

function gatherRoomPayload() {
  const room = structuredClone(currentRoom());
  room.label = qs("#room-label").value;
  room.room_type = qs("#room-type").value;
  room.ceiling_height = Number(qs("#room-ceiling").value);
  room.walls = room.walls.map((wall) => {
    wall.start.x = Number(document.querySelector(`[data-id="${wall.id}"][data-field="start.x"]`).value);
    wall.start.y = Number(document.querySelector(`[data-id="${wall.id}"][data-field="start.y"]`).value);
    wall.end.x = Number(document.querySelector(`[data-id="${wall.id}"][data-field="end.x"]`).value);
    wall.end.y = Number(document.querySelector(`[data-id="${wall.id}"][data-field="end.y"]`).value);
    wall.status = document.querySelector(`[data-id="${wall.id}"][data-field="status"]`).value;
    return wall;
  });
  room.openings = room.openings.map((opening) => ({
    ...opening,
    id: document.querySelector(`[data-opening="${opening.id}"][data-field="id"]`).value,
    wall_id: document.querySelector(`[data-opening="${opening.id}"][data-field="wall_id"]`).value,
    kind: document.querySelector(`[data-opening="${opening.id}"][data-field="kind"]`).value,
    position_along_wall: Number(document.querySelector(`[data-opening="${opening.id}"][data-field="position_along_wall"]`).value),
    width: Number(document.querySelector(`[data-opening="${opening.id}"][data-field="width"]`).value),
    verify_in_field: document.querySelector(`[data-opening="${opening.id}"][data-field="verify_in_field"]`).checked,
  }));
  return room;
}

async function saveProjectMetadata() {
  const form = qs("#project-form");
  state.project = await api(`/api/projects/${state.project.id}`, {
    method: "PUT",
    body: JSON.stringify({
      address: form.elements.address.value,
      kcd_color: form.elements.kcd_color.value,
      kcd_style: form.elements.kcd_style.value,
      drawer_type: form.elements.drawer_type.value,
      uppers_height: Number(form.elements.uppers_height.value),
      crown_molding: form.elements.crown_molding.value,
      designer: form.elements.designer.value,
      use_sample: false,
    }),
  });
  renderAll();
  await generateAndRefresh();
}

async function saveRoom() {
  const payload = gatherRoomPayload();
  state.project = await api(`/api/projects/${state.project.id}/rooms/${state.currentRoomId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  renderAll();
  await generateAndRefresh();
}

async function generateAndRefresh(showMessage = true) {
  if (!state.project) return;
  if (showMessage) setStatus("Generating previews…");
  state.generation = await api(`/api/projects/${state.project.id}/generate-cd`, { method: "POST" });
  renderSheetSelect();
  const selectedSheet = qs("#sheet-select").value || state.project.sheets[0]?.sheet_number;
  if (selectedSheet) {
    qs("#preview-frame").src = `${state.generation.sheet_urls[selectedSheet]}?t=${Date.now()}`;
  }
  qs("#pdf-link").href = state.generation.pdf_url;
  qs("#tsv-link").href = state.generation.tsv_url;
  setStatus(`Generated ${Object.keys(state.generation.sheet_urls).length} sheets.`);
}

async function createProject(useSample) {
  const form = qs("#project-form");
  const created = await api("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      address: form.elements.address.value || "New Project",
      kcd_color: form.elements.kcd_color.value || "BW",
      kcd_style: form.elements.kcd_style.value || "Brooklyn White",
      drawer_type: form.elements.drawer_type.value || "5-piece",
      uppers_height: Number(form.elements.uppers_height.value || 36),
      crown_molding: form.elements.crown_molding.value || "Flat",
      designer: form.elements.designer.value || "LOCAL",
      use_sample: useSample,
    }),
  });
  await loadProjects(created.id);
}

async function addCabinet() {
  const room = currentRoom();
  if (!room) return;
  state.project = await api(`/api/projects/${state.project.id}/cabinets`, {
    method: "POST",
    body: JSON.stringify({
      kcd_code: qs("#cabinet-code").value,
      wall_id: qs("#cabinet-wall").value,
      offset_from_wall_start: Number(qs("#cabinet-offset").value || 0),
      is_upper: qs("#cabinet-upper").checked,
      hinge_side: "None",
      orientation: "standard",
      modifications: [],
    }),
  });
  state.currentRoomId = room.id;
  renderAll();
  await generateAndRefresh();
}

async function updateCabinet() {
  if (!state.selectedCabinetId) return;
  state.project = await api(`/api/projects/${state.project.id}/cabinets/${state.selectedCabinetId}`, {
    method: "PUT",
    body: JSON.stringify({
      id: state.selectedCabinetId,
      kcd_code: qs("#cabinet-code").value,
      wall_id: qs("#cabinet-wall").value,
      offset_from_wall_start: Number(qs("#cabinet-offset").value || 0),
      is_upper: qs("#cabinet-upper").checked,
      hinge_side: "None",
      orientation: "standard",
      modifications: [],
    }),
  });
  renderAll();
  await generateAndRefresh();
}

async function deleteCabinet() {
  if (!state.selectedCabinetId) return;
  state.project = await api(`/api/projects/${state.project.id}/cabinets/${state.selectedCabinetId}`, {
    method: "DELETE",
  });
  state.selectedCabinetId = null;
  renderAll();
  await generateAndRefresh();
}

function attachEvents() {
  qs("#refresh-projects").addEventListener("click", () => loadProjects());
  qs("#project-select").addEventListener("change", (event) => loadProject(event.target.value));
  qs("#room-select").addEventListener("change", (event) => {
    state.currentRoomId = event.target.value;
    state.selectedCabinetId = null;
    renderAll();
  });
  qs("#project-form").addEventListener("submit", (event) => {
    event.preventDefault();
    saveProjectMetadata().catch((error) => setStatus(error.message));
  });
  qs("#save-room-btn").addEventListener("click", () => saveRoom().catch((error) => setStatus(error.message)));
  qs("#new-sample-btn").addEventListener("click", () => createProject(true).catch((error) => setStatus(error.message)));
  qs("#new-blank-btn").addEventListener("click", () => createProject(false).catch((error) => setStatus(error.message)));
  qs("#add-opening-btn").addEventListener("click", () => {
    const room = currentRoom();
    if (!room) return;
    room.openings.push({
      id: `opening-${Date.now()}`,
      wall_id: room.walls[0].id,
      kind: "door",
      position_along_wall: 0,
      width: 30,
      height: 0,
      sill_height: 0,
      trim_width: 3.5,
      verify_in_field: false,
    });
    renderOpenings();
  });
  qs("#generate-btn").addEventListener("click", () => generateAndRefresh().catch((error) => setStatus(error.message)));
  qs("#sheet-select").addEventListener("change", (event) => {
    if (!state.generation) return;
    qs("#preview-frame").src = `${state.generation.sheet_urls[event.target.value]}?t=${Date.now()}`;
  });
  qs("#cabinet-list").addEventListener("change", (event) => {
    state.selectedCabinetId = event.target.value;
    const room = currentRoom();
    const cabinet = room?.cabinets.find((item) => item.id === state.selectedCabinetId);
    if (!cabinet) return;
    const baseCode = cabinet.kcd_code.includes("-") ? cabinet.kcd_code.split("-").slice(1).join("-") : cabinet.kcd_code;
    qs("#cabinet-code").value = baseCode;
    qs("#cabinet-wall").value = cabinet.wall_id;
    qs("#cabinet-offset").value = cabinet.offset_from_wall_start;
    qs("#cabinet-upper").checked = cabinet.is_upper;
  });
  qs("#add-cabinet-btn").addEventListener("click", () => addCabinet().catch((error) => setStatus(error.message)));
  qs("#update-cabinet-btn").addEventListener("click", () => updateCabinet().catch((error) => setStatus(error.message)));
  qs("#delete-cabinet-btn").addEventListener("click", () => deleteCabinet().catch((error) => setStatus(error.message)));
}

async function boot() {
  attachEvents();
  await loadStatus();
  await loadCatalog();
  await loadProjects();
}

boot().catch((error) => setStatus(error.message));
