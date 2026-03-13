# OD Select Drawing Engine — Claude Code Implementation Spec

> **Project codename:** `od-draw`  
> **Purpose:** Open-source 2D parametric construction drawing tool for Opendoor's OD Select kitchen/bath cabinetry workflow  
> **Stack:** Python 3.12 + FastAPI + python-solvespace + PyCairo + Typst + React/Konva.js  
> **Target output:** Multi-page PDF drawing sets matching Opendoor's existing bid/construction document format  

---

## PROJECT STRUCTURE

```
od-draw/
├── README.md
├── pyproject.toml                    # Python project config (uv/poetry)
├── docker-compose.yml
├── Dockerfile
├── .env.example
│
├── od_draw/                          # Python backend package
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entry
│   ├── config.py                     # Settings (env vars, paths)
│   │
│   ├── models/                       # Data models (Pydantic + SQLModel)
│   │   ├── __init__.py
│   │   ├── project.py                # Project, Room, Sheet
│   │   ├── geometry.py               # Wall, Opening, Point2D, Rect
│   │   ├── cabinet.py                # CabinetInstance, CatalogEntry
│   │   ├── appliance.py              # Appliance definitions
│   │   ├── annotation.py             # Dimension, Tag, Note
│   │   └── enums.py                  # All enums
│   │
│   ├── catalog/                      # KCD Cabinet Catalog
│   │   ├── __init__.py
│   │   ├── kcd_catalog.py            # Full KCD catalog as Python data
│   │   ├── kcd_rules.py              # Cabinet placement rules engine
│   │   ├── kcd_parser.py             # Parse KCD catalog PDF into data
│   │   └── kcd_export.py             # TSV/CSV export for ordering
│   │
│   ├── engine/                       # Core Geometry & Constraint Engine
│   │   ├── __init__.py
│   │   ├── constraint_solver.py      # python-solvespace wrapper
│   │   ├── geometry_engine.py        # Wall/opening/cabinet positioning
│   │   ├── cabinet_placer.py         # Auto-place cabinets per KCD rules
│   │   ├── dimension_engine.py       # Auto-generate dimensions
│   │   └── room_builder.py           # Build room from wall segments
│   │
│   ├── renderer/                     # 2D Rendering (Cairo)
│   │   ├── __init__.py
│   │   ├── cairo_renderer.py         # Main renderer: room plan → SVG/PDF
│   │   ├── wall_renderer.py          # Wall drawing (solid/hatched/bold)
│   │   ├── cabinet_renderer.py       # Cabinet rectangles + tags
│   │   ├── opening_renderer.py       # Door arcs, window lines
│   │   ├── dimension_renderer.py     # Dimension strings, extension lines
│   │   ├── appliance_renderer.py     # Appliance plan symbols
│   │   ├── annotation_renderer.py    # Room tags, notes, labels
│   │   ├── detail_renderer.py        # D-01 detail drawings (sections, heights)
│   │   ├── legend_renderer.py        # Legend block
│   │   └── styles.py                 # Line weights, colors, fonts, hatching
│   │
│   ├── sheets/                       # Sheet Composition (Typst)
│   │   ├── __init__.py
│   │   ├── sheet_composer.py         # Orchestrate Typst rendering
│   │   ├── title_block.py            # Title block data assembly
│   │   ├── notes_sidebar.py          # Cabinetry notes, abbreviations
│   │   ├── pdf_assembler.py          # Merge sheets into final PDF
│   │   └── templates/                # Typst template files
│   │       ├── sheet-template.typ    # Main sheet frame
│   │       ├── title-block.typ       # Title block component
│   │       ├── cover-page.typ        # CP-00 measurement guide
│   │       ├── notes-sidebar.typ     # Notes + legend sidebar
│   │       └── detail-sheet.typ      # D-01 details layout
│   │
│   ├── ai/                           # AI Layout Service
│   │   ├── __init__.py
│   │   ├── layout_detector.py        # Claude API for floor plan analysis
│   │   ├── pdf_extractor.py          # PyMuPDF vector extraction from CubiCasa PDF
│   │   ├── photo_analyzer.py         # Room photo analysis (wall detection)
│   │   ├── cabinet_suggester.py      # AI-suggested cabinet layout
│   │   └── prompts.py                # Claude prompt templates
│   │
│   ├── importer/                     # File Import
│   │   ├── __init__.py
│   │   ├── cubicasa_importer.py      # CubiCasa PDF → room geometry
│   │   ├── dxf_importer.py           # DXF/DWG → room geometry (ezdxf)
│   │   └── photo_importer.py         # Room photos processing
│   │
│   ├── api/                          # API Routes
│   │   ├── __init__.py
│   │   ├── projects.py               # Project CRUD
│   │   ├── rooms.py                  # Room geometry editing
│   │   ├── cabinets.py               # Cabinet placement
│   │   ├── drawings.py               # PDF generation endpoints
│   │   ├── import_export.py          # File import/export
│   │   └── websocket.py              # Real-time editing
│   │
│   └── db/                           # Database
│       ├── __init__.py
│       ├── database.py               # SQLModel engine setup
│       └── migrations/               # Alembic migrations
│
├── frontend/                         # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ProjectManager.tsx    # Project list + create
│   │   │   ├── PlanEditor.tsx        # Main 2D canvas editor
│   │   │   ├── CabinetPalette.tsx    # KCD cabinet drag-drop palette
│   │   │   ├── PropertiesPanel.tsx   # Selected element properties
│   │   │   ├── SheetPreview.tsx      # PDF preview
│   │   │   └── DimensionTool.tsx     # Add/edit dimensions
│   │   ├── stores/
│   │   │   └── drawingStore.ts       # Zustand store
│   │   └── api/
│   │       └── client.ts             # API client
│   └── public/
│
├── tests/
│   ├── test_constraint_solver.py
│   ├── test_cairo_renderer.py
│   ├── test_kcd_catalog.py
│   ├── test_sheet_composer.py
│   ├── test_pdf_generation.py
│   └── fixtures/
│       ├── sample_cubicasa.pdf
│       └── sample_room_photos/
│
└── scripts/
    ├── parse_kcd_catalog.py          # One-time KCD catalog PDF → Python data
    ├── generate_sample.py            # Generate sample drawing set
    └── seed_db.py                    # Seed database with test project
```

