import re
from typing import Any, Dict, List, Optional, Tuple
from rapidfuzz import fuzz

from nirikshan.lexicon import FIELD_LEXICON
from nirikshan.normalize import (
    INDIAN_STATES,
    detect_line_script,
    fix_numeric_confusions,
    normalize_currency,
    parse_unit_token,
    squash,
)
from nirikshan.schema import (
    MRP,
    ConsumerCare,
    DateField,
    Declarations,
    EntityBlock,
    FieldModel,
    NetQuantity,
    OCRLine,
    UnitSalePrice,
)

QUALIFIER_WORDS = [
    "approximate",
    "approximately",
    "approx",
    "about",
    "minimum",
    "min",
    "not less than",
    "average",
    "avg",
]

MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12
}


def union_bboxes(bboxes: List[List[List[float]]]) -> List[List[float]]:
    if not bboxes:
        return [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    min_x = min(pt[0] for bbox in bboxes for pt in bbox)
    min_y = min(pt[1] for bbox in bboxes for pt in bbox)
    max_x = max(pt[0] for bbox in bboxes for pt in bbox)
    max_y = max(pt[1] for bbox in bboxes for pt in bbox)
    return [[min_x, min_y], [max_x, min_y], [max_x, max_y], [min_x, max_y]]


def match_field_key(text: str) -> Optional[Tuple[str, str]]:
    """Returns (field_name, matched_key) if text matches a key in FIELD_LEXICON."""
    sq_text = squash(text)
    if not sq_text:
        return None

    # Collect all (field_name, key) pairs and sort by length of squash(key) descending
    all_keys = []
    for field_name, keys in FIELD_LEXICON.items():
        for key in keys:
            all_keys.append((field_name, key, squash(key)))
    
    all_keys.sort(key=lambda x: len(x[2]), reverse=True)

    # Exact squash prefix/substring match first
    for field_name, key, sq_key in all_keys:
        if sq_text.startswith(sq_key) or sq_key in sq_text:
            return field_name, key

    # Fuzzy match fallback (partial_ratio >= 88)
    best_match = None
    best_score = 0
    for field_name, key, sq_key in all_keys:
        score = fuzz.partial_ratio(sq_key, sq_text)
        if score >= 88 and score > best_score:
            best_score = score
            best_match = (field_name, key)

    return best_match


def resolve_value_lines(
    lines: List[OCRLine], key_idx: int, field_name: str
) -> Tuple[str, List[OCRLine], str]:
    key_line = lines[key_idx]
    k_text = key_line.text
    k_bbox = key_line.bbox
    k_height = max(1.0, max(pt[1] for pt in k_bbox) - min(pt[1] for pt in k_bbox))
    k_yc = sum(pt[1] for pt in k_bbox) / 4.0
    k_xmin = min(pt[0] for pt in k_bbox)
    k_xmax = max(pt[0] for pt in k_bbox)

    # Strategy (a): Same line after key or separator (:, -, etc.)
    matched = match_field_key(k_text)
    matched_key_text = matched[1] if matched else ""
    sq_key = squash(matched_key_text)

    # Find position in original text
    sep_idx = k_text.find(":")
    if sep_idx != -1 and sep_idx < len(k_text) - 1:
        after_sep = k_text[sep_idx + 1 :].strip()
        if after_sep:
            return after_sep, [key_line], "same_line"

    # Try removing matching key portion
    if matched_key_text:
        # Case insensitive replacement
        pattern = re.escape(matched_key_text)
        after_key = re.sub(pattern, "", k_text, flags=re.IGNORECASE).strip(" :-_.")
        if after_key and len(after_key) > 0:
            return after_key, [key_line], "same_line"

    # Strategy (b): Line directly below (horizontal overlap >= 40%, vertical gap < 1.5x height, max 2 lines away)
    for next_idx in range(key_idx + 1, min(len(lines), key_idx + 3)):
        cand = lines[next_idx]
        c_bbox = cand.bbox
        c_ymin = min(pt[1] for pt in c_bbox)
        k_ymax = max(pt[1] for pt in k_bbox)
        gap_y = c_ymin - k_ymax

        c_xmin = min(pt[0] for pt in c_bbox)
        c_xmax = max(pt[0] for pt in c_bbox)

        overlap = max(0.0, min(k_xmax, c_xmax) - max(k_xmin, c_xmin))
        w_k = max(1.0, k_xmax - k_xmin)
        horiz_overlap_ratio = overlap / w_k

        if gap_y < 1.5 * k_height and horiz_overlap_ratio >= 0.40:
            return cand.text.strip(), [cand], "below"

    # Strategy (c): Line to the right on the same baseline
    for cand in lines:
        if cand.id == key_line.id:
            continue
        c_bbox = cand.bbox
        c_yc = sum(pt[1] for pt in c_bbox) / 4.0
        c_xmin = min(pt[0] for pt in c_bbox)

        if abs(c_yc - k_yc) <= 0.5 * k_height and c_xmin >= k_xmin:
            return cand.text.strip(), [cand], "right"

    return k_text.strip(), [key_line], "same_line"


def absorb_block_lines(
    lines: List[OCRLine], key_idx: int
) -> Tuple[List[OCRLine], str]:
    absorbed = [lines[key_idx]]
    k_line = lines[key_idx]
    last_ymax = max(pt[1] for pt in k_line.bbox)
    line_h = max(1.0, last_ymax - min(pt[1] for pt in k_line.bbox))

    for idx in range(key_idx + 1, len(lines)):
        cand = lines[idx]
        # Stop if cand matches a key for another field
        match = match_field_key(cand.text)
        if match:
            break

        cand_ymin = min(pt[1] for pt in cand.bbox)
        cand_ymax = max(pt[1] for pt in cand.bbox)
        gap_y = cand_ymin - last_ymax

        if gap_y <= 1.5 * line_h:
            absorbed.append(cand)
            last_ymax = cand_ymax
        else:
            break

    block_text = "\n".join(l.text for l in absorbed)
    return absorbed, block_text


def parse_net_quantity(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)
    
    # Check qualifier words
    qualifiers_found = []
    text_lower = text.lower()
    for qw in QUALIFIER_WORDS:
        if qw in text_lower:
            qualifiers_found.append(qw)

    # 1. Check "N x 50 g" or "N x 50g" or "N Units x 50g"
    nx_match = re.search(
        r'(\d+)\s*(?:x|X|units?|pcs?|pieces?)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+|[\u0900-\u097F]+)',
        text,
        re.IGNORECASE
    )
    if nx_match:
        try:
            count_val = int(nx_match.group(1))
            val_num = float(nx_match.group(2))
            unit_str = nx_match.group(3)
            std_u, raw_u, nonstd = parse_unit_token(unit_str)
            return {
                "value": val_num,
                "unit": std_u,
                "raw_unit": raw_u,
                "unit_nonstandard": nonstd,
                "count": count_val,
                "qualifier_words": qualifiers_found,
            }
        except ValueError:
            pass

    # 2. Check "Pack of N" e.g. "Pack of 10 (20 g each)" or "Pack of 6"
    count_val = None
    packof_match = re.search(r'pack\s+of\s+(\d+)', text, re.IGNORECASE)
    if packof_match:
        try:
            count_val = int(packof_match.group(1))
        except ValueError:
            pass

    # 3. Match numeric value and unit token e.g. "500 g", "1.5 kg", "200 gms", "100 ml"
    val_num = None
    std_unit = None
    raw_unit = None
    unit_nonstd = False

    # Regex for float + unit e.g. "20 g"
    m = re.search(
        r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+|[\u0900-\u097F]+)', text
    )
    if m:
        try:
            val_num = float(m.group(1))
            unit_str = m.group(2)
            std_u, raw_u, nonstd = parse_unit_token(unit_str)
            std_unit = std_u
            raw_unit = raw_u
            unit_nonstd = nonstd
        except ValueError:
            pass

    return {
        "value": val_num,
        "unit": std_unit,
        "raw_unit": raw_unit,
        "unit_nonstandard": unit_nonstd,
        "count": count_val,
        "qualifier_words": qualifiers_found,
    }


