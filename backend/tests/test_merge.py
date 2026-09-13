import pytest
from nirikshan.extract import extract
from nirikshan.merge import merge_declarations
from nirikshan.schema import Declarations, SurfaceResultModel, FieldModel, NetQuantity, MRP, DateField, EntityBlock


def test_pdp_surface_priority():
    # Front vs Back for MRP (Front priority 5 > Back priority 4)
    ocr_front = {"lines": [{"id": 1, "text": "MRP Rs. 100.00 INCL. OF ALL TAXES", "confidence": 0.9, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]}
    ocr_back = {"lines": [{"id": 1, "text": "MRP Rs. 100.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]}

    decl_front = extract(ocr_front["lines"], 800, 600)
    decl_back = extract(ocr_back["lines"], 800, 600)

    s1 = SurfaceResultModel(id=1, surface="front", image_size={"width": 800, "height": 600}, scale=1.0, ocr=ocr_front, declarations=decl_front)
    s2 = SurfaceResultModel(id=2, surface="back", image_size={"width": 800, "height": 600}, scale=1.0, ocr=ocr_back, declarations=decl_back)

    merged = merge_declarations([s1, s2])
    assert merged.mrp is not None
    assert merged.mrp.surface_id == 1
    assert merged.mrp.surface == "front"


def test_date_crimp_surface_priority():
    # Mfg date on Front vs Crimp (Crimp has top priority for dates)
    decl_front = Declarations(mfg_date=DateField(value="01/2024", month=1, year=2024, confidence=0.9, surface_id=1, surface="front"))
    decl_crimp = Declarations(mfg_date=DateField(value="01/2024", month=1, year=2024, confidence=0.85, surface_id=2, surface="crimp"))

    s1 = SurfaceResultModel(id=1, surface="front", image_size={"width": 800, "height": 600}, scale=1.0, ocr={}, declarations=decl_front)
    s2 = SurfaceResultModel(id=2, surface="crimp", image_size={"width": 800, "height": 600}, scale=1.0, ocr={}, declarations=decl_crimp)

    merged = merge_declarations([s1, s2])
    assert merged.mfg_date is not None
    assert merged.mfg_date.surface_id == 2
    assert merged.mfg_date.surface == "crimp"


def test_crimp_resolution():
    # Front has declared_elsewhere="crimp", Crimp has value MFD 05/2024
    decl_front = Declarations(
        mfg_date=DateField(declared_elsewhere="crimp", surface_id=1, surface="front")
    )
    decl_crimp = Declarations(
        mfg_date=DateField(value="05/2024", raw="05/2024", month=5, year=2024, confidence=0.95, surface_id=2, surface="crimp", bbox=[[5, 5], [50, 5], [50, 20], [5, 20]])
    )

    s1 = SurfaceResultModel(id=1, surface="front", image_size={"width": 800, "height": 600}, scale=1.0, ocr={}, declarations=decl_front)
    s2 = SurfaceResultModel(id=2, surface="crimp", image_size={"width": 800, "height": 600}, scale=1.0, ocr={}, declarations=decl_crimp)

    merged = merge_declarations([s1, s2])
    assert merged.mfg_date is not None
    assert merged.mfg_date.declared_elsewhere is None
    assert merged.mfg_date.source == "crimp_resolved"
    assert merged.mfg_date.surface_id == 2
    assert merged.mfg_date.surface == "crimp"
    assert merged.mfg_date.month == 5
    assert merged.mfg_date.year == 2024
