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


def generate_conflict_crops(
    surface_images_dict: Dict[int, Image.Image],
    findings: List[Dict[str, Any]],
    surfaces_info: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generates side-by-side evidence crops for cross-surface conflict findings.
    Returns list of dicts: [{"rule_id": str, "message": str, "crops": [{"surface_id": int, "surface_name": str, "crop_b64": str}]}]
    """
    surface_names = {s.get("id"): s.get("surface", f"surface_{s.get('id')}").capitalize() for s in surfaces_info}
    conflict_crops_list = []

    for f in findings:
        rule_id = f.get("rule_id", "")
        evidence_refs = f.get("evidence_refs", [])
        verdict = f.get("verdict")

        if not rule_id.startswith("C") and len(evidence_refs) < 2:
            continue
        if verdict not in ["FAIL", "NEEDS_REVIEW"]:
            continue

        crops_for_finding = []
        for ref in evidence_refs:
            sid = ref.get("surface_id")
            bbox = ref.get("bbox")
            if not sid or sid not in surface_images_dict or not bbox:
                continue

            img = surface_images_dict[sid]
            proc_img, _, _ = ocr.preprocess(img)
            w, h = proc_img.width, proc_img.height

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

            crops_for_finding.append({
                "surface_id": sid,
                "surface_name": surface_names.get(sid, f"Surface {sid}"),
                "crop_b64": f"data:image/jpeg;base64,{b64_str}",
            })

        if len(crops_for_finding) >= 2:
            conflict_crops_list.append({
                "rule_id": rule_id,
                "message": f.get("message_en") or f.get("message") or "",
                "crops": crops_for_finding,
            })

    return conflict_crops_list
