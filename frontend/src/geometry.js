const PADDING = 64;
const ENDPOINT_EPSILON = 0.01;
const DRAFT_AXIS_RATIO = 1.75;

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function wallLength(wall) {
  return Math.hypot(wall.end.x - wall.start.x, wall.end.y - wall.start.y);
}

export function pointDistance(first, second) {
  return Math.hypot((second?.x || 0) - (first?.x || 0), (second?.y || 0) - (first?.y || 0));
}

export function pointAtWallOffset(wall, offset) {
  const length = wallLength(wall) || 1;
  const ratio = offset / length;
  return {
    x: wall.start.x + (wall.end.x - wall.start.x) * ratio,
    y: wall.start.y + (wall.end.y - wall.start.y) * ratio,
  };
}

export function roomBounds(room) {
  const xs = room.walls.flatMap((wall) => [wall.start.x, wall.end.x]);
  const ys = room.walls.flatMap((wall) => [wall.start.y, wall.end.y]);
  const minX = Math.min(...xs, 0);
  const minY = Math.min(...ys, 0);
  const maxX = Math.max(...xs, 120);
  const maxY = Math.max(...ys, 120);
  return { minX, minY, maxX, maxY };
}

export function createView(room, width, height, camera = {}) {
  const bounds = roomBounds(room);
  const worldWidth = Math.max(bounds.maxX - bounds.minX, 1);
  const worldHeight = Math.max(bounds.maxY - bounds.minY, 1);
  const zoom = camera.zoom || 1;
  const panX = camera.panX || 0;
  const panY = camera.panY || 0;
  const baseScale = Math.min((width - PADDING * 2) / worldWidth, (height - PADDING * 2) / worldHeight);
  const scale = baseScale * zoom;
  const offsetX = ((width - worldWidth * scale) / 2) + panX;
  const offsetY = ((height - worldHeight * scale) / 2) + panY;
  return {
    bounds,
    zoom,
    scale,
    worldToScreen(point) {
      return {
        x: offsetX + (point.x - bounds.minX) * scale,
        y: offsetY + (point.y - bounds.minY) * scale,
      };
    },
    screenToWorld(point) {
      return {
        x: bounds.minX + (point.x - offsetX) / scale,
        y: bounds.minY + (point.y - offsetY) / scale,
      };
    },
  };
}

export function wallOrientation(wall, bounds) {
  const dx = Math.abs(wall.end.x - wall.start.x);
  const dy = Math.abs(wall.end.y - wall.start.y);
  if (dx >= dy) {
    return wall.start.y >= bounds.maxY ? "top" : "bottom";
  }
  return wall.start.x >= bounds.maxX ? "right" : "left";
}

export function projectPointToWall(point, wall) {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const lengthSquared = dx * dx + dy * dy || 1;
  const raw = ((point.x - wall.start.x) * dx + (point.y - wall.start.y) * dy) / lengthSquared;
  const ratio = clamp(raw, 0, 1);
  const projected = {
    x: wall.start.x + dx * ratio,
    y: wall.start.y + dy * ratio,
  };
  return {
    point: projected,
    offset: ratio * wallLength(wall),
    distance: Math.hypot(projected.x - point.x, projected.y - point.y),
  };
}

export function alignDraftPoint(point, anchor, axisRatio = DRAFT_AXIS_RATIO) {
  if (!anchor) return point;
  const dx = point.x - anchor.x;
  const dy = point.y - anchor.y;
  if (Math.abs(dx) >= Math.abs(dy) * axisRatio) {
    return { x: point.x, y: anchor.y };
  }
  if (Math.abs(dy) >= Math.abs(dx) * axisRatio) {
    return { x: anchor.x, y: point.y };
  }
  return point;
}

export function nearestWallEndpoint(point, room, excludedWallId = null) {
  let best = null;
  for (const wall of room.walls) {
    if (wall.id === excludedWallId) continue;
    for (const endpointKey of ["start", "end"]) {
      const candidatePoint = wall[endpointKey];
      const distance = pointDistance(point, candidatePoint);
      if (!best || distance < best.distance) {
        best = { wall, endpointKey, point: candidatePoint, distance };
      }
    }
  }
  return best;
}

export function snapWallPoint(point, anchor, room, excludedWallId = null, joinDistance = 8) {
  const aligned = alignDraftPoint(point, anchor);
  const endpoint = nearestWallEndpoint(aligned, room, excludedWallId);
  if (endpoint && endpoint.distance <= joinDistance) {
    return { x: endpoint.point.x, y: endpoint.point.y };
  }
  return aligned;
}

export function nearestWall(point, room) {
  let best = null;
  for (const wall of room.walls) {
    const candidate = projectPointToWall(point, wall);
    if (!best || candidate.distance < best.distance) {
      best = { ...candidate, wall };
    }
  }
  return best;
}

export function wallUnitVectors(wall, view) {
  const start = view.worldToScreen(wall.start);
  const end = view.worldToScreen(wall.end);
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.hypot(dx, dy) || 1;
  return {
    start,
    end,
    tangent: { x: dx / length, y: dy / length },
    normal: { x: -dy / length, y: dx / length },
  };
}

function pointsMatch(first, second, epsilon = ENDPOINT_EPSILON) {
  return Math.abs(first.x - second.x) <= epsilon && Math.abs(first.y - second.y) <= epsilon;
}

function wallDirection(wall) {
  const length = wallLength(wall);
  if (!length) return null;
  return {
    x: (wall.end.x - wall.start.x) / length,
    y: (wall.end.y - wall.start.y) / length,
  };
}

