import os
from PIL import Image, ImageDraw, ImageFont


def make_synthetic_label(
    text_lines: list,
    output_path: str,
    width: int = 1000,
    height: int = 700,
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
        y += font_size + 5

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    print(f"Generated synthetic label at {output_path}")


def generate_all_synthetic_labels(base_dir: str):
    labels = {
        "compliant_1.png": [
            "WHOLE WHEAT ATTA",
            "MFD BY: ABC FOODS PVT LTD, PUNE - 411001",
            "NET QUANTITY: 500 g",
            "MRP Rs 150.00 (INCL. OF ALL TAXES)",
            "UNIT SALE PRICE Rs 0.30 PER g",
            "MFD DATE: 09/2026",
            "BEST BEFORE 6 MONTHS FROM PACKAGING",
            "CONSUMER CARE CELL:",
            "PHONE: 1800-111-222",
            "EMAIL: CARE@ABC.COM",
            "ADDRESS: PUNE 411001",
        ],
        "compliant_2.png": [
            "RICE FLOUR",
            "PACKED BY: XYZ TRADERS, MUMBAI - 400001",
            "NET QUANTITY: 1 kg",
            "MRP Rs 80.00 (INCL. OF ALL TAXES)",
            "UNIT SALE PRICE Rs 0.08 PER g",
            "PACKED ON: 08/2026",
            "CONSUMER CARE CELL:",
            "PHONE: 1800-222-333",
            "EMAIL: CARE@XYZ.COM",
            "ADDRESS: MUMBAI 400001",
        ],
        "four_violations.png": [
            "IMPORTED SNACK",
            "IMPORTED BY: GLOBAL IMPEX PVT LTD",
            "NET WT 200 gms",
            "MRP Rs 45",
            "CONSUMER CARE PHONE: 1800-999-000 ADDRESS MUMBAI",
        ],
        "ten_gram_sachet.png": [
            "SHAMPOO SACHET",
            "NET QUANTITY: 10 g",
            "MRP Rs 2.00 (INCL. OF ALL TAXES)",
        ],
        "food_pack.png": [
            "BISCUITS",
            "NET QUANTITY: 100 g",
            "MRP Rs 10.00 (INCL. OF ALL TAXES)",
            "UNIT SALE PRICE Rs 0.10 PER g",
            "CONSUMER CARE PHONE: 1800-555-555 EMAIL CARE@FOOD.COM ADDRESS MUMBAI",
        ],
        "wholesale_pack.png": [
            "WHOLESALE PACK",
            "MANUFACTURED BY: BULK CORP, DELHI - 110001",
            "SUGAR CUBE",
            "NET QUANTITY: 50 kg",
        ],
    }

    for fname, lines in labels.items():
        make_synthetic_label(lines, os.path.join(base_dir, fname))


if __name__ == "__main__":
    generate_all_synthetic_labels("backend/tests/fixtures/images/synthetic")
