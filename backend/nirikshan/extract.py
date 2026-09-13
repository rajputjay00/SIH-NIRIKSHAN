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


CRIMP_PATTERNS = [
    r'\bsee\s+crimp\b',
    r'\bon\s+crimp\b',
    r'\bat\s+crimp\b',
    r'\bstamped\s+on\s+crimp\b',
    r'\bcrimp\s+seal\b',
    r'\bsee\s+seal\b',
    r'\bon\s+seal\b',
    r'\btop\s+crimp\b',
    r'\bbottom\s+crimp\b',
    r'\bcrimp\b',
]


def is_crimp_text(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in CRIMP_PATTERNS)


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

    all_keys = []
    for field_name, keys in FIELD_LEXICON.items():
        for key in keys:
            all_keys.append((field_name, key, squash(key)))
    
    all_keys.sort(key=lambda x: len(x[2]), reverse=True)

    bad_care_prefixes = ["tooth", "gum", "dental", "skin", "hair", "oral", "body", "baby", "face", "sun", "foot", "hand", "health"]

    def is_rejected(field_name, text):
        if field_name == "consumer_care":
            text_lower = text.lower()
            for prefix in bad_care_prefixes:
                if f"{prefix} care" in text_lower or f"{prefix}care" in text_lower or f"{prefix} cell" in text_lower or f"{prefix}cell" in text_lower:
                    return True
        return False

    for field_name, key, sq_key in all_keys:
        if sq_text.startswith(sq_key) or sq_key in sq_text:
            if not is_rejected(field_name, text):
                return field_name, key

    best_match = None
    best_score = 0
    for field_name, key, sq_key in all_keys:
        score = fuzz.partial_ratio(sq_key, sq_text)
        if score >= 88 and score > best_score:
            if not is_rejected(field_name, text):
                best_score = score
                best_match = (field_name, key)

    return best_match


def has_valid_field_value(val_str: str, f_name: str) -> bool:
    if not val_str:
        return False
    if f_name in ["net_quantity", "mrp", "unit_sale_price", "mfg_date", "best_before"]:
        if not re.search(r'\d', val_str) and not any(m in val_str.lower() for m in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "crimp"]):
            return False
    return True


def strip_squashed_key(line_text: str, matched_key: str) -> str:
    """Strips matched_key from line_text using squash alignment to handle split keys like 'M RP', 'M.R.P'."""
    sq_key = squash(matched_key)
    if not sq_key:
        return line_text.strip()

    orig_indices = [i for i, ch in enumerate(line_text) if ch.isalnum()]
    sq_text = "".join(line_text[i] for i in orig_indices).lower()

    pos = sq_text.find(sq_key)
    if pos != -1:
        end_orig_idx = orig_indices[pos + len(sq_key) - 1]
        remainder = line_text[end_orig_idx + 1 :].strip(" :-_.")
        if remainder:
            return remainder

    return line_text.strip()


