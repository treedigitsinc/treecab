from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogEntry:
    code: str
    category: str
    width: float
    height: float
    depth: float
    premier_lines: tuple[str, ...]
    builder_lines: tuple[str, ...]
    shelves: int = 0
    drawers: int = 0
    doors: int = 1
    notes: str = ""


ALL_PREMIER = ("OW", "OC", "OO", "SW", "SK", "SE", "SS", "SM", "BW", "BS", "BG", "BF", "BM")
ALL_BUILDER = ("EW", "EG")

COLOR_LINES = {
    "OW": "Oslo White",
    "OC": "Oslo Classic Walnut",
    "OO": "Oslo Oak",
    "SW": "Shaker White",
    "SK": "Shaker Kodiak",
    "SE": "Shaker Espresso",
    "SS": "Shaker Sand",
    "SM": "Shaker Moss",
    "BW": "Brooklyn White",
    "BS": "Brooklyn Slate",
    "BG": "Brooklyn Gray",
    "BF": "Brooklyn Fawn",
    "BM": "Brooklyn Midnight",
    "EW": "Essential White",
    "EG": "Essential Gray",
}

CATALOG: dict[str, CatalogEntry] = {}


def _add(
    code: str,
    category: str,
    width: float,
    height: float,
    depth: float,
    premier: tuple[str, ...] = ALL_PREMIER,
    builder: tuple[str, ...] = ALL_BUILDER,
    **kwargs,
) -> None:
    CATALOG[code] = CatalogEntry(code, category, width, height, depth, premier, builder, **kwargs)


for height in (30, 36, 42):
    shelf_count = {30: 1, 36: 2, 42: 3}[height]
    for width in (9, 12, 15, 18, 21):
        _add(f"W{width}{height}", "wall", width, height, 12, shelves=shelf_count)

for width in (24, 27, 30, 33, 36, 39):
    for height in (30, 36, 42):
        shelf_count = {30: 1, 36: 2, 42: 3}[height]
        code = f"W{width}{height}" if width >= 27 else f"W{width}{height}-2"
        _add(code, "wall", width, height, 12, shelves=shelf_count, doors=2)

for width in (30, 33, 36, 42, 45):
    _add(f"W{width}12", "wall", width, 12, 12, doors=2, shelves=0)

_add("MWC3018", "wall", 30, 18, 12, notes="Microwave wall cabinet")
_add("BW3636", "wall", 36, 36, 12, notes='Blind wall, pull 1-3" from wall')
_add("CW2436", "wall", 24, 36, 12, shelves=2, notes="Corner wall")
_add("WER2436", "wall", 24, 36, 12, shelves=2, notes="Easy reach wall")
_add("W303015", "wall", 30, 30, 15, ALL_PREMIER, tuple(), doors=2, notes='15" deep')

for width in (9, 12, 15, 18, 21):
    _add(f"B{width:02d}" if width == 9 else f"B{width}", "base", width, 34.5, 24)

_add("B24-2", "base", 24, 34.5, 24, drawers=1, doors=2)
for width in (27, 30, 33, 36, 39, 42):
    _add(f"B{width}", "base", width, 34.5, 24, drawers=1, doors=2)

for width in (30, 33, 36, 42, 48):
    _add(f"SB{width}", "base", width, 34.5, 24, notes="Sink base")

_add("FSB36", "base", 36, 34.5, 24, ALL_PREMIER, tuple(), notes="Farm sink base")

for width in (12, 15, 18, 21, 24, 27, 30, 33, 36):
    builder = tuple() if width in (27, 33, 36) else ALL_BUILDER
    _add(f"DB{width}-3", "base", width, 34.5, 24, ALL_PREMIER, builder, drawers=3, doors=0)

_add("DB30-2", "base", 30, 34.5, 24, ALL_PREMIER, tuple(), drawers=2, doors=0)
_add("DB36-2", "base", 36, 34.5, 24, ALL_PREMIER, tuple(), drawers=2, doors=0)
_add("ER33", "base", 33, 34.5, 24, ALL_PREMIER, tuple(), notes="Easy reach base")
_add("ER36", "base", 36, 34.5, 24, notes="Easy reach base")
_add("BB36", "base", 30, 34.5, 24, notes='Blind base, pull 6-9" from wall')
_add("BB42", "base", 36, 34.5, 24, notes='Blind base, pull 6-9" from wall')
_add("BB48", "base", 48, 34.5, 24, notes='Blind base, pull 0-3" from wall')

for height in (84, 90, 96):
    shelves = 5 if height == 96 else 4
    _add(f"P18{height}", "tall", 18, height, 24, shelves=shelves)

for width in (24, 30):
    for height in (84, 90, 96):
        shelves = 5 if height == 96 else 4
        _add(f"P{width}{height}", "tall", width, height, 24, ALL_PREMIER, tuple(), shelves=shelves, doors=2)

_add("OC3396", "tall", 33, 96, 24, drawers=1, notes="Oven cabinet")
_add("TEP3096", "tall", 3, 96, 12, ALL_PREMIER, tuple(), notes="Tall end panel")

for width in (12, 15, 18, 21, 24, 30, 36):
    _add(f"V{width}", "vanity", width, 34.5, 21)

_add("VSBDL30", "vanity", 30, 34.5, 21, notes="Vanity sink base door left")
_add("VSBDR30", "vanity", 30, 34.5, 21, notes="Vanity sink base door right")
_add("F396", "filler", 3, 96, 0.75, notes='3" filler panel')
_add("F696", "filler", 6, 96, 0.75, notes='6" filler panel')
_add("TKS8", "accessory", 96, 4.5, 0.25, notes="Toe kick skin")


def lookup(full_code: str) -> CatalogEntry | None:
    base = full_code.split("-", 1)[-1] if "-" in full_code else full_code
    return CATALOG.get(base)


def get_full_code(prefix: str, base_code: str) -> str:
    return f"{prefix}-{base_code}"


def is_valid_combo(prefix: str, base_code: str) -> bool:
    entry = CATALOG.get(base_code)
    if entry is None:
        return False
    return prefix in entry.premier_lines or prefix in entry.builder_lines
