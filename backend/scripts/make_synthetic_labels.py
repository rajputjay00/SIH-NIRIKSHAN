import os
import io
import json
import random
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "synthetic_labels")
)

FONT_PATHS = [
    "C:/Windows/Fonts/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def get_font(size: int = 24):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def generate_single_label(idx: int, out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    img_filename = f"label_{idx:02d}.png"
    truth_filename = f"label_{idx:02d}.truth.json"

    width, height = 1200, 900
    img = Image.new("RGB", (width, height), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    font_title = get_font(36)
    font_bold = get_font(26)
    font_main = get_font(22)
    font_small = get_font(18)

    # Draw border
    draw.rectangle([20, 20, width - 20, height - 20], outline=(40, 40, 40), width=4)
    draw.line([(width // 2, 30), (width // 2, height - 30)], fill=(200, 200, 200), width=2)

    # Determine scenario and variations
    is_import = (idx % 4 == 0)
    category = "general"
    if idx % 5 == 0:
        category = "food"
    elif idx % 5 == 1:
        category = "cosmetic"
    elif idx % 5 == 2:
        category = "drug"

    pkg_type = "retail"
    if idx == 10:
        pkg_type = "wholesale"
    elif idx == 20:
        pkg_type = "multi_piece"
    elif idx == 30:
        pkg_type = "combination"
    elif idx == 40:
        pkg_type = "not_for_retail"

    # Default variations
    net_qty_str = "NET QUANTITY: 500 g"
    mrp_str = "MRP Rs. 150.00 INCL. OF ALL TAXES"
    mfd_str = "MFG DATE: 05/2024"
    cc_phone = "Consumer Care: 1800-123-4567"
    cc_email = "Email: care@nirikshanlabs.com"
    mfr_name = "MFD BY: NIRIKSHAN LABS PVT LTD"
    mfr_addr = "123 INDUSTRIAL ESTATE, MUMBAI 400001"
    origin_str = "COUNTRY OF ORIGIN: INDIA"
    if is_import:
        origin_str = "COUNTRY OF ORIGIN: USA"

    # Controlled violations
    v_r06_missing_tax = False
    v_r07_nonstandard_unit = False
    v_r09_qualifier = False
    v_r10_missing_email = False
    v_r04_missing_origin = False
    v_r26a_sachet = False
    v_r16_dual_mrp = False

    if 7 <= idx <= 12:
        v_r06_missing_tax = True
        mrp_str = "MRP Rs. 150.00"
    elif 13 <= idx <= 18:
        v_r07_nonstandard_unit = True
        net_qty_str = "NET QUANTITY: 500 gms"
    elif 19 <= idx <= 24:
        v_r09_qualifier = True
        net_qty_str = "NET QUANTITY: approx. 500 g"
    elif 25 <= idx <= 30:
        v_r10_missing_email = True
        cc_email = ""
    elif 31 <= idx <= 36:
        is_import = True
        v_r04_missing_origin = True
        origin_str = ""
    elif 37 <= idx <= 42:
        v_r26a_sachet = True
        net_qty_str = "NET QUANTITY: 8 g"
    elif 55 <= idx <= 60:
        v_r16_dual_mrp = True

    # Render Left Column
    y_left = 50
    draw.text((50, y_left), f"BRAND PRODUCT #{idx:02d}", fill=(20, 40, 100), font=font_title)
    y_left += 60

    draw.text((50, y_left), "COMMON NAME: Premium Wheat Flour", fill=(50, 50, 50), font=font_bold)
    y_left += 50

    draw.text((50, y_left), net_qty_str, fill=(0, 0, 0), font=font_bold)
    y_left += 50

    draw.text((50, y_left), "UNIT SALE PRICE: Rs. 0.30 / g", fill=(0, 0, 0), font=font_main)
    y_left += 50

    if origin_str:
        draw.text((50, y_left), origin_str, fill=(0, 0, 0), font=font_main)
        y_left += 50

    # Draw Barcode mock
    draw.rectangle([50, y_left, 350, y_left + 70], fill=(0, 0, 0))
    draw.rectangle([60, y_left + 5, 80, y_left + 65], fill=(255, 255, 255))
    draw.rectangle([100, y_left + 5, 115, y_left + 65], fill=(255, 255, 255))
    draw.rectangle([140, y_left + 5, 170, y_left + 65], fill=(255, 255, 255))
    draw.rectangle([190, y_left + 5, 210, y_left + 65], fill=(255, 255, 255))
    draw.rectangle([230, y_left + 5, 260, y_left + 65], fill=(255, 255, 255))
    draw.rectangle([280, y_left + 5, 310, y_left + 65], fill=(255, 255, 255))
    draw.text((50, y_left + 75), "GTIN: 8901234567890", fill=(0, 0, 0), font=font_small)

    # Render Right Column
    y_right = 50
    draw.text((630, y_right), mfr_name, fill=(0, 0, 0), font=font_bold)
    y_right += 40
    draw.text((630, y_right), mfr_addr, fill=(50, 50, 50), font=font_main)
    y_right += 60

    draw.text((630, y_right), mrp_str, fill=(0, 0, 0), font=font_bold)
    y_right += 45

    if v_r16_dual_mrp:
        draw.text((630, y_right), "SPECIAL OFFER MRP Rs. 180.00 INCL. TAXES", fill=(0, 0, 0), font=font_bold)
        y_right += 45

    draw.text((630, y_right), mfd_str, fill=(0, 0, 0), font=font_main)
    y_right += 45

    draw.text((630, y_right), "FOR COMPLAINTS / FEEDBACK CONTACT:", fill=(0, 0, 0), font=font_bold)
    y_right += 35
    draw.text((630, y_right), cc_phone, fill=(0, 0, 0), font=font_main)
    y_right += 35
    if cc_email:
        draw.text((630, y_right), cc_email, fill=(0, 0, 0), font=font_main)
        y_right += 35

    img_path = os.path.join(out_dir, img_filename)
    img.save(img_path, format="PNG")

    # Build expected truth dictionary
    expected_verdicts = {}
    
    # Generic expectations based on violations
    if category == "drug" or v_r26a_sachet or (pkg_type in ["wholesale", "not_for_retail"]):
        # Exempt package
        for r in ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R21", "R23", "R25", "R26", "R33", "R34", "R35", "C01", "C02", "C03", "C04", "C05"]:
            expected_verdicts[r] = "N/A"
        if pkg_type == "wholesale":
            expected_verdicts["R27"] = "PASS"
    else:
        expected_verdicts["R01"] = "PASS"
        expected_verdicts["R02"] = "PASS"
        expected_verdicts["R03"] = "INFO"
        expected_verdicts["R04"] = "FAIL" if (is_import and v_r04_missing_origin) else ("PASS" if is_import else "N/A")
        expected_verdicts["R05"] = "PASS"
        expected_verdicts["R06"] = "FAIL" if v_r06_missing_tax else "PASS"
        expected_verdicts["R07"] = "FAIL" if v_r07_nonstandard_unit else "PASS"
        expected_verdicts["R08"] = "PASS"
        expected_verdicts["R09"] = "FAIL" if v_r09_qualifier else "PASS"
        expected_verdicts["R10"] = "FAIL" if v_r10_missing_email else "PASS"
        expected_verdicts["R11"] = "N/A"
        expected_verdicts["R12"] = "PASS"
        expected_verdicts["R13"] = "N/A"
        expected_verdicts["R14"] = "PASS"
        expected_verdicts["R15"] = "PASS"
        expected_verdicts["R16"] = "NEEDS_REVIEW" if v_r16_dual_mrp else "PASS"
        expected_verdicts["R21"] = "PASS"
        expected_verdicts["R23"] = "PASS"
        expected_verdicts["R24"] = "PASS"
        expected_verdicts["R25"] = "PASS"
        expected_verdicts["R26"] = "PASS"
        expected_verdicts["R27"] = "N/A"
        expected_verdicts["R28"] = "MANUAL" if pkg_type in ["multi_piece", "combination"] else "N/A"
        expected_verdicts["R33"] = "PASS"
        expected_verdicts["R34"] = "N/A"
        expected_verdicts["R35"] = "PASS" if category == "food" else "N/A"
        expected_verdicts["C01"] = "PASS"
        expected_verdicts["C02"] = "PASS"
        expected_verdicts["C03"] = "PASS"
        expected_verdicts["C04"] = "PASS"
        expected_verdicts["C05"] = "PASS" if is_import else "N/A"

    truth_data = {
        "filename": img_filename,
        "context": {
            "package_type": pkg_type,
            "category": category,
            "is_import": is_import,
        },
        "expected_verdicts": expected_verdicts,
    }

    truth_path = os.path.join(out_dir, truth_filename)
    with open(truth_path, "w", encoding="utf-8") as f:
        json.dump(truth_data, f, indent=2)

    return truth_data


def generate_all_synthetic_labels(out_dir: str = OUTPUT_DIR) -> List[Dict[str, Any]]:
    print(f"Generating 60 synthetic labels in {out_dir}...")
    results = []
    for i in range(1, 61):
        tdata = generate_single_label(i, out_dir)
        results.append(tdata)
    print("Done generating 60 synthetic labels.")
    return results


if __name__ == "__main__":
    generate_all_synthetic_labels()
