"""Nigrani/Jaal helpers.

* ``dual_mrp`` — R17 (Rule 18(2A)): the same commodity (name + net quantity)
  seen in an earlier scan of this session with a different MRP.
* ``jaal`` — R29/R30 (Rules 6(10), 31): turn a listing page or listing
  screenshots into declarations and judge platform-side compliance.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

_WS = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# R17 — dual MRP across scans
# ---------------------------------------------------------------------------

def _norm(s: Optional[str]) -> str:
    return _WS.sub(" ", (s or "").strip().lower())


def product_key(decl: Any) -> Optional[str]:
    """Identity of a commodity for Rule 18(2A): generic name (or the
    responsible entity's name) plus the declared net quantity."""
    if decl is None:
        return None
    gn = getattr(decl, "generic_name", None)
    name = _norm(getattr(gn, "value", None) if gn else None)
    if not name:
        pe = getattr(decl, "primary_entity", None)
        name = _norm(getattr(pe, "name", None) if pe else None)
    nq = getattr(decl, "net_quantity", None)
    if not name or nq is None or nq.value is None or not nq.unit:
        return None
    return f"{name}|{float(nq.value):g}{str(nq.unit).lower()}"


def _key_from_result(result: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    merged = result.get("merged") or result.get("declarations") or {}
    gn = (merged.get("generic_name") or {}).get("value")
    name = _norm(gn)
    if not name:
        for ek in ("manufacturer", "packer", "importer", "marketer"):
            ent = merged.get(ek) or {}
            if ent.get("name"):
                name = _norm(ent["name"])
                break
    nq = merged.get("net_quantity") or {}
    mrp = (merged.get("mrp") or {}).get("value")
    if not name or nq.get("value") is None or not nq.get("unit"):
        return None, mrp
    return f"{name}|{float(nq['value']):g}{str(nq['unit']).lower()}", mrp


def find_dual_mrp(decl: Any, prior_scans: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare the current declarations with earlier scan records
    (``session_store.get_results`` shape: {id, result, created_at})."""
    key = product_key(decl)
    mrp = getattr(getattr(decl, "mrp", None), "value", None)
    out: Dict[str, Any] = {"key": key, "mrp": mrp, "matches": [], "conflicts": []}
    if key is None or mrp is None:
        return out
    for rec in prior_scans or []:
        k, m = _key_from_result(rec.get("result") or {})
        if k != key or m is None:
            continue
        entry = {"scan_id": rec.get("id"), "mrp": float(m), "created_at": rec.get("created_at")}
        out["matches"].append(entry)
        if abs(float(m) - float(mrp)) > 0.005:
            out["conflicts"].append(entry)
    return out


# ---------------------------------------------------------------------------
# R29/R30 — e-commerce listing mode (Jaal)
# ---------------------------------------------------------------------------

class _TextCollector(HTMLParser):
    KEEP = {"title", "h1", "h2", "h3", "li", "td", "th", "p", "span", "div", "dd", "dt", "b", "strong", "label"}
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._buf: List[str] = []
        self.lines: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("br", "li", "p", "tr", "div", "h1", "h2", "h3", "dt", "dd", "title"):
            self._flush()

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.KEEP or tag == "tr":
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        t = _WS.sub(" ", data).strip()
        if t:
            self._buf.append(t)

    def _flush(self):
        if self._buf:
            self.lines.append(" ".join(self._buf))
            self._buf = []

    def close(self):
        super().close()
        self._flush()


def html_to_lines(html: str, max_lines: int = 400) -> List[str]:
    p = _TextCollector()
    p.feed(html)
    p.close()
    seen, out = set(), []
    for t in p.lines:
        t = t.strip()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_lines:
            break
    return out


def fetch_listing_html(url: str, timeout: float = 10.0) -> str:
    """Fetch a public listing page. Caller decides whether fetching is permitted."""
    import requests
    if not re.match(r"^https?://", url or "", re.I):
        raise ValueError("URL must start with http:// or https://")
    resp = requests.get(url, timeout=timeout, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Nirikshan/0.3; +https://github.com/rajputjay00/SIH-NIRIKSHAN)",
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    })
    resp.raise_for_status()
    return resp.text


def lines_to_ocr(texts: List[str], line_h: float = 30.0, char_w: float = 9.0) -> List[Dict[str, Any]]:
    """Synthetic OCR lines for text that has no geometry (HTML)."""
    out = []
    for i, t in enumerate(texts):
        y = 10.0 + i * line_h
        w = max(20.0, char_w * len(t))
        out.append({"text": t, "confidence": 1.0, "bbox": [[10.0, y], [10.0 + w, y], [10.0 + w, y + line_h - 6], [10.0, y + line_h - 6]]})
    return out


# Rule 6(10) read with Rule 6(1): declarations the platform must display
LISTING_REQUIRED: List[Tuple[str, str]] = [
    ("entity", "Name and address of manufacturer / packer / importer — Rule 6(1)(a)"),
    ("generic_name", "Common or generic name — Rule 6(1)(b)"),
    ("net_quantity", "Net quantity — Rule 6(1)(c)"),
    ("mrp", "Maximum retail price inclusive of all taxes — Rule 6(1)(e)"),
    ("consumer_care", "Consumer care details — Rule 6(2)"),
]
LISTING_IMPORT_EXTRA: Tuple[str, str] = ("country_of_origin", "Country of origin — Rule 6(1)(aa)")
# Rule 6(10) proviso: date of manufacture / best-before need not be shown on the listing
# (they are pack-specific); reported as informational.
LISTING_OPTIONAL: List[Tuple[str, str]] = [
    ("date", "Month/year of manufacture or best-before — Rule 6(1)(d)/(da) (proviso: not required on the listing)"),
]


def listing_presence(decl: Any, is_import: bool) -> Dict[str, Any]:
    def has(field: str) -> bool:
        if field == "entity":
            pe = getattr(decl, "primary_entity", None)
            return bool(pe and (pe.name or pe.address or pe.value))
        if field == "date":
            for f in ("mfg_date", "best_before"):
                v = getattr(decl, f, None)
                if v and (v.year or v.raw):
                    return True
            return False
        if field == "consumer_care":
            cc = getattr(decl, "consumer_care", None)
            return bool(cc and (cc.phone or cc.email or cc.value))
        f = getattr(decl, field, None)
        return bool(f and (getattr(f, "value", None) not in (None, "") or getattr(f, "raw", None)))

    required = list(LISTING_REQUIRED) + ([LISTING_IMPORT_EXTRA] if is_import else [])
    present, missing = [], []
    for field, label in required:
        (present if has(field) else missing).append({"field": field, "label": label})
    optional = [{"field": f, "label": l, "present": has(f)} for f, l in LISTING_OPTIONAL]
    return {"present": present, "missing": missing, "optional": optional, "is_import": is_import}


def font_parity(decl: Any) -> Optional[Dict[str, Any]]:
    """Rule 31: the net quantity must be shown in a font at least as large as
    the MRP wherever the MRP is quoted. Uses OCR line-box heights."""
    mrp = getattr(decl, "mrp", None)
    nq = getattr(decl, "net_quantity", None)
    if not (mrp and mrp.bbox and nq and nq.bbox):
        return None
    from nirikshan.geometry import quad_to_rect
    _, my0, _, my1 = quad_to_rect(mrp.bbox)
    _, ny0, _, ny1 = quad_to_rect(nq.bbox)
    mh, nh = max(1.0, my1 - my0), max(1.0, ny1 - ny0)
    ratio = nh / mh
    return {
        "rule": "31",
        "mrp_height_px": round(mh, 1),
        "net_quantity_height_px": round(nh, 1),
        "ratio": round(ratio, 2),
        "ok": ratio >= 0.9,
        "marginal": 0.75 <= ratio < 0.9,
        "method": "OCR line-box heights on the listing screenshot",
    }