function wallEndpointExtension(wall, room, endpointKey) {
  const direction = wallDirection(wall);
  if (!direction) return 0;
  const anchor = endpointKey === "start" ? wall.start : wall.end;
  let extension = 0;

  for (const candidate of room.walls) {
    if (candidate.id === wall.id) continue;
    if (!pointsMatch(anchor, candidate.start) && !pointsMatch(anchor, candidate.end)) continue;
    const candidateDirection = wallDirection(candidate);
    if (!candidateDirection) continue;
    const dot = Math.abs(direction.x * candidateDirection.x + direction.y * candidateDirection.y);
    if (dot > 0.98) continue;
    extension = Math.max(extension, Math.max(wall.thickness || 4.5, candidate.thickness || 4.5) / 2);
  }

  return extension;
}

export function polygonBounds(points) {
  const xs = [];
  const ys = [];
  for (let index = 0; index < points.length; index += 2) {
    xs.push(points[index]);
    ys.push(points[index + 1]);
  }
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

export function wallPolygon(wall, room, view) {
  const { start, end, tangent, normal } = wallUnitVectors(wall, view);
  const halfThickness = Math.max((wall.thickness || 4.5) * view.scale, 12) / 2;
  const startExtension = wallEndpointExtension(wall, room, "start") * view.scale;
  const endExtension = wallEndpointExtension(wall, room, "end") * view.scale;
  const extendedStart = {
    x: start.x - tangent.x * startExtension,
    y: start.y - tangent.y * startExtension,
  };
  const extendedEnd = {
    x: end.x + tangent.x * endExtension,
    y: end.y + tangent.y * endExtension,
  };
  const points = [
    extendedStart.x - normal.x * halfThickness,
    extendedStart.y - normal.y * halfThickness,
    extendedEnd.x - normal.x * halfThickness,
    extendedEnd.y - normal.y * halfThickness,
    extendedEnd.x + normal.x * halfThickness,
    extendedEnd.y + normal.y * halfThickness,
    extendedStart.x + normal.x * halfThickness,
    extendedStart.y + normal.y * halfThickness,
  ];
  return {
    points,
    bounds: polygonBounds(points),
    thickness: halfThickness * 2,
  };
}

export function interiorNormalForWall(wall, room) {
  const bounds = roomBounds(room);
  const orientation = wallOrientation(wall, bounds);
  if (orientation === "top") return { x: 0, y: -1 };
  if (orientation === "bottom") return { x: 0, y: 1 };
  if (orientation === "right") return { x: -1, y: 0 };
  return { x: 1, y: 0 };
}

export function openingScreenGeometry(opening, room, view) {
  const wall = room.walls.find((candidate) => candidate.id === opening.wall_id);
  if (!wall) return null;
  const start = view.worldToScreen(pointAtWallOffset(wall, opening.position_along_wall));
  const end = view.worldToScreen(pointAtWallOffset(wall, opening.position_along_wall + opening.width));
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.hypot(dx, dy) || 1;
  const tangent = { x: dx / length, y: dy / length };
  const normal = { x: -tangent.y, y: tangent.x };
  const interior = interiorNormalForWall(wall, room);
  const thickness = Math.max((wall.thickness || 4.5) * view.scale, 12);
  const center = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
  const gap = [
    start.x - normal.x * (thickness / 2),
    start.y - normal.y * (thickness / 2),
    end.x - normal.x * (thickness / 2),
    end.y - normal.y * (thickness / 2),
    end.x + normal.x * (thickness / 2),
    end.y + normal.y * (thickness / 2),
    start.x + normal.x * (thickness / 2),
    start.y + normal.y * (thickness / 2),
  ];
  return {
    wall,
    start,
    end,
    center,
    tangent,
    normal,
    interior,
    thickness,
    gap,
  };
}

export function sampleArcPoints(center, radius, startAngle, endAngle, steps = 18) {
  const points = [];
  for (let index = 0; index <= steps; index += 1) {
    const angle = startAngle + ((endAngle - startAngle) * index) / steps;
    points.push(center.x + Math.cos(angle) * radius, center.y + Math.sin(angle) * radius);
  }
  return points;
}

export function getBaseCode(code) {
  const parts = String(code).split("-");
  if (parts.length > 1 && parts[0].length <= 3) {
    return parts.slice(1).join("-");
  }
  return code;
}

export function cabinetScreenRect(cabinet, room, view, catalogMap) {
  const wall = room.walls.find((candidate) => candidate.id === cabinet.wall_id);
  if (!wall) return null;
  const bounds = roomBounds(room);
  const entry = catalogMap[getBaseCode(cabinet.kcd_code)];
  if (!entry) return null;
  const start = view.worldToScreen(pointAtWallOffset(wall, cabinet.offset_from_wall_start));
  const end = view.worldToScreen(pointAtWallOffset(wall, cabinet.offset_from_wall_start + entry.width));
  const depth = Math.max(entry.depth * view.scale, 20);
  const orientation = wallOrientation(wall, bounds);

  if (orientation === "top") {
    return { x: Math.min(start.x, end.x), y: start.y - depth, width: Math.abs(end.x - start.x), height: depth };
  }
  if (orientation === "bottom") {
    return { x: Math.min(start.x, end.x), y: start.y, width: Math.abs(end.x - start.x), height: depth };
  }
  if (orientation === "right") {
    return { x: start.x - depth, y: Math.min(start.y, end.y), width: depth, height: Math.abs(end.y - start.y) };
  }
  return { x: start.x, y: Math.min(start.y, end.y), width: depth, height: Math.abs(end.y - start.y) };
}
