import re
from typing import Any, Dict, List, Optional, Tuple
from nirikshan.schema import Declarations


COUNT_WORDS = ["dozen", "score", "gross", "great gross", "doz"]


def get_field_value(declarations: Declarations, field_path: str) -> Any:
    """Resolve dot-notation path like 'net_quantity.value' on Declarations object."""
    if not field_path:
        return None
    parts = field_path.split(".")
    curr: Any = declarations
    for part in parts:
        if curr is None:
            return None
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif hasattr(curr, part):
            curr = getattr(curr, part)
        else:
            return None
    return curr


def eval_predicate(
    pred_name: str, params: Dict[str, Any], declarations: Declarations
) -> Tuple[bool, Optional[str], Any, Optional[List[List[float]]]]:
    """Evaluates a named predicate against Declarations.
    Returns (is_success, detail_message, extracted_val, evidence_bbox).
    """
    field_path = params.get("field", "")
    extracted_val = get_field_value(declarations, field_path) if field_path else None
    
    # Get bbox for evidence if available
    bbox = None
    if field_path:
        base_obj_path = field_path.rsplit(".", 1)[0] if "." in field_path else field_path
        base_obj = get_field_value(declarations, base_obj_path)
        if hasattr(base_obj, "bbox"):
            bbox = getattr(base_obj, "bbox")
    if bbox is None and field_path == "country_of_origin.value" and declarations.importer and hasattr(declarations.importer, "bbox"):
        bbox = declarations.importer.bbox

    if pred_name == "present":
        ok = extracted_val is not None and str(extracted_val).strip() != ""
        msg = f"Value '{extracted_val}' present" if ok else f"Field {field_path} is missing or empty"
        return ok, msg, extracted_val, bbox

    elif pred_name == "absent":
        ok = extracted_val is None or str(extracted_val).strip() == ""
        msg = f"Field {field_path} is absent" if ok else f"Field {field_path} is present"
        return ok, msg, extracted_val, bbox

    elif pred_name == "regex":
        pattern = params.get("pattern", "")
        if extracted_val is None:
            return False, f"Field {field_path} is missing", None, bbox
        matched = bool(re.search(pattern, str(extracted_val), re.IGNORECASE))
        msg = f"Pattern '{pattern}' matched" if matched else f"Pattern '{pattern}' not matched in '{extracted_val}'"
        return matched, msg, extracted_val, bbox

    elif pred_name == "unit_standard":
        nq = declarations.net_quantity
        if not nq or not nq.unit:
            return False, "Net quantity or unit missing", None, None
        ok = not nq.unit_nonstandard
        msg = f"Unit '{nq.raw_unit or nq.unit}' is standard" if ok else f"Unit '{nq.raw_unit or nq.unit}' is non-standard"
        return ok, msg, nq.raw_unit or nq.unit, nq.bbox

    elif pred_name == "magnitude_unit_consistent":
        nq = declarations.net_quantity
        if not nq or nq.value is None or not nq.unit:
            return False, "Net quantity value or unit missing", None, None
        val = nq.value
        u = str(nq.unit).lower()
        if u in ["g", "ml"] and val >= 1000.0:
            return False, f"{val} {u} should be expressed as {val/1000.0:.2f} {'kg' if u=='g' else 'L'}", f"{val} {u}", nq.bbox
        if u in ["kg", "l"] and val < 1.0:
            return False, f"{val} {u} should be expressed as {val*1000.0:.0f} {'g' if u=='kg' else 'ml'}", f"{val} {u}", nq.bbox
        return True, f"{val} {u} magnitude and unit consistent", f"{val} {u}", nq.bbox

    elif pred_name == "no_count_words":
        nq = declarations.net_quantity
        raw_text = (nq.raw if nq and nq.raw else "").lower()
        for cw in COUNT_WORDS:
            if cw in raw_text:
                return False, f"Count word '{cw}' prohibited in net quantity declaration", cw, nq.bbox if nq else None
        return True, "No count words found", None, nq.bbox if nq else None

    elif pred_name == "no_qualifier_words":
        nq = declarations.net_quantity
        if not nq or not nq.qualifier_words:
            return True, "No qualifier words found", None, nq.bbox if nq else None
        q_str = ", ".join(nq.qualifier_words)
        return False, f"Qualifier word(s) '{q_str}' prohibited in net quantity", q_str, nq.bbox

    elif pred_name == "approx_equal":
        mrp = declarations.mrp
        nq = declarations.net_quantity
        usp = declarations.unit_sale_price
        if not usp or usp.value is None:
            return False, "Unit sale price missing", None, None
        if not mrp or mrp.value is None or not nq or nq.value is None:
            return False, "MRP or Net Quantity missing for USP calculation", None, None

        # Compute net qty in base units (g, ml, cm, m, N, U)
        val = nq.value
        unit = (nq.unit or "").lower()
        if unit in ["kg", "l"]:
            base_qty = val * 1000.0
        else:
            base_qty = val

        if base_qty <= 0:
            return False, "Net quantity must be > 0 for USP", None, None

        expected_usp = mrp.value / (base_qty / (usp.per_qty if usp.per_qty > 0 else 1.0))
        actual_usp = usp.value
        if actual_usp is None:
            return False, "USP value missing", None, usp.bbox

        tol = max(0.01, 0.01 * expected_usp)
        diff = abs(actual_usp - expected_usp)
        ok = diff <= tol
        msg = (
            f"USP ₹{actual_usp:.2f} matches expected ₹{expected_usp:.2f}"
            if ok
            else f"USP ₹{actual_usp:.2f} mismatch; expected ₹{expected_usp:.2f} (diff ₹{diff:.2f})"
        )
        return ok, msg, f"₹{actual_usp:.2f}", usp.bbox

    elif pred_name == "script_in":
        allowed = params.get("scripts", ["latin", "devanagari"])
        detected = declarations.scripts_detected or []
        ok = any(s in detected for s in allowed)
        msg = f"Script detected in {allowed}" if ok else f"No script in {allowed} detected ({detected})"
        return ok, msg, ", ".join(detected), None

    elif pred_name == "phone":
        cc = declarations.consumer_care
        if cc and cc.phone:
            return True, f"Phone '{cc.phone}' present", cc.phone, cc.bbox
        return False, "Consumer care phone number missing", None, cc.bbox if cc else None

    elif pred_name == "email":
        cc = declarations.consumer_care
        if cc and cc.email:
            return True, f"Email '{cc.email}' present", cc.email, cc.bbox
        return False, "Consumer care email address missing", None, cc.bbox if cc else None

    elif pred_name == "pin":
        target = params.get("block", "first_entity")
        block = None
        if target == "first_entity":
            for b in [declarations.manufacturer, declarations.packer, declarations.importer, declarations.marketer]:
                if b is not None:
                    block = b
                    break
        elif hasattr(declarations, target):
            block = getattr(declarations, target)

        if not block:
            return False, "Entity block missing", None, None

        if block.pin and len(block.pin) == 6:
            return True, f"PIN '{block.pin}' present", block.pin, block.bbox

        return False, f"6-digit PIN missing in {block.role or 'entity'} block", block.value, block.bbox

    elif pred_name == "confidence_below":
        thresh = float(params.get("threshold", 0.75))
        if extracted_val is None:
            return False, "Field missing", None, bbox
        conf = float(extracted_val)
        ok = conf < thresh
        msg = f"Confidence {conf:.2f} is below threshold {thresh:.2f}" if ok else f"Confidence {conf:.2f} >= {thresh:.2f}"
        return ok, msg, conf, bbox

    return False, f"Unknown predicate '{pred_name}'", None, None