---

## DEPENDENCIES

### Python (`pyproject.toml`)

```toml
[project]
name = "od-draw"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "python-solvespace>=3.0.8",
    "pycairo>=1.26.0",
    "PyGObject>=3.48.0",           # For pangocairo text rendering
    "pymupdf>=1.24.0",             # PDF vector extraction
    "ezdxf>=1.3.0",                # DXF import/export
    "anthropic>=0.40.0",           # Claude API
    "opencv-python-headless>=4.10.0",
    "sqlmodel>=0.0.22",
    "alembic>=1.14.0",
    "python-multipart>=0.0.12",
    "pillow>=10.4.0",
    "numpy>=1.26.0",
    "httpx>=0.27.0",
    "celery[redis]>=5.4.0",
    "boto3>=1.35.0",               # S3-compatible storage
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff", "mypy"]
```

### System dependencies (Dockerfile)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    typst \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

### Frontend (`package.json`)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-konva": "^18.2.10",
    "konva": "^9.3.0",
    "zustand": "^5.0.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "tailwindcss": "^3.4.0",
    "lucide-react": "^0.400.0"
  }
}
```

---

## IMPLEMENTATION DETAILS

### 1. KCD Catalog Database (`od_draw/catalog/kcd_catalog.py`)

Build the complete KCD catalog as a Python data structure. Source: KCD Product Catalog March 2026 PDF.

```python
"""
Complete KCD cabinet catalog database.
Source: https://www.kcdus.com/wp-content/uploads/2026/03/03.26-KCD-Catalog.pdf

Color prefix codes:
  Premier Series: OW (Oslo White), OC (Oslo Classic Walnut), OO (Oslo Oak),
                  SW (Shaker White), SK (Shaker Kodiak), SE (Shaker Espresso),
                  SS (Shaker Sand), SM (Shaker Moss),
                  BW (Brooklyn White), BS (Brooklyn Slate), BG (Brooklyn Gray),
                  BF (Brooklyn Fawn), BM (Brooklyn Midnight)
  Builder Series: EW (Essential White), EG (Essential Gray)

Cabinet code format:
  Wall:   W{width}{height}     e.g., W2436 = 24"W x 36"H x 12"D
  Base:   B{width}             e.g., B30 = 30"W x 34.5"H x 24"D
  Sink:   SB{width}            e.g., SB36
  Drawer: DB{width}-{count}    e.g., DB24-3 = 3-drawer 24"W
  Tall:   P{width}{height}     e.g., P2496
  Vanity: V{width}             single door
          VSBDL{width}         vanity sink base door left
          VSBDR{width}         vanity sink base door right
  Blind:  BW{width} (wall)     BB{width} (base)
  Filler: F{height}{width}96   e.g., F396 = 3"x96" filler, F696 = 6"x96"
  Misc:   TKS8 (toekick), MWC3018 (microwave cabinet), ER33/ER36 (easy reach),
          CSF42 (corner sink front), FSB36 (farm sink base)
"""

