import io
import base64
from typing import Any, Dict, List
from PIL import Image
import ocr


def generate_evidence_crops(image: Image.Image, findings: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generates 12px padded evidence crop images for FAIL and NEEDS_REVIEW findings.
    Returns dict mapping rule_id to Base64 JPEG Data URI string.
    """
    proc_img, image_size, scale = ocr.preprocess(image)
    w, h = proc_img.width, proc_img.height
    crops: Dict[str, str] = {}

    for f in findings:
        verdict = f.get("verdict")
        bbox = f.get("evidence_bbox")
        rule_id = f.get("rule_id", "")

        if verdict not in ["FAIL", "NEEDS_REVIEW"] or not bbox or not rule_id:
            continue

        if isinstance(bbox, list) and len(bbox) == 4:
            if isinstance(bbox[0], list):
                min_x = min(float(pt[0]) for pt in bbox)
                min_y = min(float(pt[1]) for pt in bbox)
                max_x = max(float(pt[0]) for pt in bbox)
                max_y = max(float(pt[1]) for pt in bbox)
            else:
                min_x, min_y, max_x, max_y = [float(v) for v in bbox]
        else:
            continue

        # Add 12px padding around bbox
        pad = 12
        crop_box = [
            max(0, int(min_x - pad)),
            max(0, int(min_y - pad)),
            min(w, int(max_x + pad)),
            min(h, int(max_y + pad)),
        ]

        if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
            continue

        cropped = proc_img.crop(crop_box)
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=92)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        crops[rule_id] = f"data:image/jpeg;base64,{b64_str}"

    return crops
