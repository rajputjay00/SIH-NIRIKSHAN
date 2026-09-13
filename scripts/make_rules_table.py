#!/usr/bin/env python3
import sys
import json
import os
import yaml

def generate_table():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cat_path = os.path.join(root_dir, "backend", "nirikshan", "rules", "catalogue.yaml")
    plan_path = os.path.join(root_dir, "frontend", "src", "data", "planned_rules.json")

    with open(cat_path, "r", encoding="utf-8") as f:
        cat_data = yaml.safe_load(f)

    if isinstance(cat_data, dict):
        rules_list = cat_data.get("rules", [])
    else:
        rules_list = cat_data

    active_rules = []
    active_ids = set()

    for r in rules_list:
        r_id = r.get("id")
        if not r_id:
            continue
        active_ids.add(r_id)
        verdicts = ["PASS", "FAIL"]

        unc = r.get("on_uncertain")
        if isinstance(unc, dict):
            verdicts.append(unc.get("verdict", "NEEDS_REVIEW"))
        elif isinstance(unc, list):
            for item in unc:
                if isinstance(item, dict) and "verdict" in item:
                    verdicts.append(item["verdict"])
                else:
                    verdicts.append("NEEDS_REVIEW")
        elif unc:
            verdicts.append("NEEDS_REVIEW")

        if "NEEDS_REVIEW" not in verdicts and r_id in ["R05", "R11", "R16", "R18", "R19", "R21", "R22", "R30", "R34"]:
            verdicts.append("NEEDS_REVIEW")

        active_rules.append({
            "id": r_id,
            "rule_ref": r.get("rule_ref", r_id),
            "title_en": r.get("title_en", r.get("description", r_id)),
            "severity": r.get("severity", "high"),
            "status": "Implemented",
            "verdicts": ", ".join(sorted(list(set(verdicts))))
        })

    planned_rules = []
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
        for pr in plan_data:
            if pr["id"] in active_ids:
                continue
            v_types = "FAIL, PASS"
            if pr["id"] in ["R24", "R28"]:
                v_types = "MANUAL"
            elif pr["id"] in ["R33"]:
                v_types = "INFO"
            elif pr["id"] in ["R16", "R19", "R21", "R22", "R30", "R34"]:
                v_types = "FAIL, NEEDS_REVIEW, PASS"

            planned_rules.append({
                "id": pr["id"],
                "rule_ref": pr.get("rule_ref", pr["id"]),
                "title_en": pr.get("title_en", pr["id"]),
                "severity": pr.get("severity", "medium"),
                "status": "Planned",
                "verdicts": v_types
            })

    all_rules = sorted(active_rules + planned_rules, key=lambda x: int(x["id"].replace("R", "")) if x["id"].replace("R", "").isdigit() else 99)

    lines = [
        "# Nirikshan Legal Metrology Rules Catalogue",
        "",
        f"Total Rules Encoded: **{len(all_rules)}** ({len(active_rules)} Implemented Engine Rules, {len(planned_rules)} Planned M3 Rules)",
        "",
        "| ID | Rule Ref | Title (EN) | Severity | Status | Verdict Types |",
        "|---|---|---|---|---|---|"
    ]

    for r in all_rules:
        lines.append(f"| **{r['id']}** | `{r['rule_ref']}` | {r['title_en']} | {r['severity']} | `{r['status']}` | {r['verdicts']} |")

    lines.append("")
    return "\n".join(lines)

def main():
    content = generate_table()
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_file = os.path.join(root_dir, "docs", "RULES.md")

    if "--check" in sys.argv:
        if not os.path.exists(target_file):
            print(f"Error: {target_file} does not exist.")
            sys.exit(1)
        with open(target_file, "r", encoding="utf-8") as f:
            existing = f.read()
        if existing.strip() != content.strip():
            print("Error: docs/RULES.md is out of date. Run python scripts/make_rules_table.py to update.")
            sys.exit(1)
        print("docs/RULES.md is up to date.")
        sys.exit(0)
    else:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully generated {target_file}")

if __name__ == "__main__":
    main()
