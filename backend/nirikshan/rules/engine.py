import os
from typing import Any, Dict, List, Optional, Tuple

import yaml
from functools import lru_cache

from nirikshan.rules.predicates import eval_predicate
from nirikshan.schema import ApplicabilityModel, ContextModel, Declarations, FindingModel, SummaryModel


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
    check_node: Dict[str, Any], declarations: Declarations, quality: Optional[Dict[str, Any]] = None
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
                ok, d_list, v, b = eval_check_block(pred_item, declarations, quality)
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
                ok, msg, val, bbox = eval_predicate(pred_name, params, declarations, quality)
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
                ok, d_list, v, b = eval_check_block(pred_item, declarations, quality)
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
                ok, msg, val, bbox = eval_predicate(pred_name, params, declarations, quality)
                details.append(msg)
                if ok:
                    any_ok = True
                if bbox is not None:
                    last_bbox = bbox
                if val is not None:
                    last_val = val

        return any_ok, details, last_val, last_bbox

    return False, ["Invalid check node"], None, None


import datetime

def evaluate(
    declarations: Declarations,
    applicability: ApplicabilityModel,
    quality: Optional[Dict[str, Any]] = None,
    context: Optional[ContextModel] = None,
) -> Tuple[List[FindingModel], SummaryModel]:
    catalogue = load_catalogue()
    findings: List[FindingModel] = []
    counts = {"PASS": 0, "FAIL": 0, "NEEDS_REVIEW": 0, "MANUAL": 0, "INFO": 0, "N/A": 0}

    ref_date = (context.reference_date if context and context.reference_date else None) or datetime.date.today().isoformat()

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

        # Generic effective date check against context.reference_date
        eff_from = rule.get("effective_from")
        eff_to = rule.get("effective_to")
        if (eff_from and ref_date < eff_from) or (eff_to and ref_date > eff_to):
            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict="N/A",
                severity=severity,
                extracted=None,
                expected=None,
                evidence_bbox=None,
                message_en=f"not in force on {ref_date}",
                message_hi=f"{ref_date} को लागू नहीं है",
                fix_hint_en=None,
            )
            findings.append(finding)
            counts["N/A"] += 1
            continue

        # Evaluate rule check
        check_ok, details, extracted_val, bbox = eval_check_block(rule["check"], declarations, quality)

        if check_ok:
            verdict = rule.get("verdict") or rule.get("on_pass") or "PASS"
            msg_en_final = f"Compliant: {rule['title_en']}"
            msg_hi_final = f"अनुपालन: {rule['title_hi']}"

            if "on_uncertain" in rule:
                unc_list = rule["on_uncertain"] if isinstance(rule["on_uncertain"], list) else [rule["on_uncertain"]]
                for unc in unc_list:
                    if "when_pass" in unc:
                        u_ok, _, _, _ = eval_check_block(unc["when_pass"], declarations, quality)
                        if u_ok:
                            verdict = unc.get("verdict", verdict)
                            msg_en_final = unc.get("message_en", msg_en_final)
                            msg_hi_final = unc.get("message_hi", msg_hi_final)
                            break
                    elif "check" in unc:
                        u_ok, _, _, _ = eval_check_block(unc["check"], declarations, quality)
                        if u_ok:
                            verdict = unc.get("verdict", verdict)
                            msg_en_final = unc.get("message_en", msg_en_final)
                            msg_hi_final = unc.get("message_hi", msg_hi_final)
                            break

            finding = FindingModel(
                rule_id=rid,
                rule_ref=rref,
                verdict=verdict,
                severity=severity,
                extracted=extracted_val,
                expected="Compliant declaration",
                evidence_bbox=bbox,
                message_en=msg_en_final,
                message_hi=msg_hi_final,
                fix_hint_en=None,
            )
            findings.append(finding)
            counts[verdict] += 1
        else:
            verdict = rule["on_fail"]
            msg_en_final = msg_en
            msg_hi_final = msg_hi

            if "on_uncertain" in rule:
                unc_list = rule["on_uncertain"] if isinstance(rule["on_uncertain"], list) else [rule["on_uncertain"]]
                for unc in unc_list:
                    if "check" in unc:
                        u_ok, _, _, _ = eval_check_block(unc["check"], declarations)
                        if u_ok:
                            verdict = unc.get("verdict", "NEEDS_REVIEW")
                            msg_en_final = unc.get("message_en", msg_en_final)
                            msg_hi_final = unc.get("message_hi", msg_hi_final)
                            break
                    elif "when" in unc:
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
                message_en=msg_en_final,
                message_hi=msg_hi_final,
                fix_hint_en=fix_hint,
            )
            findings.append(finding)
            counts[verdict] += 1

    # Overall Summary calculation: MANUAL counts towards "Officer review required", INFO never affects status
    if counts["FAIL"] > 0:
        status = "Non-compliant"
    elif counts["NEEDS_REVIEW"] > 0 or counts["MANUAL"] > 0:
        status = "Officer review required"
    elif applicability.exempt_reason:
        status = "Exempt"
    else:
        status = "Compliant"

    summary = SummaryModel(status=status, counts=counts)
    return findings, summary
