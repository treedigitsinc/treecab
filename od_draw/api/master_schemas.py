from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MasterPointPayload(BaseModel):
    x: float
    y: float


class MasterSizePayload(BaseModel):
    width: float
    height: float


class MasterRectPayload(BaseModel):
    x: float
    y: float
    width: float
    height: float


class MasterProjectCreatePayload(BaseModel):
    project_id: Optional[str] = None
    address: str
    project_type: str = "Kitchen"
    kcd_color: str = "OW"
    kcd_style: str = "Oslo"
    drawer_type: str = "slab"
    uppers_height: int = 36
    crown_molding: str = "Flat"
    status: str = "A1_Request"
    date: str = ""
    use_sample: bool = False


class CalibrationPayload(BaseModel):
    pdf_point_a: MasterPointPayload
    pdf_point_b: MasterPointPayload
    model_point_a: MasterPointPayload
    model_point_b: MasterPointPayload
    known_distance: float


class MasterWallCreatePayload(BaseModel):
    id: Optional[str] = None
    start: MasterPointPayload
    end: MasterPointPayload
    thickness: float = 4.5
    status: Literal["existing", "to_remove", "new"] = "existing"


class MasterCabinetPlacePayload(BaseModel):
    id: Optional[str] = None
    kcd_code: str
    position: MasterPointPayload
    wall_id: str = ""
    is_upper: bool = False
    hinge_side: str = "None"
    color_prefix: Optional[str] = None
    modifications: List[str] = Field(default_factory=list)


class MasterCabinetMovePayload(BaseModel):
    position: MasterPointPayload
    wall_id: str = ""
    hinge_side: str = "None"
    modifications: List[str] = Field(default_factory=list)


class MasterSheetCreatePayload(BaseModel):
    sheet_number: str
    description: str
    purpose: Literal["FOR BID", "FOR CONSTRUCTION"] = "FOR BID"
    scale: str = '1/2" = 1\'-0"'
    date: str = ""
    designer: str = "YES"
    has_notes_sidebar: bool = True
    notes_template: str = "kitchen_bid"


class MasterViewportPayload(BaseModel):
    id: Optional[str] = None
    label: str
    crop_rect: MasterRectPayload
    scale: str = '1/2" = 1\'-0"'
    scale_factor: Optional[float] = None
    position_on_sheet: MasterPointPayload
    size_on_sheet: MasterSizePayload
    render_layers: List[str] = Field(
        default_factory=lambda: ["underlay", "walls", "openings", "cabinets", "appliances", "dimensions", "annotations"]
    )
    is_active: bool = False


class DimensionVerificationPayload(BaseModel):
    id: str
    value: float


class MasterGenerationResponse(BaseModel):
    project_id: str
    drawing_type: str
    pdf_url: Optional[str] = None
    tsv_url: str
    sheet_pdf_urls: Dict[str, str] = Field(default_factory=dict)
    sheet_typst_urls: Dict[str, str] = Field(default_factory=dict)
    viewport_svg_urls: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
