from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PointPayload(BaseModel):
    x: float
    y: float


class WallPayload(BaseModel):
    id: str
    start: PointPayload
    end: PointPayload
    thickness: float = 4.5
    status: Literal["existing", "to_remove", "new"] = "existing"


class OpeningPayload(BaseModel):
    id: str
    wall_id: str
    kind: Literal["door", "window", "cased"]
    position_along_wall: float
    width: float
    height: float = 0.0
    sill_height: float = 0.0
    trim_width: float = 3.5
    verify_in_field: bool = False


class CabinetPayload(BaseModel):
    id: Optional[str] = None
    kcd_code: str
    wall_id: str
    offset_from_wall_start: float
    is_upper: bool = False
    hinge_side: str = "None"
    orientation: str = "standard"
    modifications: List[str] = Field(default_factory=list)


class RoomPayload(BaseModel):
    id: str
    label: str
    room_type: Literal["kitchen", "dining", "laundry", "main_bath", "bath"]
    room_number: int
    ceiling_height: float
    walls: List[WallPayload]
    openings: List[OpeningPayload] = Field(default_factory=list)


class ProjectMetadataPayload(BaseModel):
    address: str
    kcd_color: str
    kcd_style: str
    drawer_type: str
    uppers_height: int
    crown_molding: str
    designer: str


class CreateProjectPayload(ProjectMetadataPayload):
    project_id: Optional[str] = None
    use_sample: bool = False


class GenerationResponse(BaseModel):
    project_id: str
    pdf_url: str
    tsv_url: str
    sheet_urls: Dict[str, str]
