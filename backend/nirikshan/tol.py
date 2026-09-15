"""Tol (तोल) — net quantity, maximum permissible error and lot inspection.

Deterministic arithmetic for:

* R31 — Rule 22 read with the First Schedule: is the measured net content of a
  single package short of the declared quantity by more than the maximum
  permissible error (MPE)?
* R32 — Rules 19–21 read with the Fifth, Sixth and Seventh Schedules: lot
  sampling, tare determination, corrected average and approval criteria,
  plus the data needed to print Form A (weight) / Form B (volume, length).

Everything here is pure Python and unit-agnostic: quantities are converted
to a base unit (g, ml, cm, cm² or count) before any comparison.

Statutory constants that the team still has to confirm against the Gazette
text (PRD §16 open question 3) are collected in ``LOT_CRITERIA`` and
``SAMPLE_CORRECTION_FACTOR`` and are echoed back in every result under
``criteria`` so an officer can see exactly which numbers were applied.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------

# base unit per family; factor converts the declared unit into the base unit
UNIT_FAMILY: Dict[str, Tuple[str, str, float]] = {
    # unit: (family, base_unit, factor_to_base)
    "g": ("weight", "g", 1.0),
    "kg": ("weight", "g", 1000.0),
    "mg": ("weight", "g", 0.001),
    "ml": ("volume", "ml", 1.0),
    "l": ("volume", "ml", 1000.0),
    "cl": ("volume", "ml", 10.0),
    "mm": ("length", "cm", 0.1),
    "cm": ("length", "cm", 1.0),
    "m": ("length", "cm", 100.0),
    "cm2": ("area", "cm2", 1.0),
    "m2": ("area", "cm2", 10000.0),
    "n": ("number", "N", 1.0),
    "u": ("number", "N", 1.0),
    "piece": ("number", "N", 1.0),
    "pieces": ("number", "N", 1.0),
    "pcs": ("number", "N", 1.0),
    "pair": ("number", "N", 1.0),
    "set": ("number", "N", 1.0),
}

FORM_FOR_FAMILY = {"weight": "A", "volume": "B", "length": "B", "area": "B", "number": "B"}


def normalise_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    u = str(unit).strip().lower().replace("²", "2").replace(".", "")
    aliases = {
        "gm": "g", "gms": "g", "gram": "g", "grams": "g",
        "kgs": "kg", "ltr": "l", "lt": "l", "litre": "l", "litres": "l", "liter": "l",
        "mtr": "m", "metre": "m", "meter": "m", "metres": "m", "meters": "m",
        "sqcm": "cm2", "sq cm": "cm2", "sqm": "m2", "sq m": "m2",
        "nos": "n", "no": "n", "unit": "u", "units": "u", "pc": "piece",
    }
    u = aliases.get(u, u)
    return u if u in UNIT_FAMILY else None


def to_base(value: float, unit: str) -> Tuple[float, str, str]:
    """Return (value_in_base_unit, base_unit, family)."""
    u = normalise_unit(unit)
    if u is None:
        raise ValueError(f"Unsupported unit for MPE: {unit!r}")
    family, base, factor = UNIT_FAMILY[u]
    return float(value) * factor, base, family


# --------------------------------------------------------------------------
# First Schedule — maximum permissible error
# --------------------------------------------------------------------------

# Table I: by weight or volume. (upper_bound_inclusive_g_or_ml, pct, abs)
# One of pct / abs is None. Source: LMPC Rules 2011, First Schedule, Table I
# as transcribed in docs/Nirikshan_PRD_SIH26034.md Appendix A.2.
MPE_TABLE_I: List[Tuple[float, Optional[float], Optional[float]]] = [
    (50.0, 9.0, None),
    (100.0, None, 4.5),
    (200.0, 4.5, None),
    (300.0, None, 9.0),
    (500.0, 3.0, None),
    (1000.0, None, 15.0),
    (10000.0, 1.5, None),
    (15000.0, None, 150.0),
    (math.inf, 1.0, None),
]

# Table II: by length, area and number (percentages). PRD Appendix A.3.
MPE_TABLE_II: Dict[str, List[Tuple[float, float]]] = {
    # family: [(upper_bound_inclusive_in_base_unit, pct)]
    "length": [(1000.0, 2.0), (math.inf, 1.0)],      # ≤ 10 m → 2 %, above → 1 %
    "area": [(100000.0, 4.0), (math.inf, 1.0)],       # ≤ 10 m² → 4 %, above → 1 %
    "number": [(math.inf, 2.0)],
}


def _round_mpe(mpe: float, declared_base: float) -> float:
    """First Schedule rounding: percentages are rounded to 0.1 g/ml up to
    1000 g/ml and to the next whole g/ml above 1000 g/ml."""
    if declared_base <= 1000.0:
        return round(mpe + 1e-9, 1)
    return float(math.ceil(mpe - 1e-9))


def mpe_for(declared_value: float, unit: str) -> Dict[str, Any]:
    """Maximum permissible error for a declared quantity.

    Returns a dict with the MPE in the base unit, the band used and the
    schedule table it came from.
    """
    if declared_value is None or float(declared_value) <= 0:
        raise ValueError("Declared quantity must be > 0")
    base_val, base_unit, family = to_base(declared_value, unit)

    if family in ("weight", "volume"):
        for upper, pct, abs_ in MPE_TABLE_I:
            if base_val <= upper:
                if pct is not None:
                    raw = base_val * pct / 100.0
                    mpe = _round_mpe(raw, base_val)
                    band = f"{pct}%"
                else:
                    mpe = float(abs_)
                    band = f"{abs_} {base_unit}"
                return {
                    "table": "First Schedule Table I",
                    "family": family,
                    "declared_base": base_val,
                    "base_unit": base_unit,
                    "mpe_base": mpe,
                    "mpe_pct_of_declared": round(mpe / base_val * 100.0, 3),
                    "band": band,
                }
    else:
        for upper, pct in MPE_TABLE_II[family]:
            if base_val <= upper:
                raw = base_val * pct / 100.0
                # count MPE cannot be fractional — round up to the next whole unit
                mpe = float(math.ceil(raw - 1e-9)) if family == "number" else round(raw, 3)
                return {
                    "table": "First Schedule Table II",
                    "family": family,
                    "declared_base": base_val,
                    "base_unit": base_unit,
                    "mpe_base": mpe,
                    "mpe_pct_of_declared": round(mpe / base_val * 100.0, 3),
                    "band": f"{pct}%",
                }
    raise ValueError("MPE band not found")  # pragma: no cover


# --------------------------------------------------------------------------
# R31 — single package
# --------------------------------------------------------------------------

def check_single_pack(
    declared_value: float,
    unit: str,
    gross: Optional[float] = None,
    tare: Optional[float] = None,
    net: Optional[float] = None,
    measured_unit: Optional[str] = None,
    resolution: Optional[float] = None,
) -> Dict[str, Any]:
    """Compare one measured package against the declared quantity.

    ``measured_unit`` defaults to the declared unit. ``resolution`` (scale
    readability, same unit as the measurement) defines the uncertainty band:
    a deficiency within ± resolution of the MPE is reported as ``marginal``
    so the rules engine can return NEEDS_REVIEW instead of a hard verdict.
    """
    m = mpe_for(declared_value, unit)
    mu = measured_unit or unit
    if net is None:
        if gross is None or tare is None:
            raise ValueError("Provide net, or both gross and tare")
        net = float(gross) - float(tare)
    net_base, base_unit, fam = to_base(net, mu)
    if fam != m["family"]:
        raise ValueError(f"Measured unit {mu!r} does not match declared unit {unit!r}")

    res_base = to_base(resolution, mu)[0] if resolution else 0.0
    error = net_base - m["declared_base"]          # negative = short
    deficiency = max(0.0, -error)
    mpe = m["mpe_base"]
    within = deficiency <= mpe + 1e-9
    exceeds_2x = deficiency > 2.0 * mpe + 1e-9
    marginal = res_base > 0 and abs(deficiency - mpe) <= res_base

    if within:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    if marginal:
        verdict = "NEEDS_REVIEW"

    bu = base_unit
    summary = (
        f"declared {m['declared_base']:g} {bu}; measured {net_base:g} {bu}; "
        f"error {error:+.1f} {bu}; MPE {mpe:g} {bu} ({m['band']})"
    )
    if exceeds_2x:
        summary += "; exceeds 2×MPE (aggravated)"
    if marginal:
        summary += f"; within scale resolution ±{res_base:g} {bu} of the MPE limit — confirm on a verified balance"

    return {
        "rule_id": "R31",
        "verdict": verdict,
        "declared_value": float(declared_value),
        "declared_unit": unit,
        "declared_base": m["declared_base"],
        "base_unit": bu,
        "gross": gross,
        "tare": tare,
        "net": float(net),
        "net_base": net_base,
        "error_base": round(error, 4),
        "deficiency_base": round(deficiency, 4),
        "mpe_base": mpe,
        "mpe_band": m["band"],
        "mpe_table": m["table"],
        "within_mpe": within,
        "exceeds_2x_mpe": exceeds_2x,
        "marginal": marginal,
        "resolution_base": res_base,
        "summary": summary,
    }


# --------------------------------------------------------------------------
# R32 — lot inspection (Fifth, Sixth, Seventh Schedules)
# --------------------------------------------------------------------------

# Fifth Schedule: sample size by lot size and the number of packages in the
# sample that may fall below (declared − MPE) — "T1 errors". No package may
# fall below (declared − 2×MPE) — "T2 errors".
#
# TODO(confirm): column 4 of the Fifth Schedule (allowed T1 count) is an image
# in most online copies of G.S.R. 629(E); the values below follow OIML R 87.
# Change here only — every result echoes the values used under "criteria".
LOT_CRITERIA: Dict[int, Dict[str, Any]] = {
    32: {"allowed_t1": 2, "allowed_t2": 0},
    80: {"allowed_t1": 5, "allowed_t2": 0},
}
LOT_SIZE_THRESHOLD = 4000  # lots up to this size → 32 samples, larger → 80

# Sixth Schedule para 10 — sample correction factor t(0.995, n−1) / √n.
# TODO(confirm): formula transcribed from OIML R 87 §4.2.2; verify against the
# Gazette text of Sixth Schedule para 10.
SAMPLE_CORRECTION_FACTOR: Dict[int, float] = {32: 0.485, 80: 0.295}

# Sixth Schedule para 3 — tare determination (as encoded in PRD §6.4 FR-T3)
SINGLE_TARE_MAX_FRACTION_OF_MPE = 0.3
TARE_SPREAD_MAX_FRACTION_OF_MPE = 0.4
MIN_TARES_FOR_AVERAGE = 5


def sample_size_for(lot_size: int) -> int:
    if lot_size is None or int(lot_size) <= 0:
        raise ValueError("Lot size must be a positive integer")
    return 32 if int(lot_size) <= LOT_SIZE_THRESHOLD else 80


def _t_over_sqrt_n(n: int) -> float:
    """Sample correction factor. Tabulated for the statutory sample sizes;
    approximated for other n via a Cornish–Fisher expansion of t(0.995)."""
    if n in SAMPLE_CORRECTION_FACTOR:
        return SAMPLE_CORRECTION_FACTOR[n]
    df = max(1, n - 1)
    z = 2.5758293  # 0.995 quantile of the standard normal
    t = z + (z ** 3 + z) / (4 * df) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2)
    return round(t / math.sqrt(n), 4)


def determine_tare(tares: List[float], mpe_base: float) -> Dict[str, Any]:
    """Sixth Schedule para 3 tare procedure.

    * one tare reading is acceptable if it is ≤ 0.3 × MPE;
    * otherwise at least five tares are needed and their average may be used
      only if the spread (max − min) is ≤ 0.4 × MPE;
    * otherwise each sample must be weighed with its own tare.
    """
    vals = [float(t) for t in (tares or []) if t is not None]
    if not vals:
        return {"method": "none", "tare": None, "ok": False,
                "note": "No tare provided — enter tare(s) or per-sample net contents."}
    if len(vals) == 1:
        t = vals[0]
        if t <= SINGLE_TARE_MAX_FRACTION_OF_MPE * mpe_base + 1e-9:
            return {"method": "single", "tare": t, "ok": True,
                    "note": f"Single tare {t:g} ≤ 0.3 × MPE ({0.3 * mpe_base:g}) — acceptable."}
        return {"method": "single", "tare": t, "ok": False,
                "note": f"Single tare {t:g} exceeds 0.3 × MPE ({0.3 * mpe_base:g}); weigh at least {MIN_TARES_FOR_AVERAGE} tares."}
    if len(vals) < MIN_TARES_FOR_AVERAGE:
        return {"method": "average", "tare": statistics.fmean(vals), "ok": False,
                "note": f"Only {len(vals)} tares; Sixth Schedule needs {MIN_TARES_FOR_AVERAGE} for an average tare."}
    spread = max(vals) - min(vals)
    avg = statistics.fmean(vals)
    if spread <= TARE_SPREAD_MAX_FRACTION_OF_MPE * mpe_base + 1e-9:
        return {"method": "average", "tare": avg, "ok": True, "spread": spread,
                "note": f"Average of {len(vals)} tares = {avg:g}; spread {spread:g} ≤ 0.4 × MPE ({0.4 * mpe_base:g})."}
    return {"method": "average", "tare": avg, "ok": False, "spread": spread,
            "note": f"Tare spread {spread:g} exceeds 0.4 × MPE ({0.4 * mpe_base:g}); weigh each sample with its own tare."}


def lot_inspection(
    lot_size: int,
    declared_value: float,
    unit: str,
    samples: List[Dict[str, Any]],
    tares: Optional[List[float]] = None,
    measured_unit: Optional[str] = None,
) -> Dict[str, Any]:
    """Rule 19–21 lot procedure.

    ``samples`` is a list of dicts with ``gross`` and optionally ``tare`` or
    ``net``. When a sample has no tare of its own the lot tare from
    ``tares`` (Sixth Schedule para 3) is used.
    """
    m = mpe_for(declared_value, unit)
    mu = measured_unit or unit
    n_required = sample_size_for(lot_size)
    mpe = m["mpe_base"]
    declared_base = m["declared_base"]
    bu = m["base_unit"]
    notes: List[str] = []

    tare_info = determine_tare(tares or [], mpe)
    lot_tare_base = to_base(tare_info["tare"], mu)[0] if tare_info["tare"] is not None else None

    rows: List[Dict[str, Any]] = []
    missing_tare = 0
    for i, s in enumerate(samples or [], start=1):
        gross = s.get("gross")
        tare = s.get("tare")
        net = s.get("net")
        if net is None:
            if gross is None:
                raise ValueError(f"Sample {i}: provide gross or net")
            if tare is None:
                if lot_tare_base is None or not tare_info["ok"]:
                    missing_tare += 1
                    tare_base = None
                else:
                    tare_base = lot_tare_base
            else:
                tare_base = to_base(tare, mu)[0]
            gross_base = to_base(gross, mu)[0]
            net_base = gross_base - tare_base if tare_base is not None else None
        else:
            gross_base = to_base(gross, mu)[0] if gross is not None else None
            tare_base = to_base(tare, mu)[0] if tare is not None else None
            net_base = to_base(net, mu)[0]

        if net_base is None:
            rows.append({"sno": i, "gross": gross_base, "tare": None, "net": None,
                         "error": None, "t1": False, "t2": False})
            continue
        err = net_base - declared_base
        rows.append({
            "sno": i,
            "gross": gross_base,
            "tare": tare_base,
            "net": round(net_base, 4),
            "error": round(err, 4),
            "t1": err < -mpe - 1e-9,
            "t2": err < -2.0 * mpe - 1e-9,
        })

    nets = [r["net"] for r in rows if r["net"] is not None]
    n = len(nets)
    status = "APPROVED"
    reasons: List[str] = []

    if missing_tare:
        notes.append(tare_info["note"])
        notes.append(f"{missing_tare} sample(s) have no usable tare — net content not computed.")
    if n < n_required:
        notes.append(f"Sample size {n} is below the Fifth Schedule requirement of {n_required} for a lot of {lot_size}.")

    criteria = LOT_CRITERIA.get(n_required, {"allowed_t1": 0, "allowed_t2": 0})
    scf = _t_over_sqrt_n(n) if n >= 2 else None

    if n >= 2:
        mean = statistics.fmean(nets)
        sd = statistics.stdev(nets)
        corrected_avg = mean + scf * sd
    elif n == 1:
        mean, sd, corrected_avg = nets[0], 0.0, nets[0]
    else:
        mean = sd = corrected_avg = None

    t1_count = sum(1 for r in rows if r["t1"])
    t2_count = sum(1 for r in rows if r["t2"])

    if n == 0:
        status = "INCOMPLETE"
        reasons.append("No sample net contents available.")
    else:
        if corrected_avg is not None and corrected_avg < declared_base - 1e-9:
            status = "REJECTED"
            reasons.append(
                f"Corrected average {corrected_avg:.3f} {bu} is below the declared quantity {declared_base:g} {bu} (Rule 19(6)(a))."
            )
        if t1_count > criteria["allowed_t1"]:
            status = "REJECTED"
            reasons.append(
                f"{t1_count} package(s) below declared − MPE; Fifth Schedule allows {criteria['allowed_t1']} for a sample of {n_required}."
            )
        if t2_count > criteria["allowed_t2"]:
            status = "REJECTED"
            reasons.append(f"{t2_count} package(s) below declared − 2×MPE; none permitted.")
        if status == "APPROVED" and (n < n_required or missing_tare):
            status = "INCOMPLETE"
            reasons.append("Criteria met on the packages weighed so far, but the sample is incomplete.")

    return {
        "rule_id": "R32",
        "status": status,                       # APPROVED | REJECTED | INCOMPLETE
        "form": FORM_FOR_FAMILY[m["family"]],  # Seventh Schedule Form A or B
        "lot_size": int(lot_size),
        "sample_size_required": n_required,
        "sample_size_weighed": n,
        "declared_value": float(declared_value),
        "declared_unit": unit,
        "declared_base": declared_base,
        "base_unit": bu,
        "mpe_base": mpe,
        "mpe_band": m["band"],
        "tare": tare_info,
        "samples": rows,
        "mean": round(mean, 4) if mean is not None else None,
        "sd": round(sd, 4) if sd is not None else None,
        "sample_correction_factor": scf,
        "corrected_average": round(corrected_avg, 4) if corrected_avg is not None else None,
        "t1_count": t1_count,
        "t2_count": t2_count,
        "criteria": {
            "corrected_average_min": declared_base,
            "allowed_t1": criteria["allowed_t1"],
            "allowed_t2": criteria["allowed_t2"],
            "t1_threshold": round(declared_base - mpe, 4),
            "t2_threshold": round(declared_base - 2.0 * mpe, 4),
            "formula": "corrected_average = mean + (t(0.995, n-1) / sqrt(n)) × s",
            "source": "Fifth & Sixth Schedules (values to be confirmed against G.S.R. 629(E))",
        },
        "reasons": reasons,
        "notes": notes,
        "summary": _lot_summary(status, n, n_required, mean, corrected_avg, declared_base, bu, t1_count, t2_count),
    }


def _lot_summary(status, n, n_req, mean, corrected, declared, bu, t1, t2) -> str:
    if mean is None:
        return f"Lot {status.lower()}: no measurements"
    return (
        f"Lot {status.lower()}: n={n}/{n_req}, mean {mean:.2f} {bu}, corrected average {corrected:.2f} {bu} "
        f"vs declared {declared:g} {bu}, T1={t1}, T2={t2}"
    )
