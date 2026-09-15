"""Maap (माप) — geometry and contrast measurements from OCR boxes and pixels.

All measurements here are *scale-free ratios* (no mm needed):

* R20 — Rule 8(1): clear space around the net-quantity declaration, expressed
  in multiples of the numeral height (≥ 1× above/below, ≥ 2× left/right).
* R19 — Rule 7(3): average glyph width ≥ ⅓ of glyph height (except 1, i, I, l).
* R22 — Rule 9(1)(b): luminance contrast between numerals and background.

OCR boxes are line boxes, not glyph boxes, so every result carries an
uncertainty note and the rules built on them never FAIL on their own: they
PASS or ask the officer to confirm with a graduated scale (NEEDS_REVIEW).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Fraction of an OCR line-box height that is the numeral/cap height. PP-OCR
# boxes wrap ascender-to-descender with a little padding; 0.72 is a middle
# estimate for Latin digits and capitals.
CAP_HEIGHT_FRACTION = 0.72
# Fraction of the per-character advance that is ink (the rest is side bearing / spacing)
GLYPH_WIDTH_FRACTION = 0.80

CLEAR_SPACE_REQUIRED = {"above": 1.0, "below": 1.0, "left": 2.0, "right": 2.0}
ASPECT_MIN_RATIO = 1.0 / 3.0
CONTRAST_PASS_RATIO = 3.0        # WCAG-style luminance ratio; below this → officer confirms
CONTRAST_MIN_BOX_PX = 8


def quad_to_rect(bbox: List[List[float]]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return min(xs), min(ys), max(xs), max(ys)


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


# ---------------------------------------------------------------------------
# R20 — clear space
# ---------------------------------------------------------------------------

def clear_space(
    target_bbox: List[List[float]],
    other_boxes: List[Tuple[int, List[List[float]]]],
    image_w: Optional[float] = None,
    image_h: Optional[float] = None,
) -> Dict[str, Any]:
    """Distance from the target box to the nearest other text box in each
    direction, in multiples of the estimated numeral height."""
    x0, y0, x1, y1 = quad_to_rect(target_bbox)
    box_h = max(1.0, y1 - y0)
    numeral_h = box_h * CAP_HEIGHT_FRACTION

    gaps: Dict[str, Dict[str, Any]] = {}
    for d in ("above", "below", "left", "right"):
        gaps[d] = {"gap_px": None, "ratio": None, "required": CLEAR_SPACE_REQUIRED[d], "ok": True, "neighbour_line_id": None}

    def consider(d: str, gap: float, lid: int):
        g = gaps[d]
        if g["gap_px"] is None or gap < g["gap_px"]:
            g["gap_px"] = round(max(0.0, gap), 1)
            g["neighbour_line_id"] = lid

    for lid, bb in other_boxes:
        ox0, oy0, ox1, oy1 = quad_to_rect(bb)
        h_ov = _overlap(x0, x1, ox0, ox1)
        v_ov = _overlap(y0, y1, oy0, oy1)
        if h_ov > 0 and v_ov > 0:
            # intersecting boxes: attribute to the direction of the neighbour's centre
            cx, cy = (ox0 + ox1) / 2, (oy0 + oy1) / 2
            tcx, tcy = (x0 + x1) / 2, (y0 + y1) / 2
            if abs(cy - tcy) >= abs(cx - tcx):
                consider("above" if cy < tcy else "below", 0.0, lid)
            else:
                consider("left" if cx < tcx else "right", 0.0, lid)
            continue
        if h_ov > 0:
            if oy1 <= y0:
                consider("above", y0 - oy1, lid)
            elif oy0 >= y1:
                consider("below", oy0 - y1, lid)
        elif v_ov > 0:
            if ox1 <= x0:
                consider("left", x0 - ox1, lid)
            elif ox0 >= x1:
                consider("right", ox0 - x1, lid)

    all_ok = True
    worst = None
    for d, g in gaps.items():
        if g["gap_px"] is None:
            g["ratio"] = None          # nothing in that direction → clear
            continue
        g["ratio"] = round(g["gap_px"] / numeral_h, 2)
        g["ok"] = g["ratio"] >= g["required"] - 1e-9
        if not g["ok"]:
            all_ok = False
            deficit = g["required"] - g["ratio"]
            if worst is None or deficit > worst[1]:
                worst = (d, deficit)

    return {
        "rule": "8(1)",
        "numeral_height_px": round(numeral_h, 1),
        "line_box_height_px": round(box_h, 1),
        "gaps": gaps,
        "all_ok": all_ok,
        "worst_direction": worst[0] if worst else None,
        "method": "OCR line boxes; numeral height ≈ 0.72 × line-box height",
    }


def clear_space_summary(cs: Dict[str, Any]) -> str:
    parts = []
    for d, g in cs["gaps"].items():
        if g["ratio"] is None:
            parts.append(f"{d}: clear")
        else:
            parts.append(f"{d}: {g['ratio']}× (need {g['required']}×){'' if g['ok'] else ' ✗'}")
    return "; ".join(parts)


# ---------------------------------------------------------------------------
# R19 — glyph width / height
# ---------------------------------------------------------------------------

def aspect_estimate(text: str, bbox: List[List[float]]) -> Optional[Dict[str, Any]]:
    """Average glyph width ÷ cap height from a line box. Excludes spaces and
    the narrow glyphs Rule 7(3) exempts (1, i, I, l, and punctuation)."""
    if not text or not bbox:
        return None
    x0, y0, x1, y1 = quad_to_rect(bbox)
    box_w, box_h = max(1.0, x1 - x0), max(1.0, y1 - y0)
    n_all = len([c for c in text if not c.isspace()])
    n_wide = len([c for c in text if c.isalnum() and c not in "1iIl"])
    if n_all < 3 or n_wide < 2:
        return None
    advance = box_w / n_all
    glyph_w = advance * GLYPH_WIDTH_FRACTION
    cap_h = box_h * CAP_HEIGHT_FRACTION
    ratio = glyph_w / cap_h
    return {
        "rule": "7(3)",
        "avg_glyph_width_px": round(glyph_w, 1),
        "cap_height_px": round(cap_h, 1),
        "ratio": round(ratio, 3),
        "min_ratio": round(ASPECT_MIN_RATIO, 3),
        "ok": ratio >= ASPECT_MIN_RATIO,
        "chars_measured": n_all,
        "method": "line-box width ÷ characters × 0.8, over 0.72 × line-box height",
    }


# ---------------------------------------------------------------------------
# R22 — contrast
# ---------------------------------------------------------------------------

def _rel_luminance(rgb: Tuple[float, float, float]) -> float:
    def ch(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_in_box(image, bbox: List[List[float]]) -> Optional[Dict[str, Any]]:
    """Luminance contrast ratio between the two Otsu clusters (ink vs paper)
    inside an OCR box. ``image`` is a PIL image in the same coordinate space
    as the bbox (i.e. the pre-processed OCR image)."""
    import numpy as np
    import cv2

    x0, y0, x1, y1 = quad_to_rect(bbox)
    w, h = image.size
    x0, y0 = int(max(0, x0)), int(max(0, y0))
    x1, y1 = int(min(w, x1)), int(min(h, y1))
    if x1 - x0 < CONTRAST_MIN_BOX_PX or y1 - y0 < CONTRAST_MIN_BOX_PX:
        return None

    crop = np.asarray(image.convert("RGB").crop((x0, y0, x1, y1)))
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    thresh, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = crop[mask == 0]
    light = crop[mask == 255]
    if len(dark) < 4 or len(light) < 4:
        return {"rule": "9(1)(b)", "ratio": 1.0, "ok": False, "note": "single-tone region — no separable text"}

    dark_mean = tuple(float(v) for v in dark.mean(axis=0))
    light_mean = tuple(float(v) for v in light.mean(axis=0))
    l_dark, l_light = _rel_luminance(dark_mean), _rel_luminance(light_mean)
    ratio = (max(l_dark, l_light) + 0.05) / (min(l_dark, l_light) + 0.05)
    # the smaller cluster is usually the text
    text_is_dark = len(dark) <= len(light)
    return {
        "rule": "9(1)(b)",
        "ratio": round(ratio, 2),
        "min_ratio": CONTRAST_PASS_RATIO,
        "ok": ratio >= CONTRAST_PASS_RATIO,
        "text_rgb": [round(v) for v in (dark_mean if text_is_dark else light_mean)],
        "background_rgb": [round(v) for v in (light_mean if text_is_dark else dark_mean)],
        "otsu_threshold": float(thresh),
        "method": "Otsu split of the OCR box; WCAG relative-luminance ratio of cluster means",
    }


def attach_geometry(declarations, lines, image_w: Optional[float] = None, image_h: Optional[float] = None) -> None:
    """Populate ``field.geometry`` for net_quantity (clear space + aspect) and mrp (aspect)."""
    nq = getattr(declarations, "net_quantity", None)
    mrp = getattr(declarations, "mrp", None)
    line_boxes = [(l.id, l.bbox) for l in lines if l.bbox]
    text_by_id = {l.id: l.text for l in lines}

    def line_text(field) -> str:
        # the bbox spans the whole OCR line(s); field.raw is only the value part
        ids = list(getattr(field, "source_line_ids", None) or [])
        joined = " ".join(text_by_id[i] for i in ids if i in text_by_id)
        return joined or (field.raw or "")

    if nq is not None and nq.bbox:
        own = set(nq.source_line_ids or [])
        others = [(lid, bb) for lid, bb in line_boxes if lid not in own]
        geo = {"clear_space": clear_space(nq.bbox, others, image_w, image_h)}
        asp = aspect_estimate(line_text(nq), nq.bbox)
        if asp:
            geo["aspect"] = asp
        nq.geometry = geo

    if mrp is not None and mrp.bbox:
        asp = aspect_estimate(line_text(mrp), mrp.bbox)
        if asp:
            mrp.geometry = {"aspect": asp}


def attach_contrast(declarations, image) -> None:
    """Populate ``field.contrast`` for mrp and net_quantity from the OCR image."""
    for fname in ("mrp", "net_quantity"):
        f = getattr(declarations, fname, None)
        if f is not None and f.bbox:
            try:
                f.contrast = contrast_in_box(image, f.bbox)
            except Exception:  # never let a measurement break a scan
                f.contrast = None