from dataclasses import dataclass
from enum import Enum

class CabinetCategory(Enum):
    WALL = "wall"
    BASE = "base"
    TALL = "tall"
    VANITY = "vanity"
    MOLDING = "molding"
    FILLER = "filler"
    ACCESSORY = "accessory"

class CabinetSeries(Enum):
    PREMIER = "premier"   # Oslo, Shaker, Brooklyn
    BUILDER = "builder"   # Essential

@dataclass
class CatalogEntry:
    code: str            # e.g., "W2436"
    category: CabinetCategory
    width: float         # inches
    height: float        # inches
    depth: float         # inches
    available_premier: list[str]   # color codes available in Premier
    available_builder: list[str]   # color codes available in Builder
    shelves: int = 0
    drawers: int = 0
    doors: int = 1
    notes: str = ""

# WALL CABINETS - Standard 12" deep
WALL_CABINETS = [
    # Single door 30" high
    CatalogEntry("W930",  CabinetCategory.WALL, 9, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    CatalogEntry("W1230", CabinetCategory.WALL, 12, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    CatalogEntry("W1530", CabinetCategory.WALL, 15, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    CatalogEntry("W1830", CabinetCategory.WALL, 18, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    CatalogEntry("W2130", CabinetCategory.WALL, 21, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    # Single door 36" high
    CatalogEntry("W936",  CabinetCategory.WALL, 9, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2),
    CatalogEntry("W1236", CabinetCategory.WALL, 12, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2),
    CatalogEntry("W1536", CabinetCategory.WALL, 15, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2),
    CatalogEntry("W1836", CabinetCategory.WALL, 18, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2),
    CatalogEntry("W2136", CabinetCategory.WALL, 21, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2),
    # Single door 42" high
    CatalogEntry("W942",  CabinetCategory.WALL, 9, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3),
    CatalogEntry("W1242", CabinetCategory.WALL, 12, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3),
    CatalogEntry("W1542", CabinetCategory.WALL, 15, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3),
    CatalogEntry("W1842", CabinetCategory.WALL, 18, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3),
    CatalogEntry("W2142", CabinetCategory.WALL, 21, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3),
    # Double door 30" high
    CatalogEntry("W2430-2", CabinetCategory.WALL, 24, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    CatalogEntry("W2730", CabinetCategory.WALL, 27, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    CatalogEntry("W3030", CabinetCategory.WALL, 30, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    CatalogEntry("W3330", CabinetCategory.WALL, 33, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    CatalogEntry("W3630", CabinetCategory.WALL, 36, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    CatalogEntry("W3930", CabinetCategory.WALL, 39, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1, doors=2),
    # Double door 36" high
    CatalogEntry("W2436", CabinetCategory.WALL, 24, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    CatalogEntry("W2736", CabinetCategory.WALL, 27, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    CatalogEntry("W3036", CabinetCategory.WALL, 30, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    CatalogEntry("W3336", CabinetCategory.WALL, 33, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    CatalogEntry("W3636", CabinetCategory.WALL, 36, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    CatalogEntry("W3936", CabinetCategory.WALL, 39, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, doors=2),
    # Double door 42" high
    CatalogEntry("W2442-2", CabinetCategory.WALL, 24, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    CatalogEntry("W2742", CabinetCategory.WALL, 27, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    CatalogEntry("W3042", CabinetCategory.WALL, 30, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    CatalogEntry("W3342", CabinetCategory.WALL, 33, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    CatalogEntry("W3642", CabinetCategory.WALL, 36, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    CatalogEntry("W3942", CabinetCategory.WALL, 39, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, doors=2),
    # Deep wall (refrigerator) cabinets - 24" deep
    CatalogEntry("W331824", CabinetCategory.WALL, 33, 18, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], shelves=0, notes="No shelf"),
    CatalogEntry("W361824", CabinetCategory.WALL, 36, 18, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=0, notes="No shelf"),
    CatalogEntry("W332424", CabinetCategory.WALL, 33, 24, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], shelves=1),
    CatalogEntry("W362424", CabinetCategory.WALL, 36, 24, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=1),
    # Microwave wall cabinet
    CatalogEntry("MWC3018", CabinetCategory.WALL, 30, 18, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Microwave wall cabinet"),
    # Blind wall cabinets
    CatalogEntry("BW3030", CabinetCategory.WALL, 30, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind wall - pull 1-3\" from adjacent wall"),
    CatalogEntry("BW3630", CabinetCategory.WALL, 36, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind wall"),
    CatalogEntry("BW3636", CabinetCategory.WALL, 36, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind wall"),
    CatalogEntry("BW3642", CabinetCategory.WALL, 36, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, notes="Blind wall"),
    # Corner wall cabinets
    CatalogEntry("CW2430", CabinetCategory.WALL, 24, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, notes="Corner wall"),
    CatalogEntry("CW2436", CabinetCategory.WALL, 24, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=2, notes="Corner wall"),
    # Easy reach wall
    CatalogEntry("WER2430", CabinetCategory.WALL, 24, 30, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Easy reach wall"),
    CatalogEntry("WER2436", CabinetCategory.WALL, 24, 36, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Easy reach wall"),
    CatalogEntry("WER2442", CabinetCategory.WALL, 24, 42, 12,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=3, notes="Easy reach wall"),
]

# BASE CABINETS - Standard 24" deep, 34.5" high
BASE_CABINETS = [
    CatalogEntry("B09", CabinetCategory.BASE, 9, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"]),
    CatalogEntry("B12", CabinetCategory.BASE, 12, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"]),
    CatalogEntry("B15", CabinetCategory.BASE, 15, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"]),
    CatalogEntry("B18", CabinetCategory.BASE, 18, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"]),
    CatalogEntry("B21", CabinetCategory.BASE, 21, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"]),
    CatalogEntry("B24-2", CabinetCategory.BASE, 24, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2),
    CatalogEntry("B27", CabinetCategory.BASE, 27, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2),
    CatalogEntry("B30", CabinetCategory.BASE, 30, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2),
    CatalogEntry("B33", CabinetCategory.BASE, 33, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2),
    CatalogEntry("B36", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2),
    CatalogEntry("B39", CabinetCategory.BASE, 39, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, doors=2, notes="Center stile"),
    CatalogEntry("B42", CabinetCategory.BASE, 42, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], doors=2, notes="Center stile"),
    # Sink base
    CatalogEntry("SB30", CabinetCategory.BASE, 30, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Sink base"),
    CatalogEntry("SB33", CabinetCategory.BASE, 33, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Sink base"),
    CatalogEntry("SB36", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Sink base"),
    CatalogEntry("SB42", CabinetCategory.BASE, 42, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Sink base"),
    # Farm sink base
    CatalogEntry("FSB36", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], notes="Farm sink base - front trimmed for apron sink"),
    # Drawer base 3-drawer
    CatalogEntry("DB12-3", CabinetCategory.BASE, 12, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    CatalogEntry("DB15-3", CabinetCategory.BASE, 15, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    CatalogEntry("DB18-3", CabinetCategory.BASE, 18, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    CatalogEntry("DB21-3", CabinetCategory.BASE, 21, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    CatalogEntry("DB24-3", CabinetCategory.BASE, 24, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    CatalogEntry("DB30-3", CabinetCategory.BASE, 30, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=3),
    # Drawer base 2-drawer
    CatalogEntry("DB30-2", CabinetCategory.BASE, 30, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], drawers=2),
    CatalogEntry("DB36-2", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], drawers=2),
    # Easy reach base
    CatalogEntry("ER33", CabinetCategory.BASE, 33, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], notes="Easy reach base - lazy susan"),
    CatalogEntry("ER36", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Easy reach base - lazy susan"),
    # Blind base
    CatalogEntry("BB36", CabinetCategory.BASE, 30, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind base - actual width 30\", pull 6-9\" from wall"),
    CatalogEntry("BB42", CabinetCategory.BASE, 36, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind base - actual width 36\", pull 6-9\" from wall"),
    CatalogEntry("BB48", CabinetCategory.BASE, 48, 34.5, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Blind base - pull 0-3\" from wall"),
]

# TALL CABINETS - 24" deep
TALL_CABINETS = [
    CatalogEntry("P1884", CabinetCategory.TALL, 18, 84, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=4, notes="Single door pantry"),
    CatalogEntry("P1890", CabinetCategory.TALL, 18, 90, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=4),
    CatalogEntry("P1896", CabinetCategory.TALL, 18, 96, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], shelves=5),
    CatalogEntry("P2496", CabinetCategory.TALL, 24, 96, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], shelves=5, doors=2, notes="Double door pantry"),
    CatalogEntry("P3096", CabinetCategory.TALL, 30, 96, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 [], shelves=5, doors=2),
    # Oven cabinets
    CatalogEntry("OC3390", CabinetCategory.TALL, 33, 90, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, notes="Oven cabinet"),
    CatalogEntry("OC3396", CabinetCategory.TALL, 33, 96, 24,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], drawers=1, notes="Oven cabinet"),
]

# VANITY CABINETS - 21" deep, 34.5" high
VANITY_CABINETS = [
    CatalogEntry("VSBDL30", CabinetCategory.VANITY, 30, 34.5, 21,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Vanity sink base door left"),
    CatalogEntry("VSBDR30", CabinetCategory.VANITY, 30, 34.5, 21,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Vanity sink base door right"),
    # ... extend with V12, V15, V18, V24, V30, V36 etc. from catalog
]

# FILLERS & ACCESSORIES
FILLERS = [
    CatalogEntry("F396", CabinetCategory.FILLER, 3, 96, 0.75,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="3\" filler panel - cut to suit"),
    CatalogEntry("F696", CabinetCategory.FILLER, 6, 96, 0.75,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="6\" filler panel - for 96\" ceiling crown"),
    CatalogEntry("TKS8", CabinetCategory.ACCESSORY, 96, 4.5, 0.25,
                 ["OW","OC","OO","SW","SK","SE","SS","SM","BW","BS","BG","BF","BM"],
                 ["EW","EG"], notes="Toekick skin 96\"x4.5\""),
]

# Full catalog dictionary
CATALOG = {}
for entry in WALL_CABINETS + BASE_CABINETS + TALL_CABINETS + VANITY_CABINETS + FILLERS:
    CATALOG[entry.code] = entry

def get_prefixed_code(color_prefix: str, base_code: str) -> str:
    """Generate full KCD code: OW-W2436, BW-B30, etc."""
    return f"{color_prefix}-{base_code}"

def lookup(full_code: str) -> CatalogEntry | None:
    """Look up cabinet by full code (e.g., 'OW-W2436') or base code ('W2436')."""
    if "-" in full_code:
        base = full_code.split("-", 1)[1]
    else:
        base = full_code
    return CATALOG.get(base)
```

### 2. Cairo Rendering Constants (`od_draw/renderer/styles.py`)

```python
"""
Drawing style constants matching Opendoor's OD Select drawing standards.
All measurements in inches (drawing units), converted to Cairo points at render time.
Scale: 1/2" = 1'-0" means 1 drawing inch = 24 real inches, or scale factor = 1/24.
"""

# Line weights (in points at print scale)
WALL_EXISTING_WEIGHT = 1.5      # Existing wall to remain
WALL_DEMO_WEIGHT = 1.0          # Existing wall to be removed (with hatch)
WALL_NEW_WEIGHT = 2.0           # New wall (bold)
CABINET_OUTLINE_WEIGHT = 0.5    # Cabinet outlines
DIMENSION_LINE_WEIGHT = 0.25    # Dimension and extension lines
OPENING_LINE_WEIGHT = 0.5       # Door/window lines

# Colors (RGB 0-1)
COLOR_BLACK = (0, 0, 0)
COLOR_RED_VIF = (1, 0, 0)       # Verify-in-field dimensions
COLOR_DEMO_HATCH = (0.85, 0.75, 0.55)  # Demo wall fill (tan/amber)
COLOR_NEW_WALL = (0.7, 0.7, 0.7)       # New wall fill (gray)
COLOR_CABINET_FILL = (1, 1, 1)          # Cabinet interior (white)

# Hatch patterns
DEMO_WALL_HATCH_ANGLE = 45     # degrees
DEMO_WALL_HATCH_SPACING = 4    # points between hatch lines

# Text styles
FONT_DIMENSION = "Arial"
FONT_SIZE_DIMENSION = 8        # points
FONT_SIZE_ROOM_TAG = 10        # points
FONT_SIZE_CABINET_TAG = 6      # points
FONT_SIZE_NOTE = 7             # points
FONT_SIZE_TITLE_BLOCK = 9      # points

# Sheet sizes (ANSI D / Tabloid = 17" x 11")
SHEET_WIDTH_INCHES = 17
SHEET_HEIGHT_INCHES = 11
SHEET_MARGIN = 0.25            # inches

# Title block dimensions (bottom strip)
TITLE_BLOCK_HEIGHT = 0.5       # inches from bottom
TITLE_BLOCK_FIELDS = {
    "company_logo": (0.25, 0.25),    # position from bottom-left
    "date": (2.0, 0.25),
    "designer": (4.0, 0.25),
    "purpose": (5.5, 0.25),
    "scale": (8.0, 0.25),
    "address": (10.0, 0.25),
    "sheet_number": (16.0, 0.25),
}

# Notes sidebar (right side of A-02 sheets)
NOTES_SIDEBAR_WIDTH = 3.5      # inches
VIEWPORT_WIDTH = SHEET_WIDTH_INCHES - SHEET_MARGIN * 2 - NOTES_SIDEBAR_WIDTH
VIEWPORT_HEIGHT = SHEET_HEIGHT_INCHES - SHEET_MARGIN * 2 - TITLE_BLOCK_HEIGHT

# Drawing scales
SCALES = {
    "1/2\" = 1'-0\"": 1/24,    # 1 drawing inch = 24 real inches
    "1/4\" = 1'-0\"": 1/48,
    "3/4\" = 1'-0\"": 1/16,
    "1\" = 1'-0\"": 1/12,
    "As indicated": None,       # Multiple scales on one sheet (D-01)
}
```

### 3. AI Layout Detection Prompt (`od_draw/ai/prompts.py`)

```python
LAYOUT_DETECTION_PROMPT = """
You are an expert architectural drafter analyzing floor plan documents and room photos 
for a kitchen/bathroom renovation project.

Given the CubiCasa floor plan PDF and room photos, extract the following as structured JSON:

{
  "rooms": [
    {
      "room_type": "Kitchen" | "DiningArea" | "Laundry" | "MainBath" | "Bath",
      "room_number": 1,
      "label": "KITCHEN",
      "walls": [
        {
          "id": "w1",
          "start": {"x": 0, "y": 0},
          "end": {"x": 120, "y": 0},
          "thickness": 4.5,
          "status": "existing" | "to_remove" | "new"
        }
      ],
      "openings": [
        {
          "wall_id": "w1",
          "type": "door" | "window" | "cased",
          "position_along_wall": 36,
          "width": 30,
          "height": 80,
          "sill_height": null,
          "trim_width": 3.5
        }
      ],
      "ceiling_height": 96,
      "appliances": [
        {
          "type": "DW" | "REF" | "RNG" | "MW" | "WO" | "SINK",
          "approximate_position": {"x": 60, "y": 0},
          "width": 24
        }
      ]
    }
  ],
  "notes": "Any observations about the space"
}

RULES:
- All measurements in INCHES (never feet and inches)
- Round to nearest 1/4 inch
- Measure to openings, not to trims
- Wall coordinates should form closed polygons per room
- Mark walls for demolition based on visible demo notes in the plans
- Identify appliance locations from both the floor plan and photos
- If a dimension is unclear, mark it with "verify_in_field": true
- Use the room photos to confirm/correct wall positions seen in the CubiCasa plan
"""

CABINET_SUGGESTION_PROMPT = """
You are a kitchen designer following Opendoor OD Select standards.
Given the room layout JSON and KCD catalog availability, suggest optimal cabinet placement.

Design rules:
1. Work triangle: sink-stove-fridge should form efficient triangle
2. DW must be adjacent to sink base cabinet
3. Minimum 15" countertop on each side of range
4. Upper cabinets align with base cabinets below (match widths where possible)
5. Blind cabinets need 3"+ filler next to adjacent cabinet
6. Fill available wall space efficiently with standard KCD sizes
7. Crown molding: F696 for 96" ceiling, F396 for 97"+
8. Backsplash: 18" kitchen, 4" bathroom stone
9. Countertop: 1" overhang standard

Return JSON array of cabinet placements with KCD codes and positions.
"""
```

### 4. TSV Export (`od_draw/catalog/kcd_export.py`)

```python
"""Export cabinet list to KCD-compatible TSV format for ordering."""

def export_project_tsv(project, output_path: str):
    """
    Export cabinet order in KCD TSV format matching their ordering system.
    
    TSV structure (matches KCD ordering format):
    #  Qty  Manuf.code  Width  Height  Depth  Left-Right  Price  Hng
    
    Groups by catalog (color line), includes assembly costs for assembled orders.
    """
    cabinets = collect_all_cabinets(project)
    
    # Group by color prefix (each prefix = separate catalog section)
    groups = {}
    for cab in cabinets:
        prefix = cab.kcd_code.split("-")[0]
        groups.setdefault(prefix, []).append(cab)
    
    lines = []
    lines.append("Cabinet List")
    lines.append("PROJECT DETAILS")
    lines.append(f"\nID:\t\tCreation Date:\t{project.created_at}")
    # ... header fields ...
    
    item_num = 1
    for prefix, cabs in groups.items():
        catalog_entry = get_catalog_info(prefix)
        lines.append(f"\nCATALOG {catalog_entry.catalog_id}\t0")
        lines.append(f"\nSupplier\tKitchen Cabinet Distributors")
        lines.append(f"Door style\t{catalog_entry.door_style}")
        lines.append("#\tQty\tManuf. code\tWidth\tHeight\tDepth\tLeft-Right\tPrice\tHng")
        lines.append("")
        
        for cab in cabs:
            entry = lookup(cab.kcd_code)
            hinge = cab.hinge_side.value if cab.hinge_side else "None"
            lr = f"{'F' if cab.orientation != 'blind_left' else 'U'}-{'F' if cab.orientation != 'blind_right' else 'U'}"
            lines.append(
                f"{item_num}\t1\t{cab.kcd_code}\t{entry.width} \"\t"
                f"{entry.height} \"\t{entry.depth} \"\t{lr}\t"
                f"{entry.price:.2f}\t{hinge}"
            )
            item_num += 1
    
    with open(output_path, "w") as f:
        f.write("\r\n".join(lines))
```

---

## RENDERING SPECIFICATIONS

### Wall Drawing Standards

| Wall Status | Line Weight | Fill | Pattern |
|-------------|-----------|------|---------|
| Existing to remain | 1.5pt black solid | White | — |
| Existing to remove | 1.0pt black solid | Tan (#D9C49A) | 45° hatch lines |
| New construction | 2.0pt black solid | Light gray (#B0B0B0) | Solid fill |

### Cabinet Tag Format

Base cabinets: Tag placed centered inside cabinet rectangle, e.g., `OW-B24`  
Upper cabinets: Tag placed centered, prefixed with "UPPER" label above, e.g., `OW-W2436`  
Special notes below tag when applicable: `CUT TO SUIT`, `PULL 1" FROM WALL`  
Font: Arial 6pt, black  

### Dimension Standards

- Extension lines: 0.25pt, extend 1/8" past dimension line
- Dimension lines: 0.25pt with arrow/tick terminators
- Dimension text: Arial 8pt, centered above line
- VIF dimensions: Same style but RED (#FF0000), numbered with `.1.`, `.2.`, etc.

### Room Tag Format

```
┌─────────────┐
│  KITCHEN    │
│     01      │
└─────────────┘
```
Centered in room, Arial 10pt bold for room name, 8pt for number, box border 0.5pt.

### Appliance Symbols

| Appliance | Symbol |
|-----------|--------|
| DW (Dishwasher) | Rectangle with "DW" text |
| REF (Refrigerator) | Dashed rectangle outline |
| RNG (Range) | Rectangle with 4 circles (burners) |
| MW (Microwave) | "MW" in upper cabinet |
| WO (Wall Oven) | Rectangle with "WO" text |
| SINK | Double oval in plan view |

---

## CRITICAL IMPLEMENTATION NOTES

1. **All internal measurements are in inches.** Never use feet-and-inches format anywhere in the data model. Only convert to display format in rendering.

2. **Scale conversion:** At 1/2" = 1'-0", multiply real inches by (0.5/12) = 0.04167 to get drawing inches. Cairo works in points (72pt = 1 inch), so multiply again by 72 for point coordinates.

3. **PDF page size:** ANSI D Tabloid landscape = 17" × 11" (1224pt × 792pt). All drawings are landscape orientation.

4. **Typst CLI invocation:** `typst compile sheet.typ output.pdf` — runs in ~50ms per page, much faster than LaTeX.

5. **python-solvespace is GPL v3.** This is acceptable for an internal tool. If distribution is planned, the SolveSpace commercial license is available from the maintainers.

6. **KCD catalog must be version-controlled.** When KCD releases catalog updates, re-run the parser and diff against previous version. The March 2026 catalog is the baseline.

7. **CubiCasa PDFs are vector-based.** PyMuPDF can extract paths as coordinate arrays. These map directly to wall segments in the data model. The extraction is format-agnostic — it reads PDF drawing commands, not CubiCasa-specific metadata.

8. **The AI layout service is supplementary, not authoritative.** All AI-detected geometry must be reviewed and adjusted by a human designer. The tool should flag low-confidence detections.

9. **Sheet numbering follows Opendoor convention:** CP-00 (cover), A-01 through A-04 (architectural plans), D-01 (details). Additional sheets like E-01 (electrical) or P-01 (plumbing) can be added later.

10. **Redis is required for Celery task queue** — PDF generation jobs should be async to support API-triggered batch generation.
