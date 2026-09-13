import glob
import json
import os
import sys
import time
from PIL import Image

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import ocr
from nirikshan import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel


def dump_real_photos():
    real_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "fixtures", "images", "real")
    out_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "fixtures", "lines")
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(real_dir):
        print("No real photos present")
        return

    image_files = sorted(
        glob.glob(os.path.join(real_dir, "*.png"))
        + glob.glob(os.path.join(real_dir, "*.jpg"))
        + glob.glob(os.path.join(real_dir, "*.jpeg"))
    )

    if not image_files:
        print("No real photos present")
        return

    print(f"{'Photo':<25} | {'Net Qty':<10} | {'MRP':<10} | {'Mfg Date':<10} | {'Phone':<15} | {'PIN':<8} | {'Time (s)':<8} | {'Verdict'}")
    print("-" * 150)

    for img_path in image_files:
        basename = os.path.splitext(os.path.basename(img_path))[0]
        img = Image.open(img_path)
        
        # Max side 2400
        max_side = int(os.environ.get("NIRIKSHAN_MAX_SIDE", "2400"))
        max_dim = max(img.size)
        if max_dim > max_side:
            scale = float(max_side) / max_dim
            new_w = max(1, int(img.size[0] * scale))
            new_h = max(1, int(img.size[1] * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        t0 = time.perf_counter()
        ocr_res = ocr.extract_text(img)
        lines = ocr_res.get("lines", [])
        decl = extract(lines, img.size[0], img.size[1])
        elapsed = time.perf_counter() - t0

        out_json_path = os.path.join(out_dir, f"real_{basename}.json")
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(lines, f, indent=2, ensure_ascii=False)

        app_res = resolve(ContextModel(), decl)
        findings, summary = evaluate(decl, app_res)
        fail_ids = [f.rule_id for f in findings if f.verdict == "FAIL"]
        nr_ids = [f.rule_id for f in findings if f.verdict == "NEEDS_REVIEW"]
        fail_str = ",".join(fail_ids) if fail_ids else "none"
        nr_str = ",".join(nr_ids) if nr_ids else "none"
        verdict_str = f"{summary.status} [FAIL: {fail_str} | NR: {nr_str}]"

        net_qty = f"{decl.net_quantity.value} {decl.net_quantity.unit}" if decl.net_quantity and decl.net_quantity.value else "N/A"
        mrp_val = f"₹{decl.mrp.value}" if decl.mrp and decl.mrp.value else ("crimp" if decl.mrp and decl.mrp.declared_elsewhere else "N/A")
        mfg_date = f"{decl.mfg_date.month}/{decl.mfg_date.year}" if decl.mfg_date and decl.mfg_date.year else ("crimp" if decl.mfg_date and decl.mfg_date.declared_elsewhere else "N/A")
        phone = decl.consumer_care.phone if decl.consumer_care and decl.consumer_care.phone else "N/A"
        pin = decl.manufacturer.pin if decl.manufacturer and decl.manufacturer.pin else "N/A"

        print(f"{basename:<25} | {net_qty:<10} | {mrp_val:<10} | {mfg_date:<10} | {phone:<15} | {pin:<8} | {elapsed:<8.3f} | {verdict_str}")


if __name__ == "__main__":
    dump_real_photos()

