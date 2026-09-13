import pytest
from PIL import Image, ImageDraw, ImageFilter
from nirikshan.quality import assess_quality


def test_quality_sharp_label():
    # Create sharp synthetic text label image (1000x500)
    img = Image.new("RGB", (1000, 500), color=(100, 100, 100))
    draw = ImageDraw.Draw(img)
    for i in range(20):
        draw.text((10, i * 20 + 10), f"Sample text line {i} sharp details", fill=(255, 255, 255))
    
    q = assess_quality(img)
    assert isinstance(q["blur_score"], float)
    assert isinstance(q["glare_ratio"], float)
    assert isinstance(q["dark_ratio"], float)
    assert "blurry" not in q["warnings"]
    assert "glare" not in q["warnings"]


def test_quality_blurry_image():
    # Create image and apply heavy Gaussian blur
    img = Image.new("RGB", (800, 600), color=(128, 128, 128))
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Blurry text line", fill=(0, 0, 0))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6))

    q = assess_quality(blurred)
    assert "blurry" in q["warnings"]
    assert q["blur_score"] < 60.0


def test_quality_glare_image():
    # Create image with 30% pure white patch
    img = Image.new("RGB", (1000, 1000), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    # Draw a 600x600 white patch = 36% of 1000x1000 area
    draw.rectangle([200, 200, 800, 800], fill=(250, 250, 250))

    q = assess_quality(img)
    assert "glare" in q["warnings"]
    assert q["glare_ratio"] > 0.08
