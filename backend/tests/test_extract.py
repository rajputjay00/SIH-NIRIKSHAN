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
