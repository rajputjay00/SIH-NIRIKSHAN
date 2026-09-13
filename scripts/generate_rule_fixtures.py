import json
import os
import hashlib

FIXTURES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "fixtures", "rules")
)
CATALOGUE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "nirikshan", "rules", "catalogue.yaml")
)

def main():
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    # Save CATALOGUE_HASH
    with open(CATALOGUE_PATH, "rb") as f:
        cat_hash = hashlib.sha256(f.read()).hexdigest()[:12]
    hash_file = os.path.join(FIXTURES_DIR, "CATALOGUE_HASH")
    with open(hash_file, "w", encoding="utf-8") as f:
        f.write(cat_hash)
    print(f"Wrote CATALOGUE_HASH: {cat_hash}")

    bbox_dummy = [[10, 10], [200, 10], [200, 30], [10, 30]]

    fixtures = {
        "R01": [
            ("pass_1", [{"text": "Manufactured by: ABC Pvt Ltd", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Mfd By: XYZ Foods Ltd", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Packed By: Global Traders", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "MRP Rs 100", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Best Before 6 months", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R02": [
            ("pass_1", [{"text": "Mfd By: ABC Ltd, Pune 411001", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Packed By: XYZ Ltd, Mumbai 400001", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Imported By: Global Ltd, Delhi 110001", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Mfd By: ABC Ltd, Pune Maharashtra", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Packed By: XYZ Ltd, Street 4", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Manufactured By: No Pin Code Address", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R04": [
            ("pass_1", [{"text": "Imported by: ABC Ltd", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Country of Origin: India", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Imported by: ABC Ltd", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Made in Japan", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Imported by: XYZ Ltd", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Country of Origin: USA", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Imported by: ABC Ltd", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Imported by: Foreign Goods Ltd", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Imported by: ImpCorp", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R05": [
            ("pass_1", [{"text": "Generic Name: Whole Wheat Flour", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Quantity 500 g", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Rolled Oats Cereal", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Common Name: Milk Chocolate", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "BRANDONLY", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
            ("fail_2", [{"text": "SUPERBRAND", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
            ("fail_3", [{"text": "ONLYLOGO", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
        ],
        "R06": [
            ("pass_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Quantity: 1.5 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Net Volume: 250 ml", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 1500 g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Net Weight: 0.5 kg", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Net Vol: 1200 ml", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R07": [
            ("pass_1", [{"text": "Net Qty: 12 N", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Quantity: 6 Units", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Net Qty: 100 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 1 Dozen", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Net Quantity: 2 Gross", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Net Qty: 1 Score", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R08": [
            ("pass_1", [{"text": "Net Qty: 200 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Weight: 1 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Net Vol: 500 ml", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Wt 200 gms", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Net Qty: 1 ltr", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Net Weight: 8 oz", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R09": [
            ("pass_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Weight: 1 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Net Volume: 250 ml", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: approx 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Net Weight: minimum 1 kg", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Net Volume: not less than 250 ml", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R10": [
            ("pass_1", [{"text": "Mfg Date: 09/2026", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Packed On: Sep 2026", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Date of Mfd: 15/09/2026", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "MRP Rs 100", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "No Date Line Present", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R11": [
            ("pass_1", [{"text": "Best Before: 6 months from packaging", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Use By: 12/2027", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Expiry Date: Sep 2027", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
            ("fail_2", [{"text": "MRP Rs 100", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
            ("fail_3", [{"text": "No Expiry Line", "confidence": 0.95, "bbox": bbox_dummy}], "NEEDS_REVIEW", True),
        ],
        "R12": [
            ("pass_1", [{"text": "MRP ₹150.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Max Retail Price Rs. 45.00 Inclusive of all taxes", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "M.R.P. : Rs.1O5.00 lncl. of all taxes", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "MRP Rs 45", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "MRP $ 10.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Price: 100", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R14": [
            ("pass_1", [{"text": "MRP ₹100.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Unit Sale Price ₹0.20 per g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "MRP ₹16.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 100 ml", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Unit Sale Price ₹16.00 per 100 ml", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "MRP ₹320.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 2 kg", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Unit Sale Price ₹0.16 per g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "MRP ₹100.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Unit Sale Price ₹0.50 per g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "MRP ₹100.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "MRP ₹50.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 200 g", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Unit Sale Price ₹0.90 per g", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R15": [
            ("pass_1", [{"text": "Consumer Care: Contact Manager, Phone: 1800-222-333, Email: help@nirikshan.in", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Customer Care Cell: Phone: 9876543210 Email: care@brand.com Address: Mumbai", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "For Feedback: Contact Executive, Phone: 1860-111-222 Email: support@corp.com", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Consumer Care Cell: Phone: 1800-222-333 Address: Mumbai 400001", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Consumer Care: Email: care@brand.com Address: Pune", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Customer Care Phone: 1800-111-222", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R23": [
            ("pass_1", [{"text": "Net Quantity 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "शुद्ध मात्रा ५०० ग्राम", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "MRP Rs 150", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "1234567890", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "::: --- :::", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "100.00", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R25": [
            ("pass_1", [{"text": "Net Qty: 5 g", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("pass_2", [{"text": "Net Qty: 8 ml", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("pass_3", [{"text": "Net Qty: 10 g", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("fail_1", [{"text": "Net Qty: 100 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_2", [{"text": "Net Qty: 250 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_3", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
        ],
        "R26": [
            ("pass_1", [{"text": "Net Qty: 30 kg", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("pass_2", [{"text": "Net Qty: 50 L", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("pass_3", [{"text": "Net Qty: 100 kg", "confidence": 0.95, "bbox": bbox_dummy}], "N/A", False),
            ("fail_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_2", [{"text": "Net Qty: 1 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_3", [{"text": "Net Qty: 2 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
        ],
        "R27": [
            ("pass_1", [{"text": "Mfd By: ABC Ltd, Pune 411001", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Generic Name: Wheat Flour", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 50 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Packed By: XYZ Ltd, Mumbai 400001", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Generic Name: Rolled Oats", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 20 N", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Mfd By: Global Corp, Delhi 110001", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Generic Name: Milk Chocolate Bar", "confidence": 0.95, "bbox": bbox_dummy}, {"text": "Net Qty: 100 Units", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 50 kg", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_2", [{"text": "Wholesale Pack", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
            ("fail_3", [{"text": "Generic Name: Sugar", "confidence": 0.95, "bbox": bbox_dummy}], "FAIL", True),
        ],
        "R35": [
            ("pass_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_2", [{"text": "Net Volume: 1 L", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("pass_3", [{"text": "Net Weight: 250 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_1", [{"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_2", [{"text": "Net Qty: 1 kg", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
            ("fail_3", [{"text": "Net Qty: 200 g", "confidence": 0.95, "bbox": bbox_dummy}], "PASS", False),
        ],
    }

    count_total = 0
    for rule_id, tests in fixtures.items():
        rule_dir = os.path.join(FIXTURES_DIR, rule_id)
        os.makedirs(rule_dir, exist_ok=True)
        for fname, lines_data, verdict, is_fail in tests:
            json_file = os.path.join(rule_dir, f"{fname}.json")
            exp_file = os.path.join(rule_dir, f"{fname}.expected.json")

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(lines_data, f, indent=2, ensure_ascii=False)

            exp_dict = {
                rule_id: {
                    "verdict": verdict,
                    "evidence_bbox_non_null": is_fail and (verdict in ["PASS", "FAIL", "NEEDS_REVIEW"])
                }
            }
            with open(exp_file, "w", encoding="utf-8") as f:
                json.dump(exp_dict, f, indent=2, ensure_ascii=False)
            count_total += 1

    print(f"Generated {count_total} fixture files across {len(fixtures)} rules.")

if __name__ == "__main__":
    main()
