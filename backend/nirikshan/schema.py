from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OCRLine(BaseModel):
    id: Optional[int] = None
    text: str
    confidence: float
    bbox: List[List[float]]


class FieldModel(BaseModel):
    value: Any = None
    raw: Optional[str] = None
    bbox: Optional[List[List[float]]] = None
    confidence: Optional[float] = None
    source_line_ids: List[int] = Field(default_factory=list)
    source: Optional[str] = None
    declared_elsewhere: Optional[str] = None
    surface_id: Optional[int] = None
    surface: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None   # Maap: clear space / aspect estimates
    contrast: Optional[Dict[str, Any]] = None   # Maap: luminance contrast in the box


class NetQuantity(FieldModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    raw_unit: Optional[str] = None
    unit_nonstandard: bool = False
    count: Optional[int] = None
    unit_value: Optional[float] = None
    multipack: bool = False
    qualifier_words: List[str] = Field(default_factory=list)


class MRP(FieldModel):
    value: Optional[float] = None
    currency: Optional[str] = None
    incl_taxes_phrase: bool = False
    paise: Optional[int] = None


class UnitSalePrice(FieldModel):
    value: Optional[float] = None
    per_qty: float = 1.0
    per_unit: Optional[str] = None
    value_per_base_unit: Optional[float] = None


class DateField(FieldModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
    duration_months: Optional[int] = None


class EntityBlock(FieldModel):
    name: Optional[str] = None
    address: Optional[str] = None
    pin: Optional[str] = None
    state: Optional[str] = None
    role: Optional[str] = None


class ConsumerCare(FieldModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class Declarations(BaseModel):
    manufacturer: Optional[EntityBlock] = None
    packer: Optional[EntityBlock] = None
    importer: Optional[EntityBlock] = None
    marketer: Optional[EntityBlock] = None
    entities: List[EntityBlock] = Field(default_factory=list)
    country_of_origin: Optional[FieldModel] = None
    generic_name: Optional[FieldModel] = None
    net_quantity: Optional[NetQuantity] = None
    mrp: Optional[MRP] = None
    unit_sale_price: Optional[UnitSalePrice] = None
    mfg_date: Optional[DateField] = None
    best_before: Optional[DateField] = None
    consumer_care: Optional[ConsumerCare] = None
    scripts_detected: List[str] = Field(default_factory=list)
    multi_unit_note: bool = False
    mrp_candidates: List[FieldModel] = Field(default_factory=list)
    gtin: Optional[FieldModel] = None
    all_text: Optional[str] = None
    @property
    def primary_entity(self) -> Optional[EntityBlock]:
        if self.manufacturer:
            return self.manufacturer
        if self.packer:
            return self.packer
        if self.importer:
            return self.importer
        if self.marketer:
            return self.marketer
        if self.entities:
            for e in self.entities:
                if e.role in ["regd_office", "regd office", "registered office"]:
                    return e
            for e in self.entities:
                if e.role == "unqualified":
                    return e
            return self.entities[0]
        return None


class WeighingInput(BaseModel):
    """Officer-entered measurement of one package (Tol, R31)."""
    gross: Optional[float] = None
    tare: Optional[float] = None
    net: Optional[float] = None
    unit: Optional[str] = None              # unit of the readings; defaults to the declared unit
    resolution: Optional[float] = None      # scale readability, same unit as the readings
    declared_value: Optional[float] = None  # override when OCR did not read the net quantity
    declared_unit: Optional[str] = None


class LotSample(BaseModel):
    gross: Optional[float] = None
    tare: Optional[float] = None
    net: Optional[float] = None


class LotInput(BaseModel):
    """Lot inspection input (Tol, R32) — Rules 19–21, Fifth/Sixth Schedules."""
    lot_size: int
    samples: List[LotSample] = Field(default_factory=list)
    tares: List[float] = Field(default_factory=list)
    unit: Optional[str] = None
    declared_value: Optional[float] = None
    declared_unit: Optional[str] = None


class ContextModel(BaseModel):
    package_type: str = "retail"
    category: str = "general"
    is_import: Optional[bool] = None
    channel: str = "physical"
    net_quantity_override: Optional[Dict[str, Any]] = None
    reference_date: Optional[str] = None
    weighing: Optional[WeighingInput] = None
    lot: Optional[LotInput] = None
    geometry_checks: bool = False                # enables R19/R20 (OCR-box geometry, NEEDS_REVIEW only)
    dual_mrp: Optional[Dict[str, Any]] = None    # set by the pipeline from earlier scans in the session (R17)
    listing: Optional[Dict[str, Any]] = None     # set by /api/listing/check (R29/R30): {"mode": "html"|"screenshot"|"mixed"}


class ApplicabilityModel(BaseModel):
    package_type: str
    category: str
    is_import: bool
    channel: str
    exempt_reason: Optional[str] = None
    applicable_rule_ids: List[str] = Field(default_factory=list)
    reasons: Dict[str, str] = Field(default_factory=dict)


class FindingModel(BaseModel):
    rule_id: str
    rule_ref: str
    verdict: str
    severity: str
    extracted: Any = None
    expected: Optional[str] = None
    evidence_bbox: Optional[List[List[float]]] = None
    evidence_refs: List[Dict[str, Any]] = Field(default_factory=list)
    message_en: str
    message_hi: str
    fix_hint_en: Optional[str] = None
    trail: List[Dict[str, str]] = Field(default_factory=list)


class SummaryModel(BaseModel):
    status: str
    counts: Dict[str, int] = Field(default_factory=dict)


class ConflictSurfaceModel(BaseModel):
    id: int
    surface: str
    value: Any = None
    bbox: Optional[List[List[float]]] = None


class ConflictModel(BaseModel):
    field: str
    surfaces: List[ConflictSurfaceModel] = Field(default_factory=list)
    severity: str


class SurfaceResultModel(BaseModel):
    id: int
    surface: str
    image_size: Dict[str, int]
    scale: float
    ocr: Dict[str, Any]
    quality: Optional[Dict[str, Any]] = None
    declarations: Declarations
