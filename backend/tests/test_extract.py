import glob
import json
import os
import pytest

from nirikshan import extract


def get_fixture_files():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures", "lines")
    json_files = glob.glob(os.path.join(fixtures_dir, "*.json"))
    fixture_files = [f for f in json_files if not f.endswith(".expected.json")]
    return sorted(fixture_files)


@pytest.mark.parametrize("fixture_path", get_fixture_files())
def test_extract_fixtures(fixture_path):
    expected_path = fixture_path.replace(".json", ".expected.json")
    assert os.path.exists(expected_path), f"Missing expected fixture file for {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        lines_data = json.load(f)

    with open(expected_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    decl = extract(lines_data, 1600, 1200)
    decl_dict = decl.model_dump()

    # Verify expected fields
    for field_name, expected_fields in expected_data.items():
        if field_name == "scripts_detected":
            assert expected_fields[0] in decl_dict["scripts_detected"]
            continue

        assert decl_dict.get(field_name) is not None, f"Field {field_name} not extracted in {fixture_path}"
        field_obj = decl_dict[field_name]

        for k, expected_val in expected_fields.items():
            actual_val = field_obj.get(k)
            assert actual_val == expected_val, (
                f"Mismatch in {fixture_path} for {field_name}.{k}: expected {expected_val}, got {actual_val}"
            )


def test_negative_care_product_names():
    cases = [
        "TOOTH & GUM CARE",
        "SKIN CARE LOTION",
        "HAIR CARE OIL"
    ]
    for text in cases:
        lines = [
            {"id": 0, "text": text, "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]}
        ]
        decl = extract(lines, 1600, 1200)
        assert decl.consumer_care is None, f"Expected consumer_care to be None for product name '{text}', got {decl.consumer_care}"


def test_facewash_absorption_cap():
    lines = [
        {"id": 0, "text": "Manufactured By:", "confidence": 0.9, "bbox": [[10, 10], [200, 10], [200, 30], [10, 30]]},
        {"id": 1, "text": "Aroma Personal Care Pvt Ltd", "confidence": 0.9, "bbox": [[10, 35], [200, 35], [200, 55], [10, 55]]},
        {"id": 2, "text": "Plot 12, Industrial Area, Haridwar", "confidence": 0.9, "bbox": [[10, 60], [200, 60], [200, 80], [10, 80]]},
        {"id": 3, "text": "Uttarakhand - 249401", "confidence": 0.9, "bbox": [[10, 85], [200, 85], [200, 105], [10, 105]]},
        {"id": 4, "text": "Extra Line That Should Not Be Absorbed", "confidence": 0.9, "bbox": [[10, 110], [200, 110], [200, 130], [10, 130]]},
    ]
    decl = extract(lines, 1600, 1200)
    assert decl.manufacturer is not None
    assert len(decl.manufacturer.source_line_ids) <= 3, f"Expected at most 3 lines absorbed, got {len(decl.manufacturer.source_line_ids)}"

