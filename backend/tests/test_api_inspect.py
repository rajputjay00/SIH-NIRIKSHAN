import io
import pytest
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def create_synthetic_image(text_lines):
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    y = 30
    for line in text_lines:
        draw.text((30, y), line, fill=(0, 0, 0), font=font)
        y += 40

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_api_inspect_e2e_two_surfaces():
    front_bytes = create_synthetic_image([
        "NET QUANTITY: 500 g",
        "MRP Rs. 150.00 INCL. OF ALL TAXES",
        "MFD BY: NIRIKSHAN LABS PVT LTD",
    ])
    crimp_bytes = create_synthetic_image([
        "MFD: 05/2024",
        "BATCH NO: B12345",
    ])

    files = [
        ("file_1", ("front.jpg", front_bytes, "image/jpeg")),
        ("file_2", ("crimp.jpg", crimp_bytes, "image/jpeg")),
    ]
    data = {
        "surface_1": "front",
        "surface_2": "crimp",
        "package_type": "retail",
        "category": "general",
    }

    response = client.post("/api/inspect", files=files, data=data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    res = response.json()
    assert "surfaces" in res
    assert len(res["surfaces"]) == 2
    assert res["surfaces"][0]["surface"] == "front"
    assert res["surfaces"][1]["surface"] == "crimp"

    assert "merged" in res
    assert "conflicts" in res
    assert "applicability" in res
    assert "findings" in res
    assert "summary" in res
    assert "rules_version" in res
    assert "timings" in res

    # Verify trail presence on findings
    for f in res["findings"]:
        assert "trail" in f
        assert len(f["trail"]) > 0


def test_api_inspect_pdf_report_generation():
    pytest.importorskip("weasyprint")
    from nirikshan.report.render import generate_report_pdf

    front_bytes = create_synthetic_image([
        "NET QUANTITY: 500 g",
        "MRP Rs. 100.00 INCL. OF ALL TAXES",
    ])
    crimp_bytes = create_synthetic_image([
        "MRP Rs. 120.00 INCL. OF ALL TAXES",
        "MFG DATE: 05/2024",
    ])

    files = [
        ("file_1", ("front.jpg", front_bytes, "image/jpeg")),
        ("file_2", ("crimp.jpg", crimp_bytes, "image/jpeg")),
    ]
    data = {
        "surface_1": "front",
        "surface_2": "crimp",
        "package_type": "retail",
        "category": "general",
    }

    response = client.post("/api/inspect", files=files, data=data)
    assert response.status_code == 200
    inspect_res = response.json()

    surface_bytes_map = {1: front_bytes, 2: crimp_bytes}
    pdf_bytes = generate_report_pdf(
        image_bytes=front_bytes,
        result_data=inspect_res,
        officer_name="Officer Test",
        premises="Premises Test",
        remarks="Multi-surface test",
        language="en",
        surface_images_bytes=surface_bytes_map,
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
