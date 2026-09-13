import pytest
from nirikshan.extract import extract
from nirikshan.merge import merge_declarations
from nirikshan.conflicts import detect_conflicts
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel, SurfaceResultModel


C01_FIXTURES = [
    # PASS 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 100.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MRP Rs. 100.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 250.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MFG DATE: 01/2024", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 50.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MRP Rs. 50.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # FAIL 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 100.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MRP Rs. 120.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "FAIL",
    },
    # FAIL 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 250.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "MRP Rs. 300.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "FAIL",
    },
    # FAIL 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MRP Rs. 50.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MRP Rs. 60.00", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "FAIL",
    },
]


C02_FIXTURES = [
    # PASS 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET QUANTITY: 500 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "NET QTY: 500 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET QUANTITY: 1 kg", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "NET QUANTITY: 1000 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET CONTENT: 250 ml", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "NET QTY: 250 ml", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # FAIL 1 (NEEDS_REVIEW)
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET QUANTITY: 500 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "NET QUANTITY: 400 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET QUANTITY: 1 kg", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "NET QUANTITY: 500 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "NET QTY: 250 ml", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "NET QTY: 500 ml", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
]


C03_FIXTURES = [
    # PASS 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFG DATE: 05/2023", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MFG DATE: 05/2023", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFG DATE: 10/2024", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MRP Rs. 100", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "BEST BEFORE: 12/2025", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "BEST BEFORE: 12/2025", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "food"},
        "expected": "PASS",
    },
    # FAIL 1 (NEEDS_REVIEW)
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFG DATE: 05/2023", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MFG DATE: 06/2023", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFG DATE: 10/2024", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MFG DATE: 11/2024", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "BEST BEFORE: 12/2025", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "BEST BEFORE: 01/2026", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "food"},
        "expected": "NEEDS_REVIEW",
    },
]


C04_FIXTURES = [
    # PASS 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFD BY: ABC Foods Pvt Ltd, Industrial Area, Mumbai", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MFD BY: ABC Foods Pvt Ltd, Industrial Area, Mumbai", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 2 (high similarity)
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFD BY: Nirikshan Labs Pvt Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MFD BY: Nirikshan Labs Private Limited", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # PASS 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "PACKED BY: Global Pack Ltd, Sector 5, Delhi 110001", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "NET QTY: 1 kg", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "PASS",
    },
    # FAIL 1 (NEEDS_REVIEW)
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFD BY: ABC Foods Pvt Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "MFD BY: XYZ Enterprises Pvt Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MFD BY: Apex Consumer Products Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "MFD BY: Best Goods Industries Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
    # FAIL 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "PACKED BY: Quality Foods Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "PACKED BY: Super Spices Ltd", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general"},
        "expected": "NEEDS_REVIEW",
    },
]


C05_FIXTURES = [
    # PASS 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "COUNTRY OF ORIGIN: INDIA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "COUNTRY OF ORIGIN: INDIA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "PASS",
    },
    # PASS 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MADE IN USA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "COUNTRY OF ORIGIN: USA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "PASS",
    },
    # PASS 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "COUNTRY OF ORIGIN: JAPAN", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "side", "lines": [{"text": "NET QTY: 1 kg", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "PASS",
    },
    # FAIL 1
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "COUNTRY OF ORIGIN: INDIA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "COUNTRY OF ORIGIN: CHINA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "FAIL",
    },
    # FAIL 2
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "MADE IN USA", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "back", "lines": [{"text": "COUNTRY OF ORIGIN: GERMANY", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "FAIL",
    },
    # FAIL 3
    {
        "surfaces": [
            {"surface": "front", "lines": [{"text": "COUNTRY OF ORIGIN: JAPAN", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
            {"surface": "crimp", "lines": [{"text": "MADE IN UK", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}]},
        ],
        "context": {"package_type": "retail", "category": "general", "is_import": True},
        "expected": "FAIL",
    },
]


def run_conflict_fixtures(rule_id: str, fixtures: list):
    for idx, fix in enumerate(fixtures):
        surface_results = []
        for s_idx, sdata in enumerate(fix["surfaces"], start=1):
            lines = sdata["lines"]
            decl = extract(lines, 800, 600)
            sres = SurfaceResultModel(
                id=s_idx,
                surface=sdata["surface"],
                image_size={"width": 800, "height": 600},
                scale=1.0,
                ocr={"lines": lines},
                declarations=decl,
            )
            surface_results.append(sres)

        conflicts = detect_conflicts(surface_results)
        merged_decl = merge_declarations(surface_results)
        ctx = ContextModel(**fix.get("context", {}))
        applicability = resolve(ctx, merged_decl)
        findings, summary = evaluate(merged_decl, applicability, context=ctx, conflicts=conflicts)

        rule_finding = next((f for f in findings if f.rule_id == rule_id), None)
        assert rule_finding is not None, f"Rule {rule_id} finding missing for fixture {idx}"
        assert rule_finding.verdict == fix["expected"], (
            f"Fixture {idx} for rule {rule_id} expected {fix['expected']}, got {rule_finding.verdict}"
        )


def test_c01_mrp_conflicts():
    run_conflict_fixtures("C01", C01_FIXTURES)


def test_c02_net_qty_conflicts():
    run_conflict_fixtures("C02", C02_FIXTURES)


def test_c03_date_conflicts():
    run_conflict_fixtures("C03", C03_FIXTURES)


def test_c04_manufacturer_conflicts():
    run_conflict_fixtures("C04", C04_FIXTURES)


def test_c05_origin_conflicts():
    run_conflict_fixtures("C05", C05_FIXTURES)
