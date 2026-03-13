# OD Select Drawing Engine Spec Card

Date: 2026-03-13
Status: Approved for execution
Owner: Codex

## Objective

Replace the current numeric room editor with a graphical plan editor where the user can drag and drop preset walls, doors, windows, cabinets, appliances, annotations, and detail symbols into a canvas. The same scene data must drive both the on-screen viewport and the final PDF output.

## Source Of Truth

- Original implementation spec: `docs/research/260313 OD Select Drawing Engine Claude Code Spec.md`
- Original research report: `docs/research/260313 OD Select Drawing Engine Research.md`
- Current repo review: 2026-03-13 review against `main`
- Verified external sources:
  - https://github.com/konvajs/konva
  - https://github.com/konvajs/react-konva
  - https://github.com/tldraw/tldraw

## Product Decisions

1. Use React + `react-konva` for the editor canvas.
2. Do not use `tldraw` as the base editor SDK.
   Reason: its current SDK license imposes watermark or business-license constraints, which is a poor fit for this repo.
3. Treat the current static form editor as temporary and replace it.
4. Treat the current JPG-template overlay renderer as temporary and retire it.
5. Make scene JSON the shared contract between editor, preview, and PDF generation.

## Required Outcomes

1. User can draw or drag room geometry on a canvas instead of typing wall endpoint values.
2. User can place and move openings and cabinets visually.
3. User can place all plan-view elements needed for A-01 through A-04.
4. Preview viewport is generated from the same scene graph used for PDF output.
5. Final PDF no longer depends on raster screenshots of sample sheets.

## Scene Model

The execution target is a scene-based model, not a form-only room payload.

Core element types:

- `wall`
- `opening.door`
- `opening.window`
- `opening.cased`
- `cabinet.base`
- `cabinet.wall`
- `cabinet.tall`
- `cabinet.vanity`
- `appliance`
- `annotation`
- `dimension`
- `roomTag`
- `detailSymbol`
- `viewport`

Minimum element fields:

- `id`
- `type`
- `x`
- `y`
- `width`
- `height`
- `rotation`
- `metadata`

Domain-specific fields remain in `metadata` until the model is fully normalized.

## Execution Phases

### Phase 1: Editor foundation

- Create a build-based frontend app.
- Add React + `react-konva`.
- Introduce scene state, selection state, and palette definitions.
- Render a stage with pan, zoom, drag, and transform support.
- Keep existing project CRUD working while adapting payloads incrementally.

### Phase 2: Plan authoring

- Add wall, opening, and cabinet placement tools.
- Add snapping and wall attachment rules.
- Replace room geometry tables with canvas editing.
- Add sidebar properties for selected elements.

### Phase 3: Shared rendering contract

- Generate preview from scene JSON, not a placeholder SVG.
- Move PDF generation to consume scene JSON.
- Remove raster sheet screenshots and hard-coded whiteout rectangles.

### Phase 4: Drawing fidelity

- Rebuild title block, legend, notes, dimensions, and details from data.
- Support A-01 through D-01 sheet composition without embedded sample imagery.

### Phase 5: Workflow and imports

- Add A.1 to A.4 workflow states properly.
- Add verified-dimension workflow instead of synthetic flags.
- Add CubiCasa and photo import only after the editor contract is stable.

## Immediate Execution Slice

This turn begins Phase 1.

Deliverables:

1. Frontend scaffold for React + `react-konva`
2. Scene data model and palette definitions
3. Canvas shell with selection and drag behavior
4. Initial replacement path for the current room form editor

## Acceptance Criteria

- The repo contains a committed spec card for the execution plan.
- The repo has a React canvas editor scaffold wired into the app.
- A user can place at least one preset wall, one opening, and one cabinet visually.
- The codebase has tests or checks covering the new scene foundation.

## Risks

- Migrating from static HTML to a built frontend changes app serving behavior.
- The current backend payloads are wall-centric and need an adapter layer during migration.
- PDF parity should not be claimed until the preview and PDF use the same scene contract.

## Explicit Non-Goals For The First Slice

- Full SolveSpace integration
- Full Typst sheet composition
- CubiCasa import
- AI layout detection
- D-01 fidelity

These remain in scope for later phases, but they do not block starting the graphical editor foundation now.
