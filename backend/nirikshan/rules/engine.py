import os
from typing import Any, Dict, List, Tuple
import yaml
from functools import lru_cache

from nirikshan.rules.predicates import eval_predicate
from nirikshan.schema import ApplicabilityModel, Declarations, FindingModel, SummaryModel


CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "catalogue.yaml")


@lru_cache(maxsize=1)
def load_catalogue() -> List[Dict[str, Any]]:
    if not os.path.exists(CATALOGUE_PATH):
        raise FileNotFoundError(f"Catalogue file not found at {CATALOGUE_PATH}")

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        catalogue = yaml.safe_load(f)

    if not isinstance(catalogue, list):
        raise ValueError("catalogue.yaml must contain a list of rule definitions")

    required_keys = [
        "id", "key", "rule_ref", "title_en", "title_hi",
        "severity", "check", "on_fail", "message_en", "message_hi"
    ]
    for idx, rule in enumerate(catalogue):
        for k in required_keys:
            if k not in rule:
                raise ValueError(f"Rule at index {idx} (id={rule.get('id')}) missing required key '{k}'")

    return catalogue


def eval_check_block(
    check_node: Dict[str, Any], declarations: Declarations
) -> Tuple[bool, List[str], Any, Any]:
    """Evaluates a check node containing 'all' or 'any'.
    Returns (is_success, details_list, last_extracted_val, last_bbox).
    """
    if "all" in check_node:
        preds = check_node["all"]
        all_ok = True
        details = []
        last_val = None
        last_bbox = None

        for pred_item in preds:
            if "any" in pred_item:
                ok, d_list, v, b = eval_check_block(pred_item, declarations)
                details.extend(d_list)
                if not ok:
                    all_ok = False
                if b is not None:
                    last_bbox = b
                if v is not None:
                    last_val = v
            else:
                pred_name = list(pred_item.keys())[0]
                params = pred_item[pred_name]
                ok, msg, val, bbox = eval_predicate(pred_name, params, declarations)
                details.append(msg)
                if not ok:
                    all_ok = False
                if bbox is not None:
                    last_bbox = bbox
                if val is not None:
                    last_val = val

        return all_ok, details, last_val, last_bbox

    elif "any" in check_node:
        preds = check_node["any"]
        any_ok = False
        details = []
        last_val = None
        last_bbox = None

        for pred_item in preds:
            if "all" in pred_item:
                ok, d_list, v, b = eval_check_block(pred_item, declarations)
                details.extend(d_list)
                if ok:
                    any_ok = True
                if b is not None:
                    last_bbox = b
                if v is not None:
                    last_val = v
            else:
                pred_name = list(pred_item.keys())[0]
                params = pred_item[pred_name]
                ok, msg, val, bbox = eval_predicate(pred_name, params, declarations)
                details.append(msg)
                if ok:
                    any_ok = True
                if bbox is not None:
                    last_bbox = bbox
                if val is not None:
                    last_val = val

        return any_ok, details, last_val, last_bbox

    return False, ["Invalid check node"], None, None


def evaluate(
    declarations: Declarations, applicability: ApplicabilityModel
) -> Tuple[List[FindingModel], SummaryModel]:
    catalogue = load_catalogue()
    findings: List[FindingModel] = []
    counts = {"PASS": 0, "FAIL": 0, "NEEDS_REVIEW": 0, "N/A": 0}

    for rule in catalogue:
        rid = rule["id"]
        rref = rule["rule_ref"]
        severity = rule["severity"]
        msg_en = rule["message_en"]
        msg_hi = rule["message_hi"]
        fix_hint = rule.get("fix_hint_en")

        # Gating R35 food INFO finding
        if rid == "R35" and applicability.category == "food":
            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict="PASS",
                severity="low",
                extracted="category=food",
                expected="FSS Act alignment",
                evidence_bbox=declarations.net_quantity.bbox if declarations.net_quantity else None,
                message_en=msg_en,
                message_hi=msg_hi,
                fix_hint_en=fix_hint,
            )
            findings.append(finding)
            counts["PASS"] += 1
            continue

        # Check applicability
        if rid not in applicability.applicable_rule_ids:
            reason = applicability.reasons.get(rid, "Not applicable for this package context")
            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict="N/A",
                severity=severity,
                extracted=None,
                expected=None,
                evidence_bbox=None,
                message_en=reason,
                message_hi=reason,
                fix_hint_en=None,
            )
            findings.append(finding)
            counts["N/A"] += 1
            continue

        # Evaluate rule check
        check_ok, details, extracted_val, bbox = eval_check_block(rule["check"], declarations)

        if check_ok:
            verdict = "PASS"
            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict=verdict,
                severity=severity,
                extracted=extracted_val,
                expected="Compliant declaration",
                evidence_bbox=bbox,
                message_en=f"Compliant: {rule['title_en']}",
                message_hi=f"अनुपालन: {rule['title_hi']}",
                fix_hint_en=None,
            )
            findings.append(finding)
            counts[verdict] += 1
        else:
            # Check on_uncertain condition
            verdict = rule["on_fail"]
            if "on_uncertain" in rule:
                unc = rule["on_uncertain"]
                cond = unc.get("when", "")
                if cond == "declarations.mrp.confidence < 0.75":
                    if declarations.mrp and (declarations.mrp.confidence or 0.0) < 0.75:
                        verdict = unc.get("verdict", "NEEDS_REVIEW")
                elif cond == "declarations.manufacturer.confidence < 0.75":
                    if declarations.manufacturer and (declarations.manufacturer.confidence or 0.0) < 0.75:
                        verdict = unc.get("verdict", "NEEDS_REVIEW")
                elif cond == "declarations.mfg_date.raw is not None and declarations.mfg_date.month is None":
                    if declarations.mfg_date and declarations.mfg_date.raw and declarations.mfg_date.month is None:
                        verdict = unc.get("verdict", "NEEDS_REVIEW")

            expected_str = "; ".join(details)
            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict=verdict,
                severity=severity,
                extracted=extracted_val,
                expected=expected_str,
                evidence_bbox=bbox,
                message_en=msg_en,
                message_hi=msg_hi,
                fix_hint_en=fix_hint,
            )
            findings.append(finding)
            counts[verdict] += 1

    # Overall Summary calculation
    if counts["FAIL"] > 0:
        status = "Non-compliant"
    elif counts["NEEDS_REVIEW"] > 0:
        status = "Officer review required"
    else:
        status = "Compliant"

    summary = SummaryModel(status=status, counts=counts)
    return findings, summary