def clean_matched_key_from_line(line_text: str, matched_key: str) -> str:
    if not matched_key:
        return line_text.strip()
    pattern = r'^\s*' + re.escape(matched_key) + r'[\s\:\_\-\.]*'
    cleaned = re.sub(pattern, "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    if not cleaned or cleaned.lower() == line_text.lower():
        cleaned = re.sub(re.escape(matched_key), "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    return cleaned


def parse_mrp(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)
    currency, _ = normalize_currency(text)

    # Check inclusive of all taxes phrase (tolerates OCR confusion on first letter)
    tax_pattern = r'[il1|]ncl(usive|\.)?\s*(of\s*)?all\s*tax(es)?'
    has_tax_phrase = bool(re.search(tax_pattern, text, re.IGNORECASE))

    # Extract MRP float value
    val_num = None
    paise_num = None

    # Match currency + amount e.g. "Rs 45.00", "₹ 150", "45.50"
    m = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)', text, re.IGNORECASE)
    if m:
        try:
            val_num = float(m.group(1))
            if "." in m.group(1):
                paise_str = m.group(1).split(".")[1]
                if len(paise_str) == 1:
                    paise_str += "0"
                paise_num = int(paise_str[:2])
            else:
                paise_num = 0
        except ValueError:
            pass

    return {
        "value": val_num,
        "currency": currency,
        "incl_taxes_phrase": has_tax_phrase,
        "paise": paise_num,
    }


def parse_unit_sale_price(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)

    val_num = None
    per_qty = 1.0
    per_u = None
    val_per_base = None

    m = re.search(
        r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:/|per)\s*(\d+(?:\.\d+)?)?\s*([a-zA-Z]+|[\u0900-\u097F]+)',
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            val_num = float(m.group(1))
            if m.group(2):
                per_qty = float(m.group(2))
            else:
                per_qty = 1.0
            unit_str = m.group(3)
            std_u, _, _ = parse_unit_token(unit_str)
            per_u = std_u
            if per_qty > 0:
                val_per_base = round(val_num / per_qty, 4)
        except ValueError:
            pass
    else:
        m2 = re.search(r'(\d+(?:\.\d+)?)', text)
        if m2:
            try:
                val_num = float(m2.group(1))
                val_per_base = val_num
            except ValueError:
                pass

    return {
        "value": val_num,
        "per_qty": per_qty,
        "per_unit": per_u,
        "value_per_base_unit": val_per_base,
    }


def parse_date(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)

    day_val = None
    month_val = None
    year_val = None

    # Check relative date forms e.g. "6 months from packaging", "30 days", "1 year"
    m_mon = re.search(r'\b(\d+)\s*months?\b', text, re.IGNORECASE)
    if m_mon:
        return {"day": None, "month": None, "year": None, "duration_months": int(m_mon.group(1))}

    m_yr = re.search(r'\b(\d+)\s*years?\b', text, re.IGNORECASE)
    if m_yr:
        return {"day": None, "month": None, "year": None, "duration_months": int(m_yr.group(1)) * 12}

    m_day = re.search(r'\b(\d+)\s*days?\b', text, re.IGNORECASE)
    if m_day:
        return {"day": None, "month": None, "year": None, "duration_months": round(int(m_day.group(1)) / 30)}

    # 1. DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY
    m1 = re.search(r'\b(\d{1,2})[\/\.\-](\d{1,2})[\/\.\-](\d{2,4})\b', text)
    if m1:
        day_val = int(m1.group(1))
        month_val = int(m1.group(2))
        y = int(m1.group(3))
        year_val = y + 2000 if y < 100 else y
        return {"day": day_val, "month": month_val, "year": year_val, "duration_months": None}

    # 2. MM/YYYY or MM-YYYY or MM.YYYY
    m2 = re.search(r'\b(\d{1,2})[\/\.\-](\d{2,4})\b', text)
    if m2:
        month_val = int(m2.group(1))
        y = int(m2.group(2))
        year_val = y + 2000 if y < 100 else y
        return {"day": None, "month": month_val, "year": year_val, "duration_months": None}

    # 3. Mon YYYY e.g. Sep 2026 or September 2026
    m3 = re.search(r'\b([a-zA-Z]{3,9})\s*[\/\.\-,\s]\s*(\d{2,4})\b', text)
    if m3:
        mon_str = m3.group(1).lower()
        if mon_str in MONTH_NAMES:
            month_val = MONTH_NAMES[mon_str]
            y = int(m3.group(2))
            year_val = y + 2000 if y < 100 else y
            return {"day": None, "month": month_val, "year": year_val, "duration_months": None}

    return {"day": day_val, "month": month_val, "year": year_val, "duration_months": None}


def parse_entity_block(
    lines: List[OCRLine], role_name: str, matched_key: str = ""
) -> EntityBlock:
    source_lines = lines
    raw_text = "\n".join(l.text for l in source_lines)
    conf = min(l.confidence for l in source_lines) if source_lines else 0.0
    bbox = union_bboxes([l.bbox for l in source_lines])
    line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]

    # Extract PIN (6 digits)
    pin_match = re.search(r'\b[1-9][0-9]{5}\b', raw_text)
    pin_val = pin_match.group(0) if pin_match else None

    # Extract State
    state_val = None
    raw_upper = raw_text.upper()
    for st in INDIAN_STATES:
        if st in raw_upper:
            state_val = st
            break

    name_val = None
    addr_lines = []

    if source_lines:
        first_rem = clean_matched_key_from_line(source_lines[0].text, matched_key)
        if first_rem:
            name_val = first_rem
            addr_lines = [l.text.strip() for l in source_lines[1:] if l.text.strip()]
        else:
            if len(source_lines) > 1:
                name_val = source_lines[1].text.strip()
                addr_lines = [l.text.strip() for l in source_lines[2:] if l.text.strip()]
            else:
                name_val = None
                addr_lines = []

    address_val = ", ".join(addr_lines) if addr_lines else None

    return EntityBlock(
        value=raw_text.strip(),
        raw=raw_text.strip(),
        bbox=bbox,
        confidence=round(float(conf), 4),
        source_line_ids=line_ids,
        source="block_absorbed",
        name=name_val,
        address=address_val,
        pin=pin_val,
        state=state_val,
        role=role_name,
    )


