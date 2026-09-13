import os
import io
import json
import pytest
from PIL import Image

import ocr
from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel
from scripts.make_synthetic_labels import generate_all_synthetic_labels, OUTPUT_DIR


@pytest.mark.slow
def test_synthetic_benchmark_suite():
    if not os.path.exists(OUTPUT_DIR) or len(os.listdir(OUTPUT_DIR)) < 120:
        generate_all_synthetic_labels(OUTPUT_DIR)

    files = sorted(os.listdir(OUTPUT_DIR))
    png_files = [f for f in files if f.endswith(".png")]
    assert len(png_files) >= 60, f"Expected 60 synthetic label images, found {len(png_files)}"

    rule_stats = {}  # rule_id -> {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0}

    for png_name in png_files:
        truth_name = png_name.replace(".png", ".truth.json")
        truth_path = os.path.join(OUTPUT_DIR, truth_name)
        img_path = os.path.join(OUTPUT_DIR, png_name)

        with open(truth_path, "r", encoding="utf-8") as f:
            truth_data = json.load(f)

        image = Image.open(img_path)
        w, h = image.size
        ocr_res = ocr.extract_text(image)
        decl_obj = extract(ocr_res.get("lines", []), w, h)

        context_dict = truth_data.get("context", {})
        ctx = ContextModel(**context_dict)
        app = resolve(ctx, decl_obj)

        findings, summary = evaluate(decl_obj, app, context=ctx)
        actual_map = {f.rule_id: f.verdict for f in findings}
        expected_map = truth_data.get("expected_verdicts", {})

        all_rule_ids = sorted(list(set(list(actual_map.keys()) + list(expected_map.keys()))))

        for rid in all_rule_ids:
            if rid not in rule_stats:
                rule_stats[rid] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0}

            exp = expected_map.get(rid, "N/A")
            act = actual_map.get(rid, "N/A")
            rule_stats[rid]["total"] += 1

            if exp in ["FAIL", "NEEDS_REVIEW", "MANUAL"]:
                if act == exp or act in ["FAIL", "NEEDS_REVIEW", "MANUAL"]:
                    rule_stats[rid]["tp"] += 1
                else:
                    rule_stats[rid]["fn"] += 1
            elif exp in ["PASS", "INFO"]:
                if act in ["PASS", "INFO"]:
                    rule_stats[rid]["tn"] += 1
                else:
                    rule_stats[rid]["fp"] += 1
            elif exp == "N/A":
                if act == "N/A":
                    rule_stats[rid]["tn"] += 1
                else:
                    rule_stats[rid]["fp"] += 1

    # Print precision / recall table
    print("\n" + "=" * 45)
    print(f"{'Rule':<10} {'Precision':<12} {'Recall':<12} {'Total':<8}")
    print("-" * 45)

    for rid in sorted(rule_stats.keys()):
        st = rule_stats[rid]
        tp, fp, fn, total = st["tp"], st["fp"], st["fn"], st["total"]

        prec = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 100.0
        rec = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 100.0

        print(f"{rid:<10} {prec:>9.1f}% {rec:>11.1f}% {total:>7d}")

    print("=" * 45 + "\n")
