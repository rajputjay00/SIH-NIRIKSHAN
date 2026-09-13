import pytest
from nirikshan.normalize import (
    convert_devanagari_digits,
    detect_line_script,
    fix_numeric_confusions,
    normalize_currency,
    parse_unit_token,
    squash,
)


def test_squash():
    assert squash("NET QUANTITY") == "netquantity"
    assert squash("NETQUANTITY") == "netquantity"
    assert squash("Net Qty.") == "netqty"
    assert squash("M.R.P. (Incl. of all taxes)") == "mrpinclofalltaxes"


def test_convert_devanagari_digits():
    assert convert_devanagari_digits("शुद्ध मात्रा ५०० ग्राम") == "शुद्ध मात्रा 500 ग्राम"
    assert convert_devanagari_digits("MRP ₹१५०.००") == "MRP ₹150.00"


def test_fix_numeric_confusions():
    assert fix_numeric_confusions("5OOg") == "500g"
    assert fix_numeric_confusions("l00 ml") == "100 ml"
    assert fix_numeric_confusions("Rs. l50") == "Rs. 150"


def test_normalize_currency():
    assert normalize_currency("MRP ₹ 150")[0] == "INR"
    assert normalize_currency("Rs. 45.00")[0] == "INR"
    assert normalize_currency("INR 200")[0] == "INR"
    assert normalize_currency("Price 50")[0] == "unknown"


def test_parse_unit_token():
    std_u, raw_u, nonstd = parse_unit_token("gms")
    assert std_u == "g"
    assert raw_u == "gms"
    assert nonstd is True

    std_u2, raw_u2, nonstd2 = parse_unit_token("g")
    assert std_u2 == "g"
    assert nonstd2 is False

    std_u3, raw_u3, nonstd3 = parse_unit_token("ltr")
    assert std_u3 == "L"
    assert nonstd3 is True


def test_detect_line_script():
    assert detect_line_script("NET QUANTITY 500 g") == "latin"
    assert detect_line_script("शुद्ध मात्रा ५०० ग्राम") == "devanagari"
    assert detect_line_script("MRP ₹150 (रु १५०)") == "latin_devanagari"
