# OD Select Drawing Engine — Architecture & Technology Research Report

**Date:** March 13, 2026  
**Prepared for:** treedigits Inc. / Opendoor  
**Author:** Claude (Anthropic) on behalf of Julian Zaraza  

---

## 1. Executive Summary

This report evaluates the open-source landscape for building a custom 2D parametric construction drawing application tailored to Opendoor's OD Select kitchen/bath cabinetry workflow. The target is a tool that produces multi-page PDF drawing sets (CP-00, A-01 through A-04, D-01) matching current production output, with AI-assisted layout from CubiCasa PDFs and room photos, parametric cabinet placement against the KCD catalog, and automated TSV export for cabinet ordering.

**Recommended stack:** Python backend (FastAPI) + SolveSpace constraint solver (via `python-solvespace`) + Cairo/Pango for 2D rendering + Typst for PDF sheet composition + Claude API for AI layout intelligence + React frontend for web editor.

---

## 2. Current Workflow Analysis

### Process Steps (A.1 → A.4)

| Step | Input | Output | Current SLA |
|------|-------|--------|-------------|
| A.1 Initial Request | Address, project type, KCD color/style, drawer type, uppers height, crown molding, CubiCasa PDF, room photos | — | — |
| A.2 Bid Drawings | A.1 data | PDF: Demo Plan (A-01) + New Construction Plan with red VIF dims (A-02) + Bathroom Vanities (A-03/A-04) + Details (D-01) + Cover (CP-00) | ~1 business day |
| A.3 Dimension Confirmation | Marked-up bid drawings with verified red dims | — | ~5 business days (Opendoor) |
| A.4 Construction Drawings | Confirmed dims | PDF: same sheet set with KCD cabinet tags (OW-W2436, OW-B24, etc.) + TSV/CSV for ordering | ~1 business day |

### Drawing Set Structure (per project)

| Sheet | Title | Scale | Content |
|-------|-------|-------|---------|
| CP-00 | Measurement Guide / Cover | — | Opendoor branding, measurement instructions, measurement example diagram |
| A-01 | Demo Kitchen Plan | 1/2" = 1'-0" | Existing walls, walls to remove (hatched), existing cabinetry to remove, appliance locations (DW, REF, WO), room labels |
| A-02 | New Kitchen Layout | 1/2" = 1'-0" | New walls, cabinet layout with KCD tags, appliance placement, red VIF dimensions, ceiling height, notes sidebar |
| A-03 | Demo/New Main Bathroom | 1/2" = 1'-0" | Demo and new layout side-by-side, vanity tags (OO-VSBDL30, OO-VSBDR30) |
| A-04 | Demo/New Secondary Bathroom | 1/2" = 1'-0" | Same as A-03 for secondary bath |
| D-01 | Details | As indicated | Kitchen cabinet sections, bathroom typical details, plumbing accessory heights, niche details, shower fixtures, hardware placement, crown molding |

### Title Block Fields

Every sheet includes: Company logo, Date, Designer status (YES/NO), Drawing purpose (FOR BID / FOR CONSTRUCTION), Scale, Street Address, Sheet Number (CP-00, A-01, etc.).

### KCD Cabinet Catalog Structure

The KCD catalog (March 2026 edition) defines cabinet codes using this naming convention:

