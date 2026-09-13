import pytest
from PIL import Image
import ocr


def test_exif_orientation_6_transpose():
    # Create a 200x100 red image (width > height)
    img = Image.new("RGB", (200, 100), color=(255, 0, 0))
    exif = img.getexif()
    exif[274] = 6  # Orientation tag 6 = Rotate 90 CW
    
    # Extract text on image with EXIF orientation 6
    # ImageOps.exif_transpose should rotate it to 100x200
    res = ocr.extract_text(img)
    assert "lines" in res