def parse_consumer_care_block(
    lines: List[OCRLine], matched_key: str = ""
) -> ConsumerCare:
    source_lines = lines
    raw_text = "\n".join(l.text for l in source_lines)
    conf = min(l.confidence for l in source_lines) if source_lines else 0.0
    bbox = union_bboxes([l.bbox for l in source_lines])
    line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]

    # Extract Email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', raw_text)
    email_val = email_match.group(0) if email_match else None

    # Extract Phone (10 digits or 1800/1860)
    phone_match = re.search(
        r'\b(?:1800|1860)[- ]?\d{3,4}[- ]?\d{3,4}\b|\b[6-9]\d{9}\b|\b0\d{2,4}[- ]?\d{6,8}\b',
        raw_text,
    )
    phone_val = phone_match.group(0) if phone_match else None

    def clean_contact_info(text: str) -> str:
        res = text
        if email_val:
            res = res.replace(email_val, "")
        if phone_val:
            res = res.replace(phone_val, "")
        res = re.sub(r'\b(?:phone|email|tel|mobile|contact)[\s\:\.]*', '', res, flags=re.IGNORECASE)
        return res.strip(" :-_,.")

    name_val = None
    addr_lines = []

    if source_lines:
        first_rem = clean_matched_key_from_line(source_lines[0].text, matched_key)
        first_rem_cleaned = clean_contact_info(first_rem)
        if first_rem_cleaned:
            name_val = first_rem_cleaned
            addr_lines = [clean_contact_info(l.text) for l in source_lines[1:]]
        else:
            if len(source_lines) > 1:
                cand_name = clean_contact_info(source_lines[1].text)
                name_val = cand_name if cand_name else None
                addr_lines = [clean_contact_info(l.text) for l in source_lines[2:]]
            else:
                name_val = None
                addr_lines = []

    non_empty_addr = [a for a in addr_lines if a]
    address_val = ", ".join(non_empty_addr) if non_empty_addr else None

    return ConsumerCare(
        value=raw_text.strip(),
        raw=raw_text.strip(),
        bbox=bbox,
        confidence=round(float(conf), 4),
        source_line_ids=line_ids,
        source="block_absorbed",
        name=name_val,
        address=address_val,
        phone=phone_val,
        email=email_val,
    )


