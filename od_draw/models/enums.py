from enum import Enum


class WallStatus(str, Enum):
    EXISTING = "existing"
    TO_REMOVE = "to_remove"
    NEW = "new"


class OpeningType(str, Enum):
    DOOR = "door"
    WINDOW = "window"
    CASED = "cased"


class RoomType(str, Enum):
    KITCHEN = "kitchen"
    DINING = "dining"
    LAUNDRY = "laundry"
    MAIN_BATH = "main_bath"
    BATH = "bath"


class ApplianceType(str, Enum):
    DW = "DW"
    REF = "REF"
    RNG = "RNG"
    MW = "MW"
    WO = "WO"
    SINK = "SINK"


class CabinetCategory(str, Enum):
    WALL = "wall"
    BASE = "base"
    TALL = "tall"
    VANITY = "vanity"
    FILLER = "filler"
    ACCESSORY = "accessory"


class SheetMode(str, Enum):
    COVER = "cover"
    DEMO = "demo"
    LAYOUT = "layout"
    BATH = "bath"
    DETAILS = "details"
