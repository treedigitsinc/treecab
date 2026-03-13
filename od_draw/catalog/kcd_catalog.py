"""Small, local KCD catalog sufficient for the MVP workflow."""

from od_draw.models.cabinet import CatalogEntry
from od_draw.models.enums import CabinetCategory

PREMIER_PREFIXES = {
    "OW": "Oslo White",
    "OC": "Oslo Classic Walnut",
    "OO": "Oslo Oak",
    "SW": "Shaker White",
    "SK": "Shaker Kodiak",
    "BW": "Brooklyn White",
    "BG": "Brooklyn Gray",
}
BUILDER_PREFIXES = {
    "EW": "Essential White",
    "EG": "Essential Gray",
}
COLOR_LINES = {**PREMIER_PREFIXES, **BUILDER_PREFIXES}

ENTRIES = [
    CatalogEntry("W2436", CabinetCategory.WALL, 24, 36, 12, price=733.0, shelves=2, doors=2),
    CatalogEntry("W3036", CabinetCategory.WALL, 30, 36, 12, price=812.0, shelves=2, doors=2),
    CatalogEntry("W3636", CabinetCategory.WALL, 36, 36, 12, price=908.0, shelves=2, doors=2),
    CatalogEntry("W3615", CabinetCategory.WALL, 36, 15, 12, price=353.0, shelves=1, doors=2),
    CatalogEntry("B09", CabinetCategory.BASE, 9, 34.5, 24, price=359.0, doors=1),
    CatalogEntry("B18", CabinetCategory.BASE, 18, 34.5, 24, price=539.0, doors=1),
    CatalogEntry("B24", CabinetCategory.BASE, 24, 34.5, 24, price=745.0, drawers=1, doors=2),
    CatalogEntry("B30", CabinetCategory.BASE, 30, 34.5, 24, price=881.0, drawers=1, doors=2),
    CatalogEntry("B36", CabinetCategory.BASE, 36, 34.5, 24, price=977.0, drawers=1, doors=2),
    CatalogEntry("SB36", CabinetCategory.BASE, 36, 34.5, 24, price=679.0, doors=2, notes="Sink base"),
    CatalogEntry("DB24-3", CabinetCategory.BASE, 24, 34.5, 24, price=1014.0, drawers=3),
    CatalogEntry("DB30-3", CabinetCategory.BASE, 30, 34.5, 24, price=1157.0, drawers=3),
    CatalogEntry("ER33", CabinetCategory.BASE, 33, 34.5, 24, price=969.0, notes="Easy reach base"),
    CatalogEntry("P2496", CabinetCategory.TALL, 24, 96, 24, price=1675.0, shelves=5, doors=2),
    CatalogEntry("VSBDL30", CabinetCategory.VANITY, 30, 34.5, 21, price=612.0, notes="Vanity sink base door left"),
    CatalogEntry("VSBDR30", CabinetCategory.VANITY, 30, 34.5, 21, price=612.0, notes="Vanity sink base door right"),
    CatalogEntry("V30", CabinetCategory.VANITY, 30, 34.5, 21, price=566.0, doors=2),
    CatalogEntry("F396", CabinetCategory.FILLER, 3, 96, 0.75, price=76.0, notes="3 inch filler"),
    CatalogEntry("F696", CabinetCategory.FILLER, 6, 96, 0.75, price=121.0, notes="6 inch filler"),
    CatalogEntry("TKS8", CabinetCategory.ACCESSORY, 96, 4.5, 0.25, price=0.0, notes="Toe kick skin"),
]

CATALOG = {entry.code: entry for entry in ENTRIES}


def get_prefixed_code(color_prefix: str, base_code: str) -> str:
    return f"{color_prefix}-{base_code}"


def lookup(code: str) -> CatalogEntry:
    prefix, _, remainder = code.partition("-")
    base_code = remainder if prefix in COLOR_LINES and remainder else code
    try:
        return CATALOG[base_code]
    except KeyError as exc:
        raise KeyError(f"Unknown catalog code: {code}") from exc
