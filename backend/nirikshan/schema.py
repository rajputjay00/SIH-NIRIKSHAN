from typing import Any, List, Optional
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


class NetQuantity(FieldModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    raw_unit: Optional[str] = None
    unit_nonstandard: bool = False
    count: Optional[int] = None
    qualifier_words: List[str] = Field(default_factory=list)


class MRP(FieldModel):
    value: Optional[float] = None
    currency: Optional[str] = None
    incl_taxes_phrase: bool = False
    paise: Optional[int] = None


class UnitSalePrice(FieldModel):
    value: Optional[float] = None
    per_unit: Optional[str] = None


class DateField(FieldModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None


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
    country_of_origin: Optional[FieldModel] = None
    generic_name: Optional[FieldModel] = None
    net_quantity: Optional[NetQuantity] = None
    mrp: Optional[MRP] = None
    unit_sale_price: Optional[UnitSalePrice] = None
    mfg_date: Optional[DateField] = None
    best_before: Optional[DateField] = None
    consumer_care: Optional[ConsumerCare] = None
    scripts_detected: List[str] = Field(default_factory=list)
