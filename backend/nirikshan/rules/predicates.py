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
    pred_name: str,
    params: Dict[str, Any],
    declarations: Declarations,
    quality: Optional[Dict[str, Any]] = None,
    conflicts: Optional[List[Any]] = None,
) -> Tuple[bool, Optional[str], Any, Optional[List[List[float]]], List[Dict[str, Any]]]:
    """Evaluates a named predicate against Declarations.
    Returns (is_success, detail_message, extracted_val, evidence_bbox, evidence_refs).
    """
    field_path = params.get("field", "")
    extracted_val = get_field_value(declarations, field_path) if field_path else None
    
    # Get bbox for evidence if available
    bbox = None
    evidence_refs: List[Dict[str, Any]] = []
    base_obj = None
    if field_path:
        base_obj_path = field_path.rsplit(".", 1)[0] if "." in field_path else field_path
        base_obj = get_field_value(declarations, base_obj_path)
        if hasattr(base_obj, "bbox"):
            bbox = getattr(base_obj, "bbox")
    if bbox is None and field_path == "country_of_origin.value" and declarations.importer and hasattr(declarations.importer, "bbox"):
        bbox = declarations.importer.bbox
        base_obj = declarations.importer

    if bbox is not None and base_obj is not None:
        sid = getattr(base_obj, "surface_id", None)
        if sid is not None:
            evidence_refs = [{"surface_id": sid, "bbox": bbox}]

    if pred_name == "no_surface_conflict":
        target_field = params.get("field", "")
        if not conflicts:
            return True, f"No cross-surface conflict for {target_field}", None, None, []
        
        matching = []
        for c in conflicts:
            c_field = getattr(c, "field", None) if hasattr(c, "field") else (c.get("field") if isinstance(c, dict) else None)
            if c_field == target_field or (target_field == "mfg_date" and c_field in ["mfg_date", "best_before"]):
                matching.append(c)

        if not matching:
            return True, f"No cross-surface conflict for {target_field}", None, None, []

        conflict = matching[0]
        c_surfaces = getattr(conflict, "surfaces", []) if hasattr(conflict, "surfaces") else (conflict.get("surfaces", []) if isinstance(conflict, dict) else [])
        c_refs = []
        extracted_vals = []
        first_bbox = None
        for s in c_surfaces:
            sid = getattr(s, "id", None) if hasattr(s, "id") else (s.get("id") if isinstance(s, dict) else None)
            sval = getattr(s, "value", None) if hasattr(s, "value") else (s.get("value") if isinstance(s, dict) else None)
            sbox = getattr(s, "bbox", None) if hasattr(s, "bbox") else (s.get("bbox") if isinstance(s, dict) else None)
            c_refs.append({"surface_id": sid, "bbox": sbox})
            extracted_vals.append(f"Surface {sid}: {sval}")
            if first_bbox is None and sbox:
                first_bbox = sbox

        ext_str = "; ".join(extracted_vals)
        return False, f"Conflict detected across surfaces for {target_field}: {ext_str}", ext_str, first_bbox, c_refs

    elif pred_name == "present":
        ok = extracted_val is not None and str(extracted_val).strip() != ""
        msg = f"Value '{extracted_val}' present" if ok else f"Field {field_path} is missing or empty"
        return ok, msg, extracted_val, bbox, evidence_refs

    elif pred_name == "declared_elsewhere":
        base_obj_path = field_path.rsplit(".", 1)[0] if (field_path and "." in field_path) else field_path
        base_obj = get_field_value(declarations, base_obj_path) if base_obj_path else None
        de = getattr(base_obj, "declared_elsewhere", None) if base_obj else None
        ok = de is not None and str(de).strip() != ""
        msg = f"Field {field_path or base_obj_path} declared elsewhere on {de}" if ok else f"Field {field_path or base_obj_path} not declared elsewhere"
        return ok, msg, de, bbox, evidence_refs

    elif pred_name == "field_source_is":
        target_source = params.get("source", "")
        base_obj_path = field_path.rsplit(".", 1)[0] if (field_path and "." in field_path) else field_path
        base_obj = get_field_value(declarations, base_obj_path) if base_obj_path else None
        src = getattr(base_obj, "source", None) if base_obj else None
        ok = src == target_source
        msg = f"Field {field_path or base_obj_path} source is '{src}'" if ok else f"Field {field_path or base_obj_path} source is not '{target_source}'"
        return ok, msg, src, bbox, evidence_refs

    elif pred_name == "absent":
        ok = extracted_val is None or str(extracted_val).strip() == ""
        msg = f"Field {field_path} is absent" if ok else f"Field {field_path} is present"
        return ok, msg, extracted_val, bbox, evidence_refs

    elif pred_name == "regex":
        pattern = params.get("pattern", "")
        if extracted_val is None:
            return False, f"Field {field_path} is missing", None, bbox, evidence_refs
        matched = bool(re.search(pattern, str(extracted_val), re.IGNORECASE))
        msg = f"Pattern '{pattern}' matched" if matched else f"Pattern '{pattern}' not matched in '{extracted_val}'"
        return matched, msg, extracted_val, bbox, evidence_refs

    elif pred_name == "unit_standard":
        nq = declarations.net_quantity
        if not nq or not nq.unit:
            return False, "Net quantity or unit missing", None, None, []
        ok = not nq.unit_nonstandard
        msg = f"Unit '{nq.raw_unit or nq.unit}' is standard" if ok else f"Unit '{nq.raw_unit or nq.unit}' is non-standard"
        return ok, msg, nq.raw_unit or nq.unit, nq.bbox, [{"surface_id": nq.surface_id, "bbox": nq.bbox}] if nq.surface_id is not None and nq.bbox else []

    elif pred_name == "magnitude_unit_consistent":
        nq = declarations.net_quantity
        if not nq or nq.value is None or not nq.unit:
            return False, "Net quantity value or unit missing", None, None, []
        val = nq.value
        u = str(nq.unit).lower()
        nq_refs = [{"surface_id": nq.surface_id, "bbox": nq.bbox}] if nq.surface_id is not None and nq.bbox else []
        if u in ["g", "ml"] and val >= 1000.0:
            return False, f"{val} {u} should be expressed as {val/1000.0:.2f} {'kg' if u=='g' else 'L'}", f"{val} {u}", nq.bbox, nq_refs
        if u in ["kg", "l"] and val < 1.0:
            return False, f"{val} {u} should be expressed as {val*1000.0:.0f} {'g' if u=='kg' else 'ml'}", f"{val} {u}", nq.bbox, nq_refs
        return True, f"{val} {u} magnitude and unit consistent", f"{val} {u}", nq.bbox, nq_refs

    elif pred_name == "no_count_words":
        nq = declarations.net_quantity
        raw_text = (nq.raw if nq and nq.raw else "").lower()
        nq_refs = [{"surface_id": nq.surface_id, "bbox": nq.bbox}] if nq and nq.surface_id is not None and nq.bbox else []
        for cw in COUNT_WORDS:
            if cw in raw_text:
                return False, f"Count word '{cw}' prohibited in net quantity declaration", cw, nq.bbox if nq else None, nq_refs
        return True, "No count words found", None, nq.bbox if nq else None, nq_refs

    elif pred_name == "no_qualifier_words":
        nq = declarations.net_quantity
        nq_refs = [{"surface_id": nq.surface_id, "bbox": nq.bbox}] if nq and nq.surface_id is not None and nq.bbox else []
        if not nq or not nq.qualifier_words:
            return True, "No qualifier words found", None, nq.bbox if nq else None, nq_refs
        q_str = ", ".join(nq.qualifier_words)
        return False, f"Qualifier word(s) '{q_str}' prohibited in net quantity", q_str, nq.bbox, nq_refs

    elif pred_name == "approx_equal":
        mrp = declarations.mrp
        nq = declarations.net_quantity
        usp = declarations.unit_sale_price
        usp_refs = [{"surface_id": usp.surface_id, "bbox": usp.bbox}] if usp and usp.surface_id is not None and usp.bbox else []
        if not usp or usp.value is None:
            return False, "Unit sale price missing", None, None, []
        if not mrp or mrp.value is None or not nq or nq.value is None:
            return False, "MRP or Net Quantity missing for USP calculation", None, None, []

        # Compute net qty in base units (g, ml, cm, m, N, U)
        val = nq.value
        unit = (nq.unit or "").lower()
        if unit in ["kg", "l"]:
            base_qty = val * 1000.0
        else:
            base_qty = val

        if base_qty <= 0:
            return False, "Net quantity must be > 0 for USP", None, None, []

        expected_usp = mrp.value / (base_qty / (usp.per_qty if usp.per_qty > 0 else 1.0))
        actual_usp = usp.value
        if actual_usp is None:
            return False, "USP value missing", None, usp.bbox, usp_refs

        tol = max(0.01, 0.01 * expected_usp)
        diff = abs(actual_usp - expected_usp)
        ok = diff <= tol
        msg = (
            f"USP ₹{actual_usp:.2f} matches expected ₹{expected_usp:.2f}"
            if ok
            else f"USP ₹{actual_usp:.2f} mismatch; expected ₹{expected_usp:.2f} (diff ₹{diff:.2f})"
        )
        return ok, msg, f"₹{actual_usp:.2f}", usp.bbox, usp_refs

    elif pred_name == "script_in":
        allowed = params.get("scripts", ["latin", "devanagari"])
        detected = declarations.scripts_detected or []
        ok = any(s in detected for s in allowed)
        msg = f"Script detected in {allowed}" if ok else f"No script in {allowed} detected ({detected})"
        return ok, msg, ", ".join(detected), None, []

    elif pred_name == "phone":
        cc = declarations.consumer_care
        cc_refs = [{"surface_id": cc.surface_id, "bbox": cc.bbox}] if cc and cc.surface_id is not None and cc.bbox else []
        if cc and cc.phone:
            return True, f"Phone '{cc.phone}' present", cc.phone, cc.bbox, cc_refs
        return False, "Consumer care phone number missing", None, cc.bbox if cc else None, cc_refs

    elif pred_name == "email":
        cc = declarations.consumer_care
        cc_refs = [{"surface_id": cc.surface_id, "bbox": cc.bbox}] if cc and cc.surface_id is not None and cc.bbox else []
        if cc and cc.email:
            return True, f"Email '{cc.email}' present", cc.email, cc.bbox, cc_refs
        return False, "Consumer care email address missing", None, cc.bbox if cc else None, cc_refs

    elif pred_name == "pin":
        target = params.get("block", "first_entity")
        block = None
        if target == "first_entity":
            block = declarations.primary_entity
        elif hasattr(declarations, target):
            block = getattr(declarations, target)

        if not block:
            return False, "Entity block missing", None, None, []

        b_refs = [{"surface_id": block.surface_id, "bbox": block.bbox}] if block.surface_id is not None and block.bbox else []
        if block.pin and len(block.pin) == 6:
            return True, f"PIN '{block.pin}' present", block.pin, block.bbox, b_refs

        return False, f"6-digit PIN missing in {block.role or 'entity'} block", block.value, block.bbox, b_refs

    elif pred_name == "confidence_below":
        thresh = float(params.get("threshold", 0.75))
        if extracted_val is None:
            return False, "Field missing", None, bbox, evidence_refs
        conf = float(extracted_val)
        ok = conf < thresh
        msg = f"Confidence {conf:.2f} is below threshold {thresh:.2f}" if ok else f"Confidence {conf:.2f} >= {thresh:.2f}"
        return ok, msg, conf, bbox, evidence_refs

    elif pred_name == "quality_warning_present":
        warnings = quality.get("warnings", []) if quality else []
        ok = len(warnings) > 0
        msg = f"Quality warnings present: {warnings}" if ok else "No quality warnings"
        return ok, msg, warnings, None, []

    elif pred_name == "key_confidence_below":
        thresh = float(params.get("threshold", 0.70))
        confs = []
        if declarations.net_quantity and declarations.net_quantity.confidence is not None:
            confs.append(float(declarations.net_quantity.confidence))
        if declarations.mrp and declarations.mrp.confidence is not None:
            confs.append(float(declarations.mrp.confidence))

        mean_conf = sum(confs) / len(confs) if confs else 0.0
        ok = mean_conf < thresh
        msg = f"Key fields mean confidence {mean_conf:.2f} is below threshold {thresh:.2f}" if ok else f"Key fields mean confidence {mean_conf:.2f} >= {thresh:.2f}"
        return ok, msg, mean_conf, declarations.net_quantity.bbox if declarations.net_quantity else None, []

    elif pred_name == "responsible_entity":
        pe = declarations.primary_entity
        if not pe or not (pe.name or pe.address or pe.value):
            return False, "No responsible entity declared", None, None, []

        role = pe.role or "manufacturer"
        name = pe.name or pe.value or "Responsible Entity"
        has_marketer = declarations.marketer is not None or (pe and pe.role == "marketer")

        msg_extra = " (marketer/brand-owner block present — deemed responsible)" if has_marketer else ""
        msg = f"Responsible entity: {name} ({role}){msg_extra}"
        pe_refs = [{"surface_id": pe.surface_id, "bbox": pe.bbox}] if pe.surface_id is not None and pe.bbox else []
        return True, msg, f"{name} ({role})", pe.bbox, pe_refs

    elif pred_name == "mrp_paise_valid":
        mrp = declarations.mrp
        if not mrp or mrp.value is None:
            return False, "MRP value missing", None, None, []
        paise = mrp.paise
        if paise is None:
            val = float(mrp.value)
            paise = round(round(val - int(val), 4) * 100)
        mrp_refs = [{"surface_id": mrp.surface_id, "bbox": mrp.bbox}] if mrp.surface_id is not None and mrp.bbox else []
        if paise in [0, 50]:
            return True, f"MRP paise .{paise:02d} is valid (.00 or .50)", f"₹{mrp.value:.2f}", mrp.bbox, mrp_refs
        return False, f"MRP paise .{paise:02d} is invalid (must be .00 or .50)", f"₹{mrp.value:.2f}", mrp.bbox, mrp_refs

    elif pred_name == "no_conflicting_mrp":
        candidates = declarations.mrp_candidates or []
        if not candidates:
            if declarations.mrp and declarations.mrp.value is not None:
                candidates = [declarations.mrp]
            else:
                return True, "No MRP candidates found to check for conflicts", None, None, []

        vals = list(set(round(float(c.value), 2) for c in candidates if c.value is not None))
        cand_bbox = candidates[0].bbox if candidates else None
        cand_refs = [{"surface_id": c.surface_id, "bbox": c.bbox} for c in candidates if c.surface_id is not None and c.bbox]
        if len(vals) <= 1:
            return True, f"Single or consistent MRP candidate value found: {vals}", vals, cand_bbox, cand_refs
        return False, f"Conflicting MRP values found: {vals}", vals, cand_bbox, cand_refs

    elif pred_name == "manual_checklist_check":
        return False, "Manual verification required by officer", None, None, []

    elif pred_name == "has_gtin":
        gtin = declarations.gtin
        gtin_refs = [{"surface_id": gtin.surface_id, "bbox": gtin.bbox}] if gtin and gtin.surface_id is not None and gtin.bbox else []
        if gtin and gtin.value:
            return True, f"GTIN/barcode detected: {gtin.value}", gtin.value, gtin.bbox, gtin_refs
        return False, "No GTIN/barcode detected", None, None, []

    elif pred_name == "has_dimension_or_sheet_count":
        dim_pattern = re.compile(r'\d+\s*(cm|m|mm)\s*[x×]\s*\d+', re.IGNORECASE)
        sheet_pattern = re.compile(r'\b\d+\s*(sheets?|pieces?|pcs|metres?|meters?)\b|\bsheet count\b|\bpiece count\b', re.IGNORECASE)

        text_to_check = declarations.all_text or ""
        if not text_to_check:
            fields_raw = []
            for f in [declarations.net_quantity, declarations.generic_name, declarations.mrp]:
                if f and hasattr(f, "raw") and f.raw:
                    fields_raw.append(f.raw)
            text_to_check = "\n".join(fields_raw)

        nq = declarations.net_quantity
        nq_refs = [{"surface_id": nq.surface_id, "bbox": nq.bbox}] if nq and nq.surface_id is not None and nq.bbox else []

        m_dim = dim_pattern.search(text_to_check)
        if m_dim:
            return True, f"Dimension declaration found: '{m_dim.group(0)}'", m_dim.group(0), nq.bbox if nq else None, nq_refs

        m_sheet = sheet_pattern.search(text_to_check)
        if m_sheet:
            return True, f"Count declaration found: '{m_sheet.group(0)}'", m_sheet.group(0), nq.bbox if nq else None, nq_refs

        return False, "Dimensions/count declaration required — verify", None, None, []

    return False, f"Unknown predicate '{pred_name}'", None, None, []