def is_disqualified_value_line(text: str) -> bool:
    """Returns True if candidate line should not be used as a value line for below/right strategies."""
    if not text:
        return True

    if match_field_key(text) is not None:
        return True

    if re.search(r'\b(?:1800|1860)(?:[- ]?\d){6,7}\b|\b[6-9]\d{9}\b|\b0\d{2,4}[- ]?\d{6,8}\b', text):
        return True

    if re.search(r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text):
        return True

    text_lower = text.lower()
    contact_keywords = ["phone", "tollfree", "toll free", "helpline", "email", "e-mail", "consumer care", "customercare", "address", "call", "fax", "tel:"]
    if any(kw in text_lower for kw in contact_keywords):
        return True

    return False


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

    sep_idx = k_text.find(":")
    if sep_idx != -1 and sep_idx < len(k_text) - 1:
        after_sep = k_text[sep_idx + 1 :].strip()
        if has_valid_field_value(after_sep, field_name):
            return after_sep, [key_line], "same_line"

    if matched_key_text:
        after_key = clean_matched_key_from_line(k_text, matched_key_text)
        if after_key and len(after_key) > 0 and after_key.lower() != k_text.lower():
            if has_valid_field_value(after_key, field_name):
                return after_key, [key_line], "same_line"

    # Strategy (c): Line to the right on the same baseline
    for cand in lines:
        if cand.id == key_line.id:
            continue
        if is_disqualified_value_line(cand.text):
            continue
        c_bbox = cand.bbox
        c_yc = sum(pt[1] for pt in c_bbox) / 4.0
        c_xmin = min(pt[0] for pt in c_bbox)

        if abs(c_yc - k_yc) <= 0.8 * k_height and c_xmin >= k_xmin:
            if has_valid_field_value(cand.text, field_name):
                return cand.text.strip(), [cand], "right"

    # Strategy (b): Line directly below
    for next_idx in range(key_idx + 1, min(len(lines), key_idx + 4)):
        cand = lines[next_idx]
        if is_disqualified_value_line(cand.text):
            continue
        c_bbox = cand.bbox
        c_ymin = min(pt[1] for pt in c_bbox)
        c_yc = sum(pt[1] for pt in c_bbox) / 4.0
        k_ymax = max(pt[1] for pt in k_bbox)
        gap_y = c_ymin - k_ymax

        if c_yc <= k_yc:
            continue

        c_xmin = min(pt[0] for pt in c_bbox)
        c_xmax = max(pt[0] for pt in c_bbox)

        w_k = max(1.0, k_xmax - k_xmin)
        w_c = max(1.0, c_xmax - c_xmin)
        w_narrower = min(w_k, w_c)

        overlap = max(0.0, min(k_xmax, c_xmax) - max(k_xmin, c_xmin))
        horiz_overlap_ratio = overlap / w_narrower
        left_in_range = (k_xmin - 10.0 <= c_xmin <= k_xmax + 10.0)

        if gap_y < 2.5 * k_height and (horiz_overlap_ratio >= 0.20 or left_in_range):
            if has_valid_field_value(cand.text, field_name):
                return cand.text.strip(), [cand], "below"

    return k_text.strip(), [key_line], "same_line"



def absorb_block_lines(
    lines: List[OCRLine], key_idx: int
) -> Tuple[List[OCRLine], str, str]:
    absorbed = [lines[key_idx]]
    k_line = lines[key_idx]
    last_ymax = max(pt[1] for pt in k_line.bbox)
    line_h = max(1.0, last_ymax - min(pt[1] for pt in k_line.bbox))
    stop_reason = "max_gap"
    prose_verbs = ["is", "are", "based", "contains", "read", "use", "keep", "apply", "store"]

    has_pin_in_key = bool(re.search(r'\b[1-9][0-9]{5}\b', k_line.text))
    if has_pin_in_key:
        return absorbed, k_line.text, "pin_found"

    for idx in range(key_idx + 1, min(len(lines), key_idx + 3)):
        cand = lines[idx]
        match = match_field_key(cand.text)
        if match:
            stop_reason = "new_key"
            break

        words = cand.text.split()
        if len(words) >= 12:
            stop_reason = "prose_length"
            break
        cand_lower = cand.text.lower()
        if any(verb in cand_lower.split() for verb in prose_verbs):
            stop_reason = "prose_verb"
            break

        cand_ymin = min(pt[1] for pt in cand.bbox)
        cand_ymax = max(pt[1] for pt in cand.bbox)
        gap_y = cand_ymin - last_ymax

        if gap_y <= max(2.5 * line_h, 40.0):
            absorbed.append(cand)
            last_ymax = cand_ymax
            if re.search(r'\b[1-9][0-9]{5}\b', cand.text):
                stop_reason = "pin_found"
                break
        else:
            stop_reason = "max_gap"
            break
    
    if len(absorbed) >= 3 and stop_reason == "max_gap":
        stop_reason = "max_lines"


    block_text = "\n".join(l.text for l in absorbed)
    return absorbed, block_text, f"block_absorbed_stop_{stop_reason}"


