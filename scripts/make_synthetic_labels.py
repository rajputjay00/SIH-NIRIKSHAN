import os
from PIL import Image, ImageDraw, ImageFont


def make_synthetic_label(
    text_lines: list,
    output_path: str,
    width: int = 800,
    height: int = 600,
    font_size: int = 32,
):
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = None
    if os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = None
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    y = 30
    for line in text_lines:
        draw.text((30, y), line, fill=(0, 0, 0), font=font)
        y += font_size + 15

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"Generated synthetic label at {output_path}")


if __name__ == "__main__":
    sample_text = [
        "NIRIKSHAN SPICES",
        "TURMERIC POWDER",
        "NET QUANTITY: 500 g",
        "MRP Rs 150.00 (INCL. OF ALL TAXES)",
        "MFD: 09/2026",
        "CONSUMER CARE: 1800-123-4567 EMAIL: CARE@NIRIKSHAN.COM",
    ]
    make_synthetic_label(sample_text, "backend/tests/fixtures/images/synthetic_sample.png")