- **Wall cabinets:** `W{width}{height}` (e.g., W2436 = 24"W × 36"H × 12"D standard)
- **Base cabinets:** `B{width}` (e.g., B30 = 30"W × 34.5"H × 24"D)
- **Sink base:** `SB{width}` (e.g., SB36)
- **Drawer base:** `DB{width}-{drawers}` (e.g., DB24-3 = 3-drawer)
- **Tall/Pantry:** `P{width}{height}` (e.g., P2496)
- **Vanity:** `V{width}` or `VSBDL{width}` / `VSBDR{width}` (left/right sink base)
- **Blind cabinets:** `BW{width}` (wall) / `BB{width}` (base)
- **Prefix by color:** OW- (Oslo White), BW- (Brooklyn White), SK- (Shaker Kodiak), EW- (Essential White), etc.

Cabinet lines: Premier Series (Oslo, Shaker, Brooklyn — full overlay, plywood box) and Builder Series (Essential — partial overlay, engineered wood).

TSV export fields: #, Qty, Manuf. code, Width, Height, Depth, Left-Right, Price, Hng (hinge side).

---

## 3. Open-Source Technology Landscape

### 3.1 Parametric Constraint Solvers

| Tool | Language | License | Maturity | Suitability |
|------|----------|---------|----------|-------------|
| **SolveSpace / libslvs** | C++ (Python bindings via `python-solvespace`) | GPL v3 | High — used in FreeCAD Assembly3 | **Best fit.** Isolated solver library, proven 2D constraint system, Python bindings on PyPI |
| JSketcher | TypeScript | MIT | Medium | Web-native but solver less proven than SolveSpace |
| GeoSolver | Python | GPL | Low | Academic, not production-ready |
| NeoGeoSolver.NET | C# | — | Low | Unity-oriented, not suitable for server-side |
| FreeCAD Sketcher | C++/Python | LGPL | High | Overkill — full 3D app, hard to extract 2D solver alone |

**Recommendation:** `python-solvespace` (`pip install python-solvespace`). The SolveSpace constraint solver supports coincident, distance, angle, horizontal, vertical, perpendicular, parallel, equal, and symmetric constraints — all needed for cabinet-to-wall snapping, dimension-driven resizing, and opening alignment.

### 3.2 2D Rendering Engines

| Tool | Language | Output | Speed | Suitability |
|------|----------|--------|-------|-------------|
| **Cairo + Pango** | C (Python via `pycairo`) | PDF, SVG, PNG directly | Fast | **Best fit.** Direct PDF surface output at exact scale, line weight control, hatch patterns, text rendering |
| Skia | C++ | Various | Very fast | Harder to integrate, less PDF-native |
| Paper.js | JavaScript | Canvas/SVG | Medium | Browser-only, not server-side PDF |
| Fabric.js | JavaScript | Canvas/SVG | Medium | Same — browser-only |
| ReportLab | Python | PDF | Medium | Good for documents, weaker for precise CAD drawing |
| Matplotlib | Python | PDF/SVG | Slow | Not designed for technical drawing |

**Recommendation:** PyCairo for the rendering engine. Cairo has a native PDF surface that produces vector output at exact scale. Line weights, dash patterns, fill patterns (hatching for demo walls), and text placement are all first-class. Pango handles text layout for dimensions, labels, and notes.

### 3.3 PDF Sheet Composition / Title Blocks

| Tool | Approach | Suitability |
|------|----------|-------------|
| **Typst** | Markup-based typesetting, blazing fast PDF output, programmable layouts | **Best fit for title blocks and sheet composition.** Can template the entire sheet frame, import Cairo-rendered viewport SVGs, and produce final multi-page PDF |
| ReportLab | Python PDF library | Capable but verbose for complex layouts |
| WeasyPrint | HTML→PDF | CSS-based, harder to achieve precise CAD layout |
| LaTeX/TikZ | TeX | Powerful but slow compilation, huge install |
| pdfkit/jsPDF | JavaScript | Less precise for technical drawing |

**Recommendation:** Hybrid approach — Cairo renders the drawing viewport (plan views, details) as SVG. Typst composes the final sheet with title block, legend, notes sidebar, and embeds the Cairo SVG viewport. Typst's `curve` primitives can also draw the title block border directly. This gives us sub-second PDF generation per sheet.

### 3.4 AI Floor Plan Detection

| Tool | Approach | Suitability |
|------|----------|-------------|
| **Claude API (vision)** | Multimodal LLM — send CubiCasa PDF + room photos, get structured JSON of walls/openings/dims | **Best fit for this workflow.** No ML training needed, handles CubiCasa's specific format, can reason about photos |
| TF2DeepFloorplan | CNN for wall/room segmentation | Research-grade, needs training data specific to CubiCasa output |
| YOLOv8 floor plan models | Object detection (Roboflow datasets) | Good for detecting doors/windows/walls in floor plan images, but needs fine-tuning |
| OpenCV + heuristics | Edge detection, Hough transforms | Fragile, needs hand-tuned thresholds per input type |
| CubiCasa API | Commercial SaaS | Produces floor plans from phone scans, but doesn't output structured wall data for downstream CAD use |

**Recommendation:** Claude API (Sonnet) as primary AI engine. Send CubiCasa PDF page + room photos → receive structured JSON with wall segments, openings (door/window with widths), room labels, and ceiling height. For wall detection from photos, Claude's vision can identify wall boundaries and opening locations when combined with the CubiCasa floor plan as reference geometry. Fall back to OpenCV edge detection for pre-processing noisy photos before sending to Claude.

### 3.5 CAD/PDF Import

| Tool | Format | Suitability |
|------|--------|-------------|
| **ezdxf** | DXF/DWG read/write | Python library, excellent for importing AutoCAD files |
| **PyMuPDF (fitz)** | PDF vector extraction | Extract paths, text, and images from CubiCasa PDFs |
| pdf2image + OpenCV | PDF → raster → trace | Fallback for non-vector PDFs |
| LibreCAD DXF parser | DXF | C++ only, harder to integrate |

**Recommendation:** PyMuPDF for CubiCasa PDF import (extract vector paths as wall geometry) + ezdxf for DXF/DWG import. PyMuPDF can extract page content as vector paths, which can be converted to wall segments in the internal data model.

---

## 4. Recommended Tech Stack

### Backend (Python 3.12+)

| Component | Library | Version | Purpose |
|-----------|---------|---------|---------|
| Web framework | FastAPI | 0.115+ | REST API + WebSocket for real-time editing |
| Constraint solver | python-solvespace | 3.0+ | Parametric 2D constraints (wall-to-cabinet snapping, dimension-driven) |
| 2D rendering | pycairo + pangocairo | 1.26+ | Vector drawing to PDF/SVG surfaces |
| Sheet composition | typst (CLI) | 0.14+ | Title blocks, sheet frames, multi-page PDF assembly |
| PDF import | PyMuPDF | 1.24+ | Extract vectors from CubiCasa PDFs |
| DXF import/export | ezdxf | 1.3+ | AutoCAD file interop |
| AI layout | anthropic SDK | 0.40+ | Claude Sonnet for vision-based floor plan analysis |
| Image processing | OpenCV (cv2) | 4.10+ | Photo pre-processing for wall detection |
| Data storage | SQLite (dev) / PostgreSQL (prod) | — | Project and cabinet library storage |
| Task queue | Celery + Redis | — | Async PDF generation jobs |
| File storage | S3-compatible (MinIO local) | — | Drawing PDFs, project photos |

### Frontend (React 18+ / TypeScript)

| Component | Library | Purpose |
|-----------|---------|---------|
| Canvas rendering | Konva.js or PixiJS | Interactive 2D plan editing |
| State management | Zustand | Lightweight store for drawing state |
| UI framework | shadcn/ui + Tailwind | Interface chrome |
| Real-time sync | WebSocket | Live updates during editing |

### Infrastructure

| Component | Tool | Purpose |
|-----------|------|---------|
| Deployment | Docker Compose (dev) / Fly.io or Railway (prod) | Containerized deployment |
| CI/CD | GitHub Actions | Automated testing + deployment |
| Reverse proxy | Caddy | HTTPS + routing |

---

## 5. Architecture Design

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Web Frontend                       │
│  React + Konva.js (interactive 2D canvas editor)     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │ Project   │ │ Plan     │ │ Cabinet Palette  │    │
│  │ Manager   │ │ Editor   │ │ (KCD catalog)    │    │
│  └──────────┘ └──────────┘ └──────────────────┘    │
└────────────────────┬────────────────────────────────┘
                     │ REST + WebSocket
┌────────────────────┴────────────────────────────────┐
│                   FastAPI Backend                     │
│  ┌────────────┐ ┌──────────────┐ ┌───────────────┐ │
│  │ Project    │ │ Drawing      │ │ AI Layout     │ │
│  │ Service    │ │ Engine       │ │ Service       │ │
│  └────────────┘ └──────┬───────┘ └───────┬───────┘ │
│                        │                  │          │
│  ┌─────────────────────┴──────────────────┴───────┐ │
│  │              Core Geometry Engine                │ │
│  │  ┌─────────────┐ ┌──────────────┐              │ │
│  │  │ Constraint  │ │ Cabinet      │              │ │
│  │  │ Solver      │ │ Placer       │              │ │
│  │  │ (libslvs)   │ │ (KCD rules)  │              │ │
│  │  └─────────────┘ └──────────────┘              │ │
│  └────────────────────────────────────────────────┘ │
│                        │                             │
│  ┌─────────────────────┴──────────────────────────┐ │
│  │              Rendering Pipeline                  │ │
│  │  Cairo → SVG viewports → Typst sheets → PDF     │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 5.2 Core Data Model

```
Project
├── id: UUID
├── address: string
├── project_type: enum (Kitchen, Bath, Room)
├── kcd_color: string (EW, EG, OW, BW, SK, etc.)
├── kcd_style: string (Essential, Oslo, Shaker, Brooklyn)
├── drawer_type: string (slab, 5-piece)
├── uppers_height: int (30, 36, 42 inches)
├── crown_molding: enum (Flat, NoCrown)
├── ceiling_height: float (inches)
├── status: enum (A1_Request, A2_Bid, A3_Confirmed, A4_Construction)
├── rooms: Room[]
└── sheets: Sheet[]

Room
├── id: UUID
├── room_type: enum (Kitchen, DiningArea, Laundry, MainBath, Bath)
├── room_number: int (01, 02, 03...)
├── label: string
├── walls: Wall[]
├── openings: Opening[]
├── cabinets: CabinetInstance[]
├── appliances: Appliance[]
└── annotations: Annotation[]

Wall
├── id: UUID
├── start: Point2D {x, y}  // inches from room origin
├── end: Point2D {x, y}
├── thickness: float (default 4.5")
├── status: enum (Existing, ToRemove, New)
├── constraints: Constraint[]  // SolveSpace constraint refs
└── verified_dimensions: VerifiedDimension[]

Opening
├── id: UUID
├── wall_id: UUID
├── type: enum (Door, Window, Cased)
├── position_along_wall: float (inches from wall start)
├── width: float (inches)
├── height: float (inches, for windows)
├── sill_height: float (inches, for windows)
├── trim_width: float (default 3.5")
└── is_vif: bool  // verify in field

CabinetInstance
├── id: UUID
├── kcd_code: string (e.g., "OW-W2436")
├── catalog_entry: CatalogEntry (ref)
├── position: Point2D  // anchor point in room coords
├── wall_id: UUID  // which wall it's against
├── offset_from_wall_start: float (inches)
├── orientation: enum (Left, Right, Center)
├── hinge_side: enum (Left, Right, Both, None)
├── is_upper: bool
├── modifications: string[]  // e.g., "CUT TO SUIT", "PULL 1\" FROM WALL"
└── constraints: Constraint[]

CatalogEntry (from KCD catalog)
├── manuf_code: string (e.g., "W2436")
├── category: enum (Wall, Base, Tall, Vanity, Molding, Filler, Accessory)
├── width: float
├── height: float
├── depth: float
├── available_lines: string[]  // ["Oslo", "Shaker", "Brooklyn", "Essential"]
├── price: float (per unit, by line)
├── has_shelves: int
├── has_drawers: int
└── notes: string

Appliance
├── id: UUID
├── type: enum (DW, REF, RNG, MW, WO, SINK)
├── width: float
├── depth: float
├── position: Point2D
├── wall_id: UUID
└── label: string

Annotation
├── id: UUID
├── type: enum (Dimension, LeaderNote, RoomTag, CabinetTag, CeilingHeight, VIFDimension)
├── position: Point2D
├── text: string
├── color: string (default "#000000", VIF = "#FF0000")
├── font_size: float
└── rotation: float

Sheet
├── id: UUID
├── sheet_number: string (CP-00, A-01, A-02, etc.)
├── title: string
├── purpose: string (FOR BID / FOR CONSTRUCTION)
├── scale: string (1/2" = 1'-0")
├── date: date
├── designer: string (YES/NO)
├── viewports: Viewport[]
└── notes_content: NotesSidebar

Viewport
├── id: UUID
├── room_ids: UUID[]  // which rooms to render
├── render_mode: enum (Demo, NewLayout, Detail)
├── position_on_sheet: Rect {x, y, w, h}  // in sheet coords (points)
├── scale: float  // e.g., 0.0416667 for 1/2" = 1'-0"
└── label: string (e.g., "1 DEMO MAIN BATHROOM")

VerifiedDimension
├── id: UUID
├── label: string (e.g., ".1.", ".2.")
├── value: float (inches, null if not yet verified)
├── is_verified: bool
├── wall_id: UUID
├── start_point: Point2D
└── end_point: Point2D
```

### 5.3 Constraint Solver Integration

The SolveSpace constraint solver enforces parametric relationships:

```python
from python_solvespace import SolverSystem, ResultFlag

sys = SolverSystem()
wp = sys.create_2d_base()

# Define wall endpoints as constrained points
p1 = sys.add_point_2d(0, 0, wp)
p2 = sys.add_point_2d(120, 0, wp)  # 120" wall
wall = sys.add_line_2d(p1, p2, wp)

# Constrain wall length
sys.distance(p1, p2, 120.0, wp)  # 120 inches

# Constrain cabinet to wall
cab_anchor = sys.add_point_2d(12, 0, wp)
sys.coincident(cab_anchor, wall, wp)  # cabinet on wall
sys.distance(p1, cab_anchor, 12.0, wp)  # 12" from wall start

# Solve
result = sys.solve()
assert result == ResultFlag.OKAY
```

**Key constraint patterns for kitchen design:**
- Cabinet-to-wall coincidence (cabinet back face on wall line)
- Cabinet-to-cabinet adjacency (end-to-end, no gap)
- Opening clearance (cabinets don't overlap openings + trim allowance)
- Countertop overhang (1" auto-calculated from base cabinet depth)
- Backsplash height lock (18" from countertop)
- Crown molding auto-size (F696 for 96" ceiling, F396 for 97"+)
- Sink centered in sink base cabinet
- DW adjacent to sink base

### 5.4 Rendering Pipeline

```
1. Geometry Engine resolves all constraints → positioned elements
2. Cairo Renderer draws to SVG surface at drawing scale:
   - Walls: solid lines (existing), hatched fill (demo), bold (new)
   - Cabinets: rectangles with KCD tags
   - Openings: arc swings for doors, double lines for windows
   - Dimensions: extension lines + dimension text
   - VIF dimensions: red color (#FF0000)
   - Appliance symbols: standard plan symbols
   - Room tags: room name + number in box
3. Typst Sheet Composer:
   - Loads sheet template (title block, border, legend zone, notes zone)
   - Embeds Cairo SVG as viewport at specified position
   - Renders notes sidebar text (cabinetry specs, abbreviations, legend)
   - Outputs final PDF page
4. PDF Assembler:
   - Merges all sheet PDFs into single drawing set
   - Page order: CP-00, A-01, A-02, A-03, A-04, D-01
```

### 5.5 AI Layout Service

```python
# AI-assisted wall detection from CubiCasa PDF + photos
async def detect_layout(cubicasa_pdf: bytes, room_photos: list[bytes]) -> RoomLayout:
    # 1. Extract vector paths from CubiCasa PDF
    pdf_walls = extract_walls_from_pdf(cubicasa_pdf)  # PyMuPDF
    
    # 2. Send to Claude for structured analysis
    response = await anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", 
                 "media_type": "application/pdf", "data": b64_pdf}},
                *[{"type": "image", "source": {"type": "base64",
                   "media_type": "image/jpeg", "data": b64_photo}} 
                  for b64_photo in room_photos],
                {"type": "text", "text": LAYOUT_DETECTION_PROMPT}
            ]
        }]
    )
    
    # 3. Parse structured JSON response into RoomLayout
    return parse_layout_json(response.content[0].text)
```

The AI prompt instructs Claude to output structured JSON with wall segments, openings, room labels, and suggested cabinet placement based on standard kitchen design rules (work triangle, code clearances, etc.).

### 5.6 Web API Endpoints

```
POST   /api/projects                    Create project from A.1 request
GET    /api/projects/{id}               Get project state
POST   /api/projects/{id}/import-pdf    Import CubiCasa PDF
POST   /api/projects/{id}/import-photos Upload room photos
POST   /api/projects/{id}/detect-layout AI-assisted layout detection
PUT    /api/projects/{id}/rooms/{rid}   Update room geometry
POST   /api/projects/{id}/cabinets      Place cabinet
PUT    /api/projects/{id}/cabinets/{cid} Move/modify cabinet
DELETE /api/projects/{id}/cabinets/{cid} Remove cabinet
POST   /api/projects/{id}/solve         Run constraint solver
POST   /api/projects/{id}/generate-bid  Generate A.2 bid drawings (PDF)
PUT    /api/projects/{id}/verify-dims   Mark dimensions as verified (A.3)
POST   /api/projects/{id}/generate-cd   Generate A.4 construction drawings (PDF)
GET    /api/projects/{id}/export-tsv    Export KCD cabinet order TSV
GET    /api/projects/{id}/download/{sheet} Download individual sheet PDF
WS     /api/projects/{id}/ws            Real-time editing WebSocket
```

---

## 6. KCD Cabinet Rules Engine

Hardcoded rules from the KCD catalog that the constraint solver enforces:

```python
KCD_RULES = {
    "base_cabinet_height": 34.5,  # inches, universal
    "base_cabinet_depth": 24,     # inches, standard
    "wall_cabinet_depth": 12,     # inches, standard
    "vanity_cabinet_depth": 21,   # inches, standard
    "countertop_overhang": 1,     # inch
    "backsplash_height": 18,      # inches (kitchen)
    "stone_backsplash_height": 4, # inches (bathroom)
    "toekick_height": 4.5,        # inches (TKS8 part)
    "crown_96_ceiling": "F696",   # 6" filler for 96" ceiling
    "crown_97plus_ceiling": "F396",  # 3" filler for 97"+ or sloped
    "blind_base_pullout": {"BB36": (6,9), "BB42": (6,9), "BB48": (0,3)},
    "blind_wall_pullout": 1,      # 1-3" from adjacent wall
    "filler_min": 3,              # 3" min filler next to blind cabinet
    "upper_heights": [15, 18, 21, 24, 30, 36, 42],
    "base_widths": [9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48],
    "wall_widths": [9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45],
}
```

---

## 7. Typst Title Block Template

```typst
// sheet-template.typ — OD Select Drawing Sheet
#let od-sheet(
  company: "Opendoor",
  date: "2025-10-15",
  designer: "YES",
  purpose: "FOR BID",
  description: "DEMO KITCHEN PLAN",
  scale: "1/2\" = 1'-0\"",
  address: "773 Harbor View Rd Charleston, SC 29412",
  sheet-number: "A-01",
  viewport-svg: none,
  notes-content: none,
  legend-content: none,
) = {
  set page(width: 17in, height: 11in, margin: 0.25in)
  // ... border, title block, viewport placement, notes sidebar
}
```

---

## 8. Implementation Phases

### Phase 1: Core Engine (Weeks 1-3)
- Data model + SQLite storage
- SolveSpace constraint solver integration
- Cairo rendering: walls, openings, dimensions
- Basic PDF output (single sheet, no title block)

### Phase 2: KCD Cabinet System (Weeks 4-5)
- KCD catalog database from PDF extraction
- Cabinet placement with constraint rules
- Cabinet tags rendering
- TSV/CSV export for ordering

### Phase 3: Sheet Composition (Weeks 6-7)
- Typst title block templates
- Multi-sheet PDF assembly
- Legend, notes sidebar, abbreviations
- VIF dimension system (red highlighting, numbered markers)

### Phase 4: AI Layout (Weeks 8-9)
- CubiCasa PDF import (PyMuPDF vector extraction)
- Claude API integration for floor plan analysis
- Room photo wall detection
- Auto-suggested cabinet placement

### Phase 5: Web Interface (Weeks 10-12)
- React + Konva.js interactive editor
- Project management UI
- Real-time editing via WebSocket
- A.1→A.4 workflow state machine

### Phase 6: Automation & API (Weeks 13-14)
- Headless PDF generation API
- Slack webhook integration
- Batch processing queue
- Quality validation checks

---

## 9. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| SolveSpace solver GPL license | Acceptable for internal tool; commercial license available if needed |
| Cairo text rendering for architectural dimensions | Pango handles precise text metrics; test early with real dimension strings |
| AI layout accuracy from photos | Claude vision is supplementary — human review remains in workflow |
| Typst SVG embedding limitations | Typst 0.14 supports PDF as native image format; can embed Cairo PDF output directly |
| KCD catalog updates | Catalog database updatable via PDF re-parse; version-controlled |
| CubiCasa PDF format changes | PyMuPDF extraction is generic vector parsing, format-agnostic |

---

## 10. Comparison with Commercial Alternatives

| Tool | Price | Parametric | AI | KCD Integration | Custom Title Blocks | API |
|------|-------|-----------|-----|-----------------|--------------------|----|
| 2020 Design | $2,500+/yr | Yes | Limited | Partial | No | No |
| ProKitchen | $1,200+/yr | Yes | No | Yes | Limited | No |
| Chief Architect | $3,000+ | Yes | No | No | Yes | No |
| AutoCAD LT | $1,500/yr | Limited | No | No | Yes | Limited |
| SketchUp + Layout | $700/yr | No | No | No | Yes | No |
| **This tool** | **$0 (OSS)** | **Yes** | **Yes (Claude)** | **Full** | **Full** | **Yes** |

The proposed tool is purpose-built for this specific workflow, which no commercial tool fully covers. The combination of parametric constraints, KCD-specific rules, AI-assisted layout, and automated PDF generation with custom title blocks is unique.
