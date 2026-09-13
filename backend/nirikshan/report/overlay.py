import io
import base64
from typing import Any, Dict, List
from PIL import Image, ImageDraw, ImageFont
import ocr


COLOR_MAP = {
    "PASS": {"stroke": (16, 185, 129, 255), "fill": (16, 185, 129, 35)},
    "FAIL": {"stroke": (239, 68, 68, 255), "fill": (239, 68, 68, 40)},
    "NEEDS_REVIEW": {"stroke": (245, 158, 11, 255), "fill": (245, 158, 11, 40)},
}


def create_overlay_image(image: Image.Image, findings: List[Dict[str, Any]]) -> Image.Image:
    """Draws finding evidence bounding boxes and rule ID labels on the preprocessed image."""
    proc_img, image_size, scale = ocr.preprocess(image)
    overlay_img = proc_img.copy().convert("RGBA")
    draw = ImageDraw.Draw(overlay_img, "RGBA")

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    for f in findings:
        verdict = f.get("verdict")
        bbox = f.get("evidence_bbox")
        rule_id = f.get("rule_id", "")

        if not bbox or verdict not in COLOR_MAP:
            continue

        colors = COLOR_MAP[verdict]

        # bbox can be [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] or [minX, minY, maxX, maxY]
        if isinstance(bbox, list) and len(bbox) == 4:
            if isinstance(bbox[0], list):
                pts = [(float(pt[0]), float(pt[1])) for pt in bbox]
                draw.polygon(pts, fill=colors["fill"], outline=colors["stroke"], width=3)
                min_x = min(pt[0] for pt in pts)
                min_y = min(pt[1] for pt in pts)
            else:
                min_x, min_y, max_x, max_y = [float(v) for v in bbox]
                draw.rectangle([min_x, min_y, max_x, max_y], fill=colors["fill"], outline=colors["stroke"], width=3)
        else:
            continue

        # Draw Rule ID tag badge
        badge_padding = 4
        text_bbox = draw.textbbox((0, 0), rule_id, font=font)
        tw = text_bbox[2] - text_bbox[0]
        th = text_bbox[3] - text_bbox[1]
        badge_rect = [min_x, max(0, min_y - th - badge_padding * 2), min_x + tw + badge_padding * 2, max(0, min_y)]
        draw.rectangle(badge_rect, fill=colors["stroke"])
        draw.text((min_x + badge_padding, max(0, min_y - th - badge_padding)), rule_id, fill=(255, 255, 255, 255), font=font)

    return overlay_img.convert("RGB")


def overlay_image_to_base64(image: Image.Image, findings: List[Dict[str, Any]]) -> str:
    """Returns Base64 Data URI string of overlay image."""
    overlay_img = create_overlay_image(image, findings)
    buf = io.BytesIO()
    overlay_img.save(buf, format="JPEG", quality=90)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"
