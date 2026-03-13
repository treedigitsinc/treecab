export async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 401) {
    window.location.replace("/");
    throw new Error("Unauthorized");
  }
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

export function loadCatalog() {
  return api("/api/catalog");
}

export function loadStatus() {
  return api("/api/status");
}

export function loadProjects() {
  return api("/api/projects");
}

export function loadProject(projectId) {
  return api(`/api/projects/${projectId}`);
}

export function createProject(payload) {
  return api("/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProject(projectId, payload) {
  return api(`/api/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function saveRoom(projectId, roomId, payload) {
  return api(`/api/projects/${projectId}/rooms/${roomId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function addCabinet(projectId, payload) {
  return api(`/api/projects/${projectId}/cabinets`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCabinet(projectId, cabinetId, payload) {
  return api(`/api/projects/${projectId}/cabinets/${cabinetId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteCabinet(projectId, cabinetId) {
  return api(`/api/projects/${projectId}/cabinets/${cabinetId}`, {
    method: "DELETE",
  });
}

export function generateDrawingSet(projectId) {
  return api(`/api/projects/${projectId}/generate-cd`, {
    method: "POST",
  });
}
