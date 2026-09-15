import json
import os
import glob
import pytest

from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel, WeighingInput, LotInput


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
        raw_fixture = json.load(f)

    context_dict = {}
    if isinstance(raw_fixture, dict) and "lines" in raw_fixture:
        lines_data = raw_fixture["lines"]
        context_dict = raw_fixture.get("context", {})
    else:
        lines_data = raw_fixture

    with open(expected_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    declarations = extract(lines_data, 1600, 1200)

    # Determine default context by rule path fallback, then apply fixture context_dict
    ctx = ContextModel()
    if "R27" in fixture_path:
        ctx.package_type = "wholesale"
    if "R11" in fixture_path:
        ctx.category = "food"
    if "R04" in fixture_path:
        ctx.is_import = True
    if "R34" in fixture_path:
        ctx.category = "textile"

    if "package_type" in context_dict:
        ctx.package_type = context_dict["package_type"]
    if "category" in context_dict:
        ctx.category = context_dict["category"]
    if "is_import" in context_dict:
        ctx.is_import = context_dict["is_import"]
    if "reference_date" in context_dict:
        ctx.reference_date = context_dict["reference_date"]
    if "net_quantity" in context_dict:
        nq_val = context_dict["net_quantity"]
        if isinstance(nq_val, (int, float)):
            ctx.net_quantity_override = {"value": float(nq_val), "unit": "g"}
        elif isinstance(nq_val, dict):
            ctx.net_quantity_override = nq_val
    if "weighing" in context_dict:
        ctx.weighing = WeighingInput.model_validate(context_dict["weighing"])
    if "lot" in context_dict:
        ctx.lot = LotInput.model_validate(context_dict["lot"])
    if "channel" in context_dict:
        ctx.channel = context_dict["channel"]
    if "geometry_checks" in context_dict:
        ctx.geometry_checks = bool(context_dict["geometry_checks"])
    if "dual_mrp" in context_dict:
        ctx.dual_mrp = context_dict["dual_mrp"]
    if "listing" in context_dict:
        ctx.listing = context_dict["listing"]
    # fixtures may supply measured contrast (R22): it cannot come from OCR text alone
    for fname, cdata in (context_dict.get("contrast") or {}).items():
        field = getattr(declarations, fname, None)
        if field is not None:
            field.contrast = cdata

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
