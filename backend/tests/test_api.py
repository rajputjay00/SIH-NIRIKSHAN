import io
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from main import app

client = TestClient(app)


def create_test_image_bytes(fmt="PNG", size=(200, 100), text="TEST LABEL 123"):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), text, fill=(0, 0, 0))
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model_loaded" in data
    assert data["model_version"].startswith("rapidocr_")
    assert "git_sha" in data


@patch("ocr.extract_text")
def test_scan_image_success(mock_extract_text):
    mock_extract_text.return_value = {
        "full_text": "Sample Label\nMRP Rs. 100",
        "lines": [
            {
                "text": "Sample Label",
                "confidence": 0.95,
                "bbox": [[0.0, 0.0], [50.0, 0.0], [50.0, 10.0], [0.0, 10.0]],
            },
            {
                "text": "MRP Rs. 100",
                "confidence": 0.92,
                "bbox": [[0.0, 20.0], [50.0, 20.0], [50.0, 30.0], [0.0, 30.0]],
            },
        ],
        "preprocess_ms": 1.2,
        "ocr_ms": 42.5,
        "elapsed_ms": 43.7,
    }

    img_bytes = create_test_image_bytes(fmt="PNG", size=(200, 150))
    response = client.post(
        "/api/scan",
        files={"file": ("test_label.png", img_bytes, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_label.png"
    assert data["width"] == 200
    assert data["height"] == 150
    assert "ocr" in data
    assert data["ocr"]["full_text"] == "Sample Label\nMRP Rs. 100"
    assert len(data["ocr"]["lines"]) == 2
    mock_extract_text.assert_called_once()


def test_scan_image_unsupported_media_type():
    response = client.post(
        "/api/scan",
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert response.status_code == 415


def test_scan_image_payload_too_large():
    large_bytes = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/api/scan",
        files={"file": ("large.png", large_bytes, "image/png")},
    )
    assert response.status_code == 413


def test_spa_blocks_path_traversal():
    response = client.get("/..%2Fmain.py")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "import fastapi" not in response.text


def test_api_404_returns_json():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "application/json" in response.headers.get("content-type", "")
    assert response.json() == {"detail": "API route not found"}


@pytest.mark.slow
def test_real_ocr_smoke_test():
    img_bytes = create_test_image_bytes(fmt="PNG", size=(400, 200), text="NET QTY 500g")
    response = client.post(
        "/api/scan",
        files={"file": ("smoke_test.png", img_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "smoke_test.png"
    assert "ocr" in data
    assert "full_text" in data["ocr"]
    assert "ocr_ms" in data["ocr"]
