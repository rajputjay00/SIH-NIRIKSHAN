import os
import json
import io
import pytest
from pypdf import PdfReader

# WeasyPrint requires Pango/Cairo GTK libraries which run in CI/Docker
weasyprint = pytest.importorskip("weasyprint", reason="WeasyPrint needs Pango; runs in CI/Docker")

from nirikshan.report.render import generate_report_pdf


def test_report_pdf_generation_en():
    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "images", "synthetic", "four_violations.png")
    scan_json_path = os.path.join(os.path.dirname(__file__), "fixtures", "scan_results", "four_violations.json")

    assert os.path.exists(img_path), "four_violations.png missing"
    assert os.path.exists(scan_json_path), "four_violations.json missing"

    with open(img_path, "rb") as f:
        image_bytes = f.read()

    with open(scan_json_path, "r", encoding="utf-8") as f:
        scan_result = json.load(f)

    pdf_bytes = generate_report_pdf(
        image_bytes=image_bytes,
        result_data=scan_result,
        officer_name="Inspector Sharma",
        premises="Warehouse A, New Delhi",
        remarks="Routine inspection",
        language="en",
    )

    assert pdf_bytes.startswith(b"%PDF"), "Output must be valid PDF"
    assert len(pdf_bytes) > 20000, f"Expected PDF size > 20 KB, got {len(pdf_bytes)} bytes"

    # Extract text using pypdf
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""

    assert "R12" in full_text, "English PDF must contain R12"
    assert "Rule 6(1)(e)" in full_text, "English PDF must contain Rule 6(1)(e)"


def test_report_pdf_generation_hi():
    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "images", "synthetic", "four_violations.png")
    scan_json_path = os.path.join(os.path.dirname(__file__), "fixtures", "scan_results", "four_violations.json")

    with open(img_path, "rb") as f:
        image_bytes = f.read()

    with open(scan_json_path, "r", encoding="utf-8") as f:
        scan_result = json.load(f)

    pdf_bytes = generate_report_pdf(
        image_bytes=image_bytes,
        result_data=scan_result,
        officer_name="निरिेक्षक शर्मा",
        premises="नई दिल्ली",
        language="hi",
    )

    assert pdf_bytes.startswith(b"%PDF"), "Output must be valid PDF"
    assert len(pdf_bytes) > 20000, f"Expected PDF size > 20 KB, got {len(pdf_bytes)} bytes"

    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""

    assert "सभी करों" in full_text, "Hindi PDF must contain 'सभी करों'"
