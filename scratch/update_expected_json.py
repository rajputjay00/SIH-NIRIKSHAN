import json
import os

lines_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "fixtures", "lines")

expected_truths = {
    "real_Toothpaste back.expected.json": {
        "net_quantity": {"value": 600.0, "unit": "g"},
        "mrp": {"declared_elsewhere": "crimp"},
        "mfg_date": {"month": 10, "year": 2025, "source": "unkeyed"},
        "best_before": {"month": 9, "year": 2027},
        "consumer_care": {"phone": "1800-103-1644", "email": "daburcares@dabur.com"}
    },
    "real_Jam back.expected.json": {
        "net_quantity": {"value": 700.0, "unit": "g"},
        "mrp": {"declared_elsewhere": "crimp"},
        "consumer_care": {"phone": "1800-10-22-221", "email": "LEVER.CARE@UNILEVER.COM"}
    },
    "real_Facewash back.expected.json": {
        "net_quantity": {"value": 150.0, "unit": "ml"},
        "mrp": {"declared_elsewhere": "crimp"},
        "consumer_care": {"phone": "1800-10-22-221"}
    },
    "real_Minoxidil back.expected.json": {
        "mrp": {"declared_elsewhere": "crimp"},
        "consumer_care": {"email": "admin@johnleeindia.com"}
    },
    "real_Shaving foam back.expected.json": {
        "mfg_date": {"declared_elsewhere": "crimp"}
    },
    "real_Baby oil back .expected.json": {
        "net_quantity": {"value": 200.0, "unit": "ml"}
    },
    "real_Pickle back.expected.json": {}
}

for fname, content in expected_truths.items():
    fpath = os.path.join(lines_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2)
    print(f"Updated {fname}")
