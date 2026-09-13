import os
import pytest
from PIL import Image

import ocr
from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel


SYNTHETIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "fixtures", "images", "synthetic")
)


@pytest.mark.slow
def test_four_violations_synthetic_label():
    img_path = os.path.join(SYNTHETIC_DIR, "four_violations.png")
    assert os.path.exists(img_path), f"Synthetic image {img_path} missing"

    image = Image.open(img_path)
    ocr_result = ocr.extract_text(image)

    declarations = extract(ocr_result.get("lines", []), image.width, image.height)
    context = ContextModel(package_type="retail", category="general")
    applicability = resolve(context, declarations)
    findings, summary = evaluate(declarations, applicability)

    findings_dict = {f.rule_id: f for f in findings}

    for rid in ["R04", "R08", "R12", "R15"]:
        assert rid in findings_dict, f"Expected finding for {rid}"
        f = findings_dict[rid]
        assert f.verdict == "FAIL", f"Expected {rid} to FAIL, got {f.verdict}"
        assert f.evidence_bbox is not None, f"Expected {rid} evidence_bbox to be non-null"

    assert summary.status == "Non-compliant"


@pytest.mark.slow
def test_compliant_synthetic_labels():
    for fname in ["compliant_1.png", "compliant_2.png"]:
        img_path = os.path.join(SYNTHETIC_DIR, fname)
        assert os.path.exists(img_path)

        image = Image.open(img_path)
        ocr_result = ocr.extract_text(image)

        declarations = extract(ocr_result.get("lines", []), image.width, image.height)
        context = ContextModel(package_type="retail", category="general")
        applicability = resolve(context, declarations)
        findings, summary = evaluate(declarations, applicability)
        fail_count = summary.counts.get("FAIL", 0)
        review_count = summary.counts.get("NEEDS_REVIEW", 0)

        assert fail_count == 0, f"Expected 0 FAIL in {fname}, got {fail_count}"
        assert review_count <= 1, f"Expected <= 1 NEEDS_REVIEW in {fname}, got {review_count}"


@pytest.mark.slow
def test_ten_gram_sachet():
    img_path = os.path.join(SYNTHETIC_DIR, "ten_gram_sachet.png")
    assert os.path.exists(img_path)

    image = Image.open(img_path)
    ocr_result = ocr.extract_text(image)

    declarations = extract(ocr_result.get("lines", []), image.width, image.height)
    context = ContextModel(package_type="retail", category="general")
    applicability = resolve(context, declarations)

    assert applicability.exempt_reason is not None
    assert "Rule 26(a)" in applicability.exempt_reason

    findings, summary = evaluate(declarations, applicability)
    for f in findings:
        assert f.verdict == "N/A"
    assert summary.status == "Exempt"


@pytest.mark.slow
def test_food_pack():
    img_path = os.path.join(SYNTHETIC_DIR, "food_pack.png")
    assert os.path.exists(img_path)

    image = Image.open(img_path)
    ocr_result = ocr.extract_text(image)

    declarations = extract(ocr_result.get("lines", []), image.width, image.height)
    context = ContextModel(package_type="retail", category="food")
    applicability = resolve(context, declarations)

    assert "R01" not in applicability.applicable_rule_ids
    assert "R02" not in applicability.applicable_rule_ids
    assert "R10" not in applicability.applicable_rule_ids
    assert "FSS Act" in applicability.reasons["R01"]

    findings, summary = evaluate(declarations, applicability)
    findings_dict = {f.rule_id: f for f in findings}

    assert findings_dict["R01"].verdict == "N/A"
    assert findings_dict["R02"].verdict == "N/A"
    assert findings_dict["R10"].verdict == "N/A"


@pytest.mark.slow
def test_wholesale_pack():
    img_path = os.path.join(SYNTHETIC_DIR, "wholesale_pack.png")
    assert os.path.exists(img_path)

    image = Image.open(img_path)
    ocr_result = ocr.extract_text(image)

    declarations = extract(ocr_result.get("lines", []), image.width, image.height)
    context = ContextModel(package_type="wholesale", category="general")
    applicability = resolve(context, declarations)

    assert applicability.applicable_rule_ids == ["R27"]

    findings, summary = evaluate(declarations, applicability)
    findings_dict = {f.rule_id: f for f in findings}

    assert findings_dict["R27"].verdict == "PASS"
