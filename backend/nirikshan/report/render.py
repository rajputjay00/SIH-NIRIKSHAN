import io
import os
import sys
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from PIL import Image
from jinja2 import Template
import qrcode

if sys.platform == "win32":
    for gtk_path in [r"C:\Users\rajpu\GTK3\runtime_bin", r"C:\Program Files\GTK3-Runtime Win64\bin"]:
        if os.path.exists(gtk_path):
            os.environ["PATH"] = gtk_path + ";" + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(gtk_path)
                except Exception:
                    pass

from nirikshan.report.overlay import overlay_image_to_base64
from nirikshan.report.crops import generate_evidence_crops, generate_conflict_crops

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.html")


def generate_qr_code_b64(content: str) -> str:
    """Generates QR code image as Base64 Data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def sort_findings(findings: list, language: str) -> list:
    """Sorts findings in order: FAIL -> NEEDS_REVIEW -> PASS -> N/A and picks language message."""
    order = {"FAIL": 0, "NEEDS_REVIEW": 1, "PASS": 2, "N/A": 3}
    sorted_list = sorted(findings, key=lambda f: order.get(f.get("verdict", "N/A"), 4))
    
    for f in sorted_list:
        if language == "hi":
            f["message"] = f.get("message_hi") or f.get("message_en") or ""
        else:
            f["message"] = f.get("message_en") or ""
    return sorted_list


def generate_report_pdf(
    image_bytes: bytes,
    result_data: Dict[str, Any],
    officer_name: Optional[str] = None,
    premises: Optional[str] = None,
    remarks: Optional[str] = None,
    language: str = "en",
    surface_images_bytes: Optional[Dict[int, bytes]] = None,
) -> bytes:
    """Renders HTML via Jinja2 and generates PDF bytes using WeasyPrint."""
    import weasyprint

    image = Image.open(io.BytesIO(image_bytes))
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()

    # IST Timestamp
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    timestamp_ist = datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S IST")

    findings = sort_findings(result_data.get("findings", []), language)
    crops = generate_evidence_crops(image, findings)

    surfaces_info = result_data.get("surfaces", [])
    surface_overlays = []
    conflict_crops = []

    if surfaces_info:
        surface_images_dict = {}
        for s in surfaces_info:
            sid = s.get("id", 1)
            sname = s.get("surface", "front").capitalize()
            if surface_images_bytes and sid in surface_images_bytes:
                s_img = Image.open(io.BytesIO(surface_images_bytes[sid]))
            else:
                s_img = image
            surface_images_dict[sid] = s_img
            overlay_uri = overlay_image_to_base64(s_img, findings, surface_id=sid)
            surface_overlays.append({"id": sid, "surface": sname, "overlay_b64": overlay_uri})

        conflict_crops = generate_conflict_crops(surface_images_dict, findings, surfaces_info)
    else:
        overlay_b64 = overlay_image_to_base64(image, findings)
        surface_overlays = [{"id": 1, "surface": "Front", "overlay_b64": overlay_b64}]

    overlay_b64 = surface_overlays[0]["overlay_b64"] if surface_overlays else ""

    rules_ver = result_data.get("rules_version", "0.1.0")
    model_ver = result_data.get("model_version", "rapidocr_1.4.4")
    extractor_ver = result_data.get("extractor_version", "0.1.0")
    git_sha = os.getenv("GIT_SHA", "dev")

    # QR Code content: NIRIKSHAN|<sha256>|<rules_version>|<timestamp>
    qr_payload = f"NIRIKSHAN|{image_sha256}|{rules_ver}|{timestamp_ist}"
    qr_b64 = generate_qr_code_b64(qr_payload)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    template = Template(template_str)
    rendered_html = template.render(
        language=language,
        timestamp_ist=timestamp_ist,
        officer_name=officer_name,
        premises=premises,
        remarks=remarks,
        summary=result_data.get("summary", {}),
        applicability=result_data.get("applicability", {}),
        overlay_b64=overlay_b64,
        surface_overlays=surface_overlays,
        conflict_crops=conflict_crops,
        findings=findings,
        crops=crops,
        declarations=result_data.get("declarations", {}) or result_data.get("merged", {}),
        image_sha256=image_sha256,
        rules_version=rules_ver,
        model_version=model_ver,
        extractor_version=extractor_ver,
        git_sha=git_sha,
        qr_b64=qr_b64,
    )

    pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()
    return pdf_bytes
