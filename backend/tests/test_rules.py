import json
import os
import glob
import pytest

from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "rules")


def get_fixture_files():
    pattern = os.path.join(FIXTURES_DIR, "*", "*.json")
    files = [f for f in glob.glob(pattern) if not f.endswith(".expected.json")]
    return sorted(files)


@pytest.mark.parametrize("fixture_path", get_fixture_files())
def test_rule_fixtures(fixture_path):
    expected_path = fixture_path.replace(".json", ".expected.json")
    assert os.path.exists(expected_path), f"Missing expected file for {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        lines_data = json.load(f)

    with open(expected_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    declarations = extract(lines_data, 1600, 1200)

    # Determine context if wholesale, import, food, R13, R28, or R34 in fixture path
    ctx = ContextModel()
    if "R27" in fixture_path:
        ctx.package_type = "wholesale"
    if "R11" in fixture_path:
        ctx.category = "food"
    if "R04" in fixture_path:
        ctx.is_import = True
    if "R13" in fixture_path:
        ctx.reference_date = "2021-05-01"
    if "R28" in fixture_path:
        ctx.package_type = "combination"
    if "R34" in fixture_path:
        ctx.category = "textile"

    applicability = resolve(ctx, declarations)
    findings, summary = evaluate(declarations, applicability, context=ctx)

    findings_by_id = {f.rule_id: f for f in findings}

    for rule_id, expected_info in expected_data.items():
        assert rule_id in findings_by_id, f"Rule {rule_id} finding missing in {fixture_path}"
        finding = findings_by_id[rule_id]

        expected_verdict = expected_info["verdict"]
        assert finding.verdict == expected_verdict, (
            f"Mismatch in {fixture_path} for {rule_id}: expected {expected_verdict}, got {finding.verdict}"
        )

        if expected_info.get("evidence_bbox_non_null") and finding.verdict in ["FAIL", "PASS", "NEEDS_REVIEW"]:
            if finding.evidence_bbox is not None:
                assert len(finding.evidence_bbox) > 0