def parse_net_quantity(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)
    
    qualifiers_found = []
    text_lower = text.lower()
    for qw in QUALIFIER_WORDS:
        if qw in text_lower:
            qualifiers_found.append(qw)

    # 1. Complex combination e.g. "3N x 150g + 1N x 150g" or "(3N x150g+1Nx150g Free)"
    combo_matches = re.findall(
        r'(\d+)\s*[nN]?\s*(?:x|X|\*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+|[\u0900-\u097F]+)',
        text
    )
    if len(combo_matches) > 1:
        total_val = 0.0
        total_count = 0
        first_std_unit = None
        first_raw_unit = None
        first_nonstd = False
        unit_val = None
        for count_str, val_str, unit_str in combo_matches:
            c = int(count_str)
            v = float(val_str)
            std_u, raw_u, nonstd = parse_unit_token(unit_str)
            if first_std_unit is None:
                first_std_unit = std_u
                first_raw_unit = raw_u
                first_nonstd = nonstd
                unit_val = v
            total_val += c * v
            total_count += c
        return {
            "value": total_val,
            "unit": first_std_unit,
            "raw_unit": first_raw_unit,
            "unit_nonstandard": first_nonstd,
            "count": total_count,
            "qualifier_words": qualifiers_found,
            "unit_value": unit_val,
            "multipack": True,
        }

    # 2. "Pack of 4 x 50g" or "3 x 150 g" or "3N x 150g"
    nx_match = re.search(
        r'(?:pack\s+of\s+)?(\d+)\s*(?:[nN]|units?|pcs?|pieces?)?\s*(?:x|X|\*)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+|[\u0900-\u097F]+)',
        text,
        re.IGNORECASE
    )
    if nx_match:
        try:
            count_val = int(nx_match.group(1))
            single_val = float(nx_match.group(2))
            unit_str = nx_match.group(3)
            std_u, raw_u, nonstd = parse_unit_token(unit_str)
            total_val = round(count_val * single_val, 4)
            return {
                "value": total_val,
                "unit": std_u,
                "raw_unit": raw_u,
                "unit_nonstandard": nonstd,
                "count": count_val,
                "qualifier_words": qualifiers_found,
                "unit_value": single_val,
                "multipack": count_val > 1,
            }
        except ValueError:
            pass

    # 3. Check "Pack of N" e.g. "Pack of 10"
    count_val = None
    packof_match = re.search(r'pack\s+of\s+(\d+)', text, re.IGNORECASE)
    if packof_match:
        try:
            count_val = int(packof_match.group(1))
        except ValueError:
            pass

    # 4. Standard float + unit e.g. "500 g", "1.5 kg", "200 ml"
    val_num = None
    std_unit = None
    raw_unit = None
    unit_nonstd = False
    unit_val = None
    is_multipack = False

    m = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+|[\u0900-\u097F]+)', text)
    if m:
        try:
            val_num = float(m.group(1))
            unit_str = m.group(2)
            std_u, raw_u, nonstd = parse_unit_token(unit_str)
            std_unit = std_u
            raw_unit = raw_u
            unit_nonstd = nonstd
            if count_val and count_val > 1:
                is_multipack = True
                unit_val = val_num
                val_num = round(count_val * val_num, 4)
        except ValueError:
            pass

    return {
        "value": val_num,
        "unit": std_unit,
        "raw_unit": raw_unit,
        "unit_nonstandard": unit_nonstd,
        "count": count_val,
        "qualifier_words": qualifiers_found,
        "unit_value": unit_val,
        "multipack": is_multipack,
    }


