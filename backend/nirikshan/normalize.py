import re
from typing import Dict, List, Optional, Tuple

DEVANAGARI_MAP = str.maketrans('०१२३४५६७८९', '0123456789')
FULLWIDTH_PUNCT_MAP = str.maketrans('（）：，。', '():,.')


def normalize_line_text(text: str) -> str:
    """Map full-width punctuation （）：，。 to ASCII and drop CJK characters (U+3000–U+303F, U+4E00–U+9FFF)."""
    if not text:
        return ""
    text = text.translate(FULLWIDTH_PUNCT_MAP)
    text = re.sub(r'[\u3000-\u303F\u4E00-\u9FFF]+', '', text)
    return text.strip()

STANDARD_UNITS = {
    "g", "kg", "ml", "L", "l", "cm", "m", "N", "U",
    "piece", "pieces", "pcs", "pair", "set"
}

UNIT_MAPPING: Dict[str, Tuple[str, bool]] = {
    "g": ("g", False),
    "gm": ("g", True),
    "gms": ("g", True),
    "gram": ("g", True),
    "grams": ("g", True),
    "kg": ("kg", False),
    "kgs": ("kg", False),
    "ml": ("ml", False),
    "m.l.": ("ml", False),
    "l": ("L", False),
    "L": ("L", False),
    "ltr": ("L", True),
    "lt": ("L", True),
    "litre": ("L", True),
    "litres": ("L", True),
    "cm": ("cm", False),
    "m": ("m", False),
    "meter": ("m", False),
    "meters": ("m", False),
    "n": ("N", False),
    "N": ("N", False),
    "nos": ("N", False),
    "no": ("N", False),
    "u": ("U", False),
    "U": ("U", False),
    "unit": ("U", False),
    "units": ("U", False),
    "piece": ("piece", False),
    "pieces": ("piece", False),
    "pcs": ("piece", False),
    "pair": ("pair", False),
    "set": ("set", False),
    "oz": ("oz", True),
    "lb": ("lb", True),
    "lbs": ("lb", True),
    "doz": ("doz", True),
    "dozen": ("doz", True),
    "ग्राम": ("g", True),
}

CURRENCY_TOKENS = ["₹", "rs.", "rs", "inr", "र", "रु", "rs.."]

INDIAN_STATES = [
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHHATTISGARH",
    "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JHARKHAND", "KARNATAKA",
    "KERALA", "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA", "MIZORAM",
    "NAGALAND", "ODISHA", "PUNJAB", "RAJASTHAN", "SIKKIM", "TAMIL NADU",
    "TELANGANA", "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND", "WEST BENGAL",
    "DELHI", "NEW DELHI", "JAMMU AND KASHMIR", "LADAKH", "PUDUCHERRY", "CHANDIGARH"
]


def squash(text: str) -> str:
    """Lowercase, strip, remove all whitespace and punctuation."""
    if not text:
        return ""
    # remove whitespace and punctuation like . : - _ , ; ( ) / \
    cleaned = re.sub(r'[\s\.\:\_\-\,\;\(\)\/\\\'\"]+', '', text.lower())
    return cleaned


def convert_devanagari_digits(text: str) -> str:
    """Convert Devanagari numerals ०-९ to ASCII 0-9."""
    if not text:
        return ""
    return text.translate(DEVANAGARI_MAP)


def fix_numeric_confusions(text: str) -> str:
    """Fix common OCR confusions O->0, l/I->1, S->5, B->8 inside digit contexts."""
    if not text:
        return ""
    text = convert_devanagari_digits(text)
    
    # Replace O/o in numeric context (adjacent to digits)
    text = re.sub(r'(?<=\d)[Oo]+', lambda m: '0' * len(m.group(0)), text)
    text = re.sub(r'[Oo]+(?=\d)', lambda m: '0' * len(m.group(0)), text)
    
    # Replace l/I in numeric context
    text = re.sub(r'(?<=\d)[lI]+', lambda m: '1' * len(m.group(0)), text)
    text = re.sub(r'[lI]+(?=\d)', lambda m: '1' * len(m.group(0)), text)

    # Replace S/s in numeric context (excluding currency token Rs/rs)
    text = re.sub(r'(?<=\d)[Ss]+', lambda m: '5' * len(m.group(0)), text)
    text = re.sub(r'(?<![Rr])[Ss]+(?=\d)', lambda m: '5' * len(m.group(0)), text)

    # Replace B in numeric context
    text = re.sub(r'(?<=\d)B+', lambda m: '8' * len(m.group(0)), text)
    text = re.sub(r'B+(?=\d)', lambda m: '8' * len(m.group(0)), text)

    return text



def normalize_currency(text: str) -> Tuple[Optional[str], str]:
    """Detect currency in text."""
    lower = text.lower()
    if "$" in text:
        return "USD", "$"
    if "€" in text:
        return "EUR", "€"
    if "£" in text:
        return "GBP", "£"
    for token in CURRENCY_TOKENS:
        if token in lower:
            return "INR", token
    return "unknown", ""



def parse_unit_token(token: str) -> Tuple[Optional[str], str, bool]:
    """Normalize raw unit token into (std_unit, raw_unit, is_nonstandard)."""
    clean_tok = token.strip().rstrip('.').lower()
    if clean_tok in UNIT_MAPPING:
        std_unit, nonstd = UNIT_MAPPING[clean_tok]
        return std_unit, token, nonstd
    # Exact check
    for key, (std_unit, nonstd) in UNIT_MAPPING.items():
        if clean_tok == key:
            return std_unit, token, nonstd
    return clean_tok, token, True


def detect_line_script(text: str) -> str:
    """Detect script per line: latin / devanagari / other."""
    if not text:
        return "other"
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', text))
    has_latin = bool(re.search(r'[a-zA-Z]', text))
    if has_devanagari and has_latin:
        return "latin_devanagari"
    if has_devanagari:
        return "devanagari"
    if has_latin:
        return "latin"
    return "other"
