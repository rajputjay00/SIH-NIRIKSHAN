import io
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image

from main import app

client = TestClient(app)


def create_test_image_bytes(fmt="PNG", size=(100, 100), color=(255, 0, 0)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
        "elapsed_ms": 42.5,
    }

    img_bytes = create_test_image_bytes(fmt="PNG", size=(200, 150))
    response = client.post(
        "/scan",
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
        "/scan",
        files={"file": ("test.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert response.status_code == 415


def test_scan_image_payload_too_large():
    large_bytes = b"0" * (11 * 1024 * 1024)
    response = client.post(
        "/scan",
        files={"file": ("large.png", large_bytes, "image/png")},
    )
    assert response.status_code == 413