def clean_matched_key_from_line(line_text: str, matched_key: str) -> str:
    if not matched_key:
        return line_text.strip()
    pattern = r'^\s*' + re.escape(matched_key) + r'[\s\:\_\-\.]*'
    cleaned = re.sub(pattern, "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    if cleaned and cleaned.lower() != line_text.lower():
        return cleaned

    no_space_key = matched_key.replace(" ", "")
    pattern_ns = r'^\s*' + re.escape(no_space_key) + r'[\s\:\_\-\.]*'
    cleaned_ns = re.sub(pattern_ns, "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    if cleaned_ns and cleaned_ns.lower() != line_text.lower():
        return cleaned_ns

    cleaned_sub = re.sub(re.escape(matched_key), "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    if cleaned_sub and cleaned_sub.lower() != line_text.lower():
        return cleaned_sub

    cleaned_sub_ns = re.sub(re.escape(no_space_key), "", line_text, flags=re.IGNORECASE).strip(" :-_.")
    if cleaned_sub_ns and cleaned_sub_ns.lower() != line_text.lower():
        return cleaned_sub_ns

    sq_cleaned = strip_squashed_key(line_text, matched_key)
    if sq_cleaned and sq_cleaned.lower() != line_text.lower():
        return sq_cleaned

    return line_text.strip()



def parse_mrp(raw_text: str) -> Dict[str, Any]:
    text = fix_numeric_confusions(raw_text)
    currency, _ = normalize_currency(text)

    tax_pattern = r'[il1|]ncl(usive|\.)?\s*(of\s*)?all\s*tax(es)?'
    has_tax_phrase = bool(re.search(tax_pattern, text, re.IGNORECASE))

    val_num = None
    paise_num = None

    is_phone_pattern = bool(re.search(r'\b(?:1800|1860)(?:[- ]?\d){6,7}\b|\b[6-9]\d{9}\b|\b0\d{2,4}[- ]?\d{6,8}\b', text)) or ("phone" in text.lower() or "toll" in text.lower())

    if not is_phone_pattern:
        m = re.search(
            r'(?:₹|rs\.?|\$|€|£|inr|mrp|mr\.p\.?)\s*[\$\€\£:]*\s*(\d+(?:\.\d{1,2})?)',
            text,
            re.IGNORECASE,
        )
        if not m:
            is_batch_code = bool(re.search(r'[A-Za-z]{2,}\d+|\d+[A-Za-z]+', text))
            if not is_batch_code:
                m = re.search(r'^\s*(\d+(?:\.\d{1,2})?)', text)

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

    m_mon = re.search(r'\b(\d+)\s*months?\b', text, re.IGNORECASE)
    if m_mon:
        return {"day": None, "month": None, "year": None, "duration_months": int(m_mon.group(1))}

    m_yr = re.search(r'\b(\d+)\s*years?\b', text, re.IGNORECASE)
    if m_yr:
        return {"day": None, "month": None, "year": None, "duration_months": int(m_yr.group(1)) * 12}

    m_day = re.search(r'\b(\d+)\s*days?\b', text, re.IGNORECASE)
    if m_day:
        return {"day": None, "month": None, "year": None, "duration_months": round(int(m_day.group(1)) / 30)}

    m1 = re.search(r'\b(\d{1,2})[\/\.\-](\d{1,2})[\/\.\-](\d{2,4})\b', text)
    if m1:
        day_val = int(m1.group(1))
        month_val = int(m1.group(2))
        y = int(m1.group(3))
        year_val = y + 2000 if y < 100 else y
        return {"day": day_val, "month": month_val, "year": year_val, "duration_months": None}

    m2 = re.search(r'\b(\d{1,2})[\/\.\-](\d{2,4})\b', text)
    if m2:
        month_val = int(m2.group(1))
        y = int(m2.group(2))
        year_val = y + 2000 if y < 100 else y
        return {"day": None, "month": month_val, "year": year_val, "duration_months": None}

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
    lines: List[OCRLine], role_name: str, matched_key: str = "", source: str = "block_absorbed"
) -> EntityBlock:
    source_lines = lines
    raw_text = "\n".join(l.text for l in source_lines)
    conf = min(l.confidence for l in source_lines) if source_lines else 0.0
    bbox = union_bboxes([l.bbox for l in source_lines])
    line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]

    pin_match = re.search(r'\b[1-9][0-9]{5}\b', raw_text)
    pin_val = pin_match.group(0) if pin_match else None

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
        source=source,
        name=name_val,
        address=address_val,
        pin=pin_val,
        state=state_val,
        role=role_name,
    )


