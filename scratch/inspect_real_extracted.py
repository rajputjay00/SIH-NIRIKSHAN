import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from nirikshan import extract

lines_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "fixtures", "lines")
files = sorted(glob.glob(os.path.join(lines_dir, "real_*.json")))

for f in files:
    if f.endswith(".expected.json"):
        continue
    name = os.path.basename(f)
    with open(f, "r", encoding="utf-8") as fp:
        lines = json.load(fp)
    decl = extract(lines, 1600, 1200)
    d = {k: v for k, v in decl.model_dump().items() if v is not None}
    print(f"=== {name} ===")
    for k, v in d.items():
        if k in ["scripts_detected"]:
            continue
        print(f"  {k}: {v}")