def extract_generic_name(
    lines: List[OCRLine], claimed_line_ids: set
) -> Optional[FieldModel]:
    # Heuristic: longest line near top (first 5 lines) that is not an ALL-CAPS single brand token and not a key line
    candidates = []
    for idx, line in enumerate(lines[:5]):
        if line.id in claimed_line_ids:
            continue
        text = line.text.strip()
        words = text.split()
        if len(words) == 1 and text.isupper():
            continue  # Likely brand name
        if len(text) >= 3:
            candidates.append((len(text), line))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_line = candidates[0][1]
        line_id = best_line.id if best_line.id is not None else 0
        return FieldModel(
            value=best_line.text.strip(),
            raw=best_line.text.strip(),
            bbox=best_line.bbox,
            confidence=round(float(best_line.confidence * 0.6), 4),  # Mark confidence lower as heuristic
            source_line_ids=[line_id],
            source="top_header_heuristic",
        )
    return None


def extract(
    lines_raw: List[Dict[str, Any]], image_w: int = 1600, image_h: int = 1200
) -> Declarations:
    # Convert dict lines to OCRLine objects if needed
    lines: List[OCRLine] = []
    for idx, item in enumerate(lines_raw):
        if isinstance(item, OCRLine):
            line_obj = item
            if line_obj.id is None:
                line_obj.id = idx
            lines.append(line_obj)
        else:
            line_obj = OCRLine(
                id=item.get("id", idx),
                text=item["text"],
                confidence=float(item["confidence"]),
                bbox=item["bbox"],
            )
            lines.append(line_obj)

    # Detect scripts
    scripts = list(set(detect_line_script(l.text) for l in lines))

    claimed_line_ids = set()

    extracted_dict: Dict[str, Any] = {}

    for idx, line in enumerate(lines):
        match = match_field_key(line.text)
        if not match:
            continue

        field_name, matched_key = match
        if field_name in extracted_dict:
            continue  # Already extracted first occurrence

        # Entity / ConsumerCare blocks
        if field_name in ["manufacturer", "packer", "importer", "marketer"]:
            absorbed, block_text = absorb_block_lines(lines, idx)
            for l in absorbed:
                if l.id is not None:
                    claimed_line_ids.add(l.id)
            extracted_dict[field_name] = parse_entity_block(absorbed, field_name, matched_key)
            continue

        if field_name == "consumer_care":
            absorbed, block_text = absorb_block_lines(lines, idx)
            for l in absorbed:
                if l.id is not None:
                    claimed_line_ids.add(l.id)
            extracted_dict["consumer_care"] = parse_consumer_care_block(absorbed, matched_key)
            continue

        # Single value fields
        raw_val_str, source_lines, strategy = resolve_value_lines(lines, idx, field_name)
        for l in source_lines:
            if l.id is not None:
                claimed_line_ids.add(l.id)

        conf = min(l.confidence for l in source_lines) if source_lines else 0.0
        bbox = union_bboxes([l.bbox for l in source_lines])
        line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]

        if field_name == "net_quantity":
            parsed = parse_net_quantity(raw_val_str)
            extracted_dict["net_quantity"] = NetQuantity(
                value=parsed["value"],
                unit=parsed["unit"],
                raw_unit=parsed["raw_unit"],
                unit_nonstandard=parsed["unit_nonstandard"],
                count=parsed["count"],
                qualifier_words=parsed["qualifier_words"],
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )
        elif field_name == "mrp":
            parsed = parse_mrp(raw_val_str)
            extracted_dict["mrp"] = MRP(
                value=parsed["value"],
                currency=parsed["currency"],
                incl_taxes_phrase=parsed["incl_taxes_phrase"],
                paise=parsed["paise"],
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )
        elif field_name == "unit_sale_price":
            parsed = parse_unit_sale_price(raw_val_str)
            extracted_dict["unit_sale_price"] = UnitSalePrice(
                value=parsed["value"],
                per_qty=parsed["per_qty"],
                per_unit=parsed["per_unit"],
                value_per_base_unit=parsed["value_per_base_unit"],
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )
        elif field_name in ["mfg_date", "best_before"]:
            parsed = parse_date(raw_val_str)
            extracted_dict[field_name] = DateField(
                day=parsed["day"],
                month=parsed["month"],
                year=parsed["year"],
                duration_months=parsed["duration_months"],
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )
        elif field_name == "country_of_origin":
            clean_country = raw_val_str.replace("Country of Origin", "").replace("Made in", "").strip(" :-_.")
            extracted_dict["country_of_origin"] = FieldModel(
                value=clean_country if clean_country else raw_val_str,
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )

    # Generic name heuristic if missing
    if "generic_name" not in extracted_dict:
        gen_field = extract_generic_name(lines, claimed_line_ids)
        if gen_field:
            extracted_dict["generic_name"] = gen_field

    return Declarations(
        manufacturer=extracted_dict.get("manufacturer"),
        packer=extracted_dict.get("packer"),
        importer=extracted_dict.get("importer"),
        marketer=extracted_dict.get("marketer"),
        country_of_origin=extracted_dict.get("country_of_origin"),
        generic_name=extracted_dict.get("generic_name"),
        net_quantity=extracted_dict.get("net_quantity"),
        mrp=extracted_dict.get("mrp"),
        unit_sale_price=extracted_dict.get("unit_sale_price"),
        mfg_date=extracted_dict.get("mfg_date"),
        best_before=extracted_dict.get("best_before"),
        consumer_care=extracted_dict.get("consumer_care"),
        scripts_detected=scripts,
    )