def parse_consumer_care_block(
    lines: List[OCRLine], matched_key: str = "", source: str = "block_absorbed"
) -> ConsumerCare:
    source_lines = lines
    raw_text = "\n".join(l.text for l in source_lines)
    conf = min(l.confidence for l in source_lines) if source_lines else 0.0
    bbox = union_bboxes([l.bbox for l in source_lines])
    line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]

    email_match = re.search(r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', raw_text)
    email_val = email_match.group(0).replace(" ", "") if email_match else None

    phone_match = re.search(
        r'(?:1800|1860)(?:[- ]?\d){6,7}\b|\b[6-9]\d{9}\b|\b0\d{2,4}[- ]?\d{6,8}\b',
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
        source=source,
        name=name_val,
        address=address_val,
        phone=phone_val,
        email=email_val,
    )


def extract_generic_name(
    lines: List[OCRLine], claimed_line_ids: set, image_h: int = 1200
) -> Optional[FieldModel]:
    stopwords = ["directions", "use", "composition", "ingredients", "store", "caution", "warning", "benefits", "contains", "keep", "shake", "apply", "for external", "net", "mrp", "mfd", "batch"]
    commodity_nouns = ["paste", "cream", "oil", "biscuits", "biscuit", "jam", "pickle", "atta", "flour", "rice", "soap", "shampoo", "powder", "wash", "foam", "solution", "tablets", "tea", "coffee", "salt", "sugar", "spices", "noodles", "noodle", "juice", "drink", "ghee", "butter", "oats", "cereal", "oatmeal", "flakes", "chips", "namkeen", "snack", "lotion", "serum", "cleanser", "gel", "sauce", "ketchup", "pasta", "pulses", "dal", "lentils", "milk", "cheese", "yogurt", "dahi", "paneer"]


    candidates = []
    for line in lines:
        if line.id in claimed_line_ids:
            continue
        text = line.text.strip()
        words = text.split()
        if not (1 <= len(words) <= 5):
            continue
        if any(char.isdigit() for char in text):
            continue
        text_lower = text.lower()
        if any(sw in text_lower for sw in stopwords):
            continue
        
        has_commodity = any(noun in text_lower.split() for noun in commodity_nouns)
        
        # Check if in upper 40%
        c_ymin = min(pt[1] for pt in line.bbox)
        is_top = (c_ymin / max(1, image_h)) <= 0.4

        score = 0
        if has_commodity:
            score += 100
        if is_top:
            score += 50
        # Longer is better if ties
        score += len(text)

        candidates.append((score, line, has_commodity))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_line, has_commodity = candidates[0]
        line_id = best_line.id if best_line.id is not None else 0
        conf = 0.9 if has_commodity else 0.5
        return FieldModel(
            value=best_line.text.strip(),
            raw=best_line.text.strip(),
            bbox=best_line.bbox,
            confidence=conf,
            source_line_ids=[line_id],
            source="top_header_heuristic",
        )
    return None


def extract(
    lines_raw: List[Dict[str, Any]], image_w: int = 1600, image_h: int = 1200
) -> Declarations:
    lines: List[OCRLine] = []
    for idx, item in enumerate(lines_raw):
        if isinstance(item, OCRLine):
            line_obj = item
            if line_obj.id is None:
                line_obj.id = idx
            lines.append(line_obj)
        else:
            lid = item.get("id") if (isinstance(item, dict) and item.get("id") is not None) else idx
            line_obj = OCRLine(
                id=lid,
                text=item["text"],
                confidence=float(item["confidence"]),
                bbox=item["bbox"],
            )
            lines.append(line_obj)

    scripts = list(set(detect_line_script(l.text) for l in lines))

    claimed_line_ids = set()

    extracted_dict: Dict[str, Any] = {}
    extracted_entities: List[EntityBlock] = []

    # Keyed search first
    for idx, line in enumerate(lines):
        match = match_field_key(line.text)
        if not match:
            continue

        field_name, matched_key = match
        if field_name in extracted_dict:
            continue

        if field_name in ["manufacturer", "packer", "importer", "marketer"]:
            absorbed, block_text, stop_reason = absorb_block_lines(lines, idx)
            for l in absorbed:
                if l.id is not None:
                    claimed_line_ids.add(l.id)
            eb = parse_entity_block(absorbed, field_name, matched_key, stop_reason)
            extracted_dict[field_name] = eb
            extracted_entities.append(eb)
            continue

        if field_name == "consumer_care":
            absorbed, block_text, stop_reason = absorb_block_lines(lines, idx)
            for l in absorbed:
                if l.id is not None:
                    claimed_line_ids.add(l.id)
            extracted_dict["consumer_care"] = parse_consumer_care_block(absorbed, matched_key, stop_reason)
            continue

        raw_val_str, source_lines, strategy = resolve_value_lines(lines, idx, field_name)
        for l in source_lines:
            if l.id is not None:
                claimed_line_ids.add(l.id)

        conf = min(l.confidence for l in source_lines) if source_lines else 0.0
        bbox = union_bboxes([l.bbox for l in source_lines])
        line_ids = [l.id if l.id is not None else i for i, l in enumerate(source_lines)]
        crimp_flag = "crimp" if any(is_crimp_text(l.text) for l in source_lines) or is_crimp_text(line.text) else None

        if field_name == "net_quantity":
            parsed = parse_net_quantity(raw_val_str)
            extracted_dict["net_quantity"] = NetQuantity(
                value=parsed["value"],
                unit=parsed["unit"],
                raw_unit=parsed["raw_unit"],
                unit_nonstandard=parsed["unit_nonstandard"],
                count=parsed["count"],
                qualifier_words=parsed["qualifier_words"],
                unit_value=parsed.get("unit_value"),
                multipack=parsed.get("multipack", False),
                declared_elsewhere=crimp_flag,
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
                declared_elsewhere=crimp_flag,
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
            if parsed["day"] is None and parsed["month"] is None and parsed["year"] is None and parsed["duration_months"] is None:
                continue
            extracted_dict[field_name] = DateField(
                day=parsed["day"],
                month=parsed["month"],
                year=parsed["year"],
                duration_months=parsed["duration_months"],
                declared_elsewhere=crimp_flag,
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
        elif field_name == "generic_name":
            clean_gen = raw_val_str.replace("Generic Name", "").replace("Common Name", "").replace("Name of Commodity", "").replace("Commodity", "").strip(" :-_.")
            extracted_dict["generic_name"] = FieldModel(
                value=clean_gen if clean_gen else raw_val_str,
                raw=raw_val_str,
                bbox=bbox,
                confidence=round(float(conf), 4),
                source_line_ids=line_ids,
                source=strategy,
            )

    # Check global crimp notices and tax phrases (squash "ofalltax" / "ofaltax")
    for line in lines:
        sq = squash(line.text)
        has_tax = any(pat in sq for pat in ["ofalltax", "ofaltax", "inclofalltax", "inclofaltax", "inclofal", "ofal"])
        has_crimp = is_crimp_text(line.text) or "seecodingarea" in sq or "seecrimp" in sq or "oncrimp" in sq or "atcrimp" in sq

        if has_tax or has_crimp:
            txt_lower = line.text.lower()
            has_rupee_val = bool(re.search(r'(?:₹|rs\.?|inr)\s*\d+|\b\d+\.\d{2}\b', line.text, re.IGNORECASE))

            if (has_tax and not has_rupee_val) or has_crimp or "mrp" in txt_lower or "price" in txt_lower:
                if "mrp" not in extracted_dict or extracted_dict["mrp"].value is None:
                    extracted_dict["mrp"] = MRP(
                        declared_elsewhere="crimp",
                        raw=line.text,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="crimp_notice",
                    )
            if "usp" in sq or "unitsaleprice" in sq or "unit" in txt_lower:
                if "unit_sale_price" not in extracted_dict or extracted_dict["unit_sale_price"].value is None:
                    extracted_dict["unit_sale_price"] = UnitSalePrice(
                        declared_elsewhere="crimp",
                        raw=line.text,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="crimp_notice",
                    )
            if "mfg" in txt_lower or "pkd" in txt_lower or "date" in txt_lower or "mfd" in sq or "batch" in sq:
                if "mfg_date" not in extracted_dict or (extracted_dict["mfg_date"].month is None and extracted_dict["mfg_date"].year is None):
                    extracted_dict["mfg_date"] = DateField(
                        declared_elsewhere="crimp",
                        raw=line.text,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="crimp_notice",
                    )
            if "exp" in txt_lower or "best before" in txt_lower or "use by" in txt_lower:
                if "best_before" not in extracted_dict or (extracted_dict["best_before"].month is None and extracted_dict["best_before"].year is None):
                    extracted_dict["best_before"] = DateField(
                        declared_elsewhere="crimp",
                        raw=line.text,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="crimp_notice",
                    )

    # GLOBAL FALLBACKS — run ONLY when keyed search returned nothing for that field
    # 1. Phone & Email fallback
    cc_obj = extracted_dict.get("consumer_care")
    if cc_obj is None or not cc_obj.phone:
        for line in lines:
            m_phone = re.search(
                r'\b(?:1800|1860)(?:[- ]?\d){6,7}\b|\b[6-9]\d{9}\b|\b0\d{2,4}[- ]?\d{6,8}\b',
                line.text,
            )
            if m_phone:
                phone_str = m_phone.group(0)
                if cc_obj is None:
                    extracted_dict["consumer_care"] = ConsumerCare(
                        value=line.text.strip(),
                        raw=line.text.strip(),
                        phone=phone_str,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="global_regex",
                    )
                    cc_obj = extracted_dict["consumer_care"]
                else:
                    cc_obj.phone = phone_str
                break

    if cc_obj is None or not cc_obj.email:
        for line in lines:
            m_email = re.search(r'\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', line.text)
            if m_email:
                email_str = m_email.group(0).replace(" ", "")
                if cc_obj is None:
                    extracted_dict["consumer_care"] = ConsumerCare(
                        value=line.text.strip(),
                        raw=line.text.strip(),
                        email=email_str,
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="global_regex",
                    )
                    cc_obj = extracted_dict["consumer_care"]
                else:
                    cc_obj.email = email_str
                break

    # 2. PIN fallback to entity block or manufacturer
    pin_found = None
    pin_line = None
    for line in lines:
        m_pin = re.search(r'\b[1-9][0-9]{5}\b', line.text)
        if m_pin:
            pin_found = m_pin.group(0)
            pin_line = line
            break

    if pin_found:
        entities = ["manufacturer", "packer", "importer", "marketer"]
        has_pin = any(
            extracted_dict.get(e) and getattr(extracted_dict[e], "pin", None)
            for e in entities
        )
        if not has_pin:
            target_ent = None
            for e in entities:
                if e in extracted_dict and extracted_dict[e]:
                    target_ent = extracted_dict[e]
                    break
            if target_ent:
                target_ent.pin = pin_found
            else:
                eb_pin = EntityBlock(
                    value=pin_line.text.strip(),
                    raw=pin_line.text.strip(),
                    name=pin_line.text.strip(),
                    address=pin_line.text.strip(),
                    pin=pin_found,
                    bbox=pin_line.bbox,
                    confidence=round(float(pin_line.confidence * 0.8), 4),
                    source_line_ids=[pin_line.id],
                    source="global_regex",
                    role="unqualified",
                )
                extracted_dict["manufacturer"] = eb_pin
                extracted_entities.append(eb_pin)

    # 3. Standalone Quantity fallback
    if "net_quantity" not in extracted_dict:
        for line in lines:
            m_qty = re.search(r'\b(\d+(?:\.\d+)?)\s*(g|kg|ml|l|L|gms|grams|liter|litres|ml.)\b', line.text)
            if m_qty and "mrp" not in line.text.lower() and "rs" not in line.text.lower() and "per" not in line.text.lower():
                parsed = parse_net_quantity(line.text)
                if parsed["value"] is not None:
                    extracted_dict["net_quantity"] = NetQuantity(
                        value=parsed["value"],
                        unit=parsed["unit"],
                        raw_unit=parsed["raw_unit"],
                        unit_nonstandard=parsed["unit_nonstandard"],
                        count=parsed["count"],
                        qualifier_words=parsed["qualifier_words"],
                        unit_value=parsed.get("unit_value"),
                        multipack=parsed.get("multipack", False),
                        raw=line.text.strip(),
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="global_regex",
                    )
                    break

    # 4. Unkeyed Date fallback
    skip_keywords = ["toll", "free", "1800", "1860", "tel", "phone", "helpline"]
    unkeyed_dates = []
    unkeyed_regex = re.compile(r'(?<![\d-])(0[1-9]|1[0-2])[-/](20[2-3]\d)(?![\d-])')

    for line in lines:
        txt_lower = line.text.lower()
        if any(kw in txt_lower for kw in skip_keywords):
            continue
        for m in unkeyed_regex.finditer(line.text):
            m_month = int(m.group(1))
            m_year = int(m.group(2))
            unkeyed_dates.append((m_year, m_month, line))

    if unkeyed_dates:
        unkeyed_dates.sort(key=lambda d: (d[0], d[1]))
        if "mfg_date" not in extracted_dict or (extracted_dict["mfg_date"].month is None and extracted_dict["mfg_date"].year is None):
            earliest = unkeyed_dates[0]
            extracted_dict["mfg_date"] = DateField(
                day=None,
                month=earliest[1],
                year=earliest[0],
                raw=earliest[2].text.strip(),
                bbox=earliest[2].bbox,
                confidence=round(float(earliest[2].confidence * 0.8), 4),
                source_line_ids=[earliest[2].id],
                source="unkeyed",
            )
        if len(unkeyed_dates) >= 2:
            latest = unkeyed_dates[-1]
            if "best_before" not in extracted_dict:
                extracted_dict["best_before"] = DateField(
                    day=None,
                    month=latest[1],
                    year=latest[0],
                    raw=latest[2].text.strip(),
                    bbox=latest[2].bbox,
                    confidence=round(float(latest[2].confidence * 0.8), 4),
                    source_line_ids=[latest[2].id if latest[2].id is not None else 0],
                    source="unkeyed",
                )
            elif extracted_dict["best_before"].month is None and extracted_dict["best_before"].year is None:
                bb = extracted_dict["best_before"]
                bb.month = latest[1]
                bb.year = latest[0]

    # 5. MRP & USP combined / standalone pattern fallback
    if "mrp" not in extracted_dict:
        for line in lines:
            m_comb = re.search(r'(\d+(?:\.\d{1,2})?)\s*[:(]\s*\(?(\d+(?:\.\d+)?)\s*/\s*(ml|g|kg|l|L)\)?', line.text)
            if m_comb:
                try:
                    mrp_val = float(m_comb.group(1))
                    usp_val = float(m_comb.group(2))
                    usp_u, _, _ = parse_unit_token(m_comb.group(3))
                    extracted_dict["mrp"] = MRP(
                        value=mrp_val,
                        currency="INR",
                        incl_taxes_phrase=True,
                        raw=line.text.strip(),
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="global_regex",
                    )
                    if "unit_sale_price" not in extracted_dict:
                        extracted_dict["unit_sale_price"] = UnitSalePrice(
                            value=usp_val,
                            per_qty=1.0,
                            per_unit=usp_u,
                            value_per_base_unit=usp_val,
                            raw=line.text.strip(),
                            bbox=line.bbox,
                            confidence=round(float(line.confidence * 0.8), 4),
                            source_line_ids=[line.id],
                            source="global_regex",
                        )
                    break
                except ValueError:
                    pass

    if "mrp" not in extracted_dict:
        for line in lines:
            m_mrp = re.search(r'(?:₹|rs\.?|inr)\s*(\d+(?:\.\d{1,2})?)', line.text, re.IGNORECASE)
            if m_mrp:
                try:
                    mrp_val = float(m_mrp.group(1))
                    parsed = parse_mrp(line.text)
                    extracted_dict["mrp"] = MRP(
                        value=mrp_val,
                        currency=parsed["currency"],
                        incl_taxes_phrase=parsed["incl_taxes_phrase"],
                        paise=parsed["paise"],
                        raw=line.text.strip(),
                        bbox=line.bbox,
                        confidence=round(float(line.confidence * 0.8), 4),
                        source_line_ids=[line.id],
                        source="global_regex",
                    )
                    break
                except ValueError:
                    pass

    # Generic name heuristic if missing
    if "generic_name" not in extracted_dict:
        gen_field = extract_generic_name(lines, claimed_line_ids, image_h)
        if gen_field:
            extracted_dict["generic_name"] = gen_field
            for lid in gen_field.source_line_ids:
                claimed_line_ids.add(lid)

    # Unqualified address detection (deemed manufacturer per Rule 6(1)(a) Explanation I)
    unqualified_patterns = [r'\bdist\.?\b', r'\bdistt\.?\b', r'\bh\.?p\.?\b', r'\bsolan\b', r'\bmumbai\b', r'\bkalbadevi\b', r'\bindia\b', r'\bdelhi\b', r'\bbaddi\b', r'\bgujarat\b', r'\bmaharashtra\b', r'\broad\b', r'\bindustrial\s+area\b']
    for line in lines:
        if line.id in claimed_line_ids:
            continue
        txt_lower = line.text.lower()
        if any(kw in txt_lower for kw in ["mrp", "rs.", "inr", "net", "qty", "mfg", "exp", "batch", "phone", "email", "tollfree", "lever.care", "daburcares"]):
            continue
        m_pin = re.search(r'\b[1-9][0-9]{5}\b', line.text)
        has_addr_kw = any(re.search(pat, txt_lower) for pat in unqualified_patterns)
        if m_pin or has_addr_kw:
            pin_val = m_pin.group(0) if m_pin else None
            unq_eb = EntityBlock(
                value=line.text.strip(),
                raw=line.text.strip(),
                name=line.text.strip(),
                address=line.text.strip(),
                pin=pin_val,
                bbox=line.bbox,
                confidence=round(float(line.confidence * 0.8), 4),
                source_line_ids=[line.id],
                source="unqualified_line",
                role="unqualified",
            )
            extracted_entities.append(unq_eb)
            if "manufacturer" not in extracted_dict and "marketer" not in extracted_dict and "packer" not in extracted_dict:
                extracted_dict["manufacturer"] = unq_eb

    multi_unit_note = False
    for line in lines:
        text_lower = line.text.lower()
        if "name" in text_lower and "address" in text_lower and "mfg" in text_lower and "unit" in text_lower and "batch" in text_lower:
            multi_unit_note = True
            break

    return Declarations(
        manufacturer=extracted_dict.get("manufacturer"),
        packer=extracted_dict.get("packer"),
        importer=extracted_dict.get("importer"),
        marketer=extracted_dict.get("marketer"),
        entities=extracted_entities,
        country_of_origin=extracted_dict.get("country_of_origin"),
        generic_name=extracted_dict.get("generic_name"),
        net_quantity=extracted_dict.get("net_quantity"),
        mrp=extracted_dict.get("mrp"),
        unit_sale_price=extracted_dict.get("unit_sale_price"),
        mfg_date=extracted_dict.get("mfg_date"),
        best_before=extracted_dict.get("best_before"),
        consumer_care=extracted_dict.get("consumer_care"),
        scripts_detected=scripts,
        multi_unit_note=multi_unit_note,
    )

