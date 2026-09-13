from typing import Any, Dict, List, Optional, Tuple
from nirikshan.schema import ApplicabilityModel, ContextModel, Declarations


ALL_RULE_IDS = [
    "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09",
    "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R21", "R23",
    "R24", "R25", "R26", "R27", "R28", "R33", "R34", "R35"
]



def resolve_net_quantity_in_g_ml(
    context: ContextModel, declarations: Declarations
) -> Tuple[Optional[float], Optional[str], Optional[float]]:
    """Returns (qty_in_g_ml, unit, raw_value)."""
    val = None
    unit = None

    if context.net_quantity_override:
        val = context.net_quantity_override.get("value")
        unit = context.net_quantity_override.get("unit")
    elif declarations.net_quantity and declarations.net_quantity.value is not None:
        val = declarations.net_quantity.value
        unit = declarations.net_quantity.unit

    if val is None or unit is None:
        return None, unit, val

    raw_val = float(val)
    unit_lower = str(unit).lower()

    if unit_lower in ["g", "gm", "gms", "gram", "grams"]:
        return raw_val, unit, raw_val
    elif unit_lower in ["kg", "kgs"]:
        return raw_val * 1000.0, unit, raw_val
    elif unit_lower in ["ml", "m.l."]:
        return raw_val, unit, raw_val
    elif unit_lower in ["l", "ltr", "lt", "litre", "litres"]:
        return raw_val * 1000.0, unit, raw_val

    return None, unit, raw_val


def resolve(
    context: ContextModel, declarations: Declarations
) -> ApplicabilityModel:
    pkg_type = context.package_type or "retail"
    cat = context.category or "general"
    channel = context.channel or "physical"

    # Infer is_import if not provided
    if context.is_import is not None:
        is_import = context.is_import
    else:
        is_import = declarations.importer is not None

    qty_g_ml, qty_unit, raw_qty_val = resolve_net_quantity_in_g_ml(context, declarations)

    reasons: Dict[str, str] = {}
    applicable_rule_ids: List[str] = list(ALL_RULE_IDS)
    exempt_reason: Optional[str] = None

    # 1. Category == drug (Rule 26(c))
    if cat == "drug":
        exempt_reason = "Rule 26(c): DPCO scheduled formulation"
        for rid in ALL_RULE_IDS:
            reasons[rid] = exempt_reason
        return ApplicabilityModel(
            package_type=pkg_type,
            category=cat,
            is_import=is_import,
            channel=channel,
            exempt_reason=exempt_reason,
            applicable_rule_ids=[],
            reasons=reasons,
        )

    # 2. Rule 26(a): net qty <= 10 g/ml or 10-20 g/ml
    if qty_g_ml is not None:
        if qty_g_ml <= 10.0:
            exempt_reason = "Rule 26(a): package ≤ 10 g/ml exempt"
            for rid in ALL_RULE_IDS:
                reasons[rid] = exempt_reason
            return ApplicabilityModel(
                package_type=pkg_type,
                category=cat,
                is_import=is_import,
                channel=channel,
                exempt_reason=exempt_reason,
                applicable_rule_ids=[],
                reasons=reasons,
            )
        elif 10.0 < qty_g_ml <= 20.0:
            reason_text = "Rule 26(a): 10–20 g/ml packages need only MRP and net quantity"
            applicable_rule_ids = ["R06", "R12"]
            for rid in ALL_RULE_IDS:
                if rid not in applicable_rule_ids:
                    reasons[rid] = reason_text
            return ApplicabilityModel(
                package_type=pkg_type,
                category=cat,
                is_import=is_import,
                channel=channel,
                exempt_reason=None,
                applicable_rule_ids=applicable_rule_ids,
                reasons=reasons,
            )

    # 3. Rule 24: wholesale package
    if pkg_type == "wholesale":
        applicable_rule_ids = ["R27"]
        reason_text = "Rule 24: wholesale package"
        for rid in ALL_RULE_IDS:
            if rid != "R27":
                reasons[rid] = reason_text
        return ApplicabilityModel(
            package_type=pkg_type,
            category=cat,
            is_import=is_import,
            channel=channel,
            exempt_reason=None,
            applicable_rule_ids=applicable_rule_ids,
            reasons=reasons,
        )

    # 4. Rule 3: net qty > 25 kg/L or package_type == not_for_retail
    if (qty_g_ml is not None and qty_g_ml > 25000.0) or pkg_type == "not_for_retail":
        exempt_reason = "Rule 3: excluded from Chapter II"
        for rid in ALL_RULE_IDS:
            reasons[rid] = exempt_reason
        return ApplicabilityModel(
            package_type=pkg_type,
            category=cat,
            is_import=is_import,
            channel=channel,
            exempt_reason=exempt_reason,
            applicable_rule_ids=[],
            reasons=reasons,
        )

    # 5. Retail / standard applicability exclusions
    # R27 is wholesale-only
    if "R27" in applicable_rule_ids:
        applicable_rule_ids.remove("R27")
        reasons["R27"] = "Rule 24: applies only to wholesale packages"

    # Category exemptions
    if cat == "food":
        for rid in ["R01", "R02", "R10"]:
            if rid in applicable_rule_ids:
                applicable_rule_ids.remove(rid)
                reasons[rid] = "Rule 6(1)(a) Explanation III / 6(1)(d) proviso: governed by FSS Act"
    elif cat in ["cosmetic", "seed"]:
        if "R10" in applicable_rule_ids:
            applicable_rule_ids.remove("R10")
            reasons["R10"] = "Drugs & Cosmetics Rules / Seeds Act proviso"
    elif cat == "bidi_incense":
        for rid in ["R10", "R12"]:
            if rid in applicable_rule_ids:
                applicable_rule_ids.remove(rid)
                reasons[rid] = "Category exemption: bidi & incense"
    elif cat == "lpg":
        for rid in ["R10", "R12"]:
            if rid in applicable_rule_ids:
                applicable_rule_ids.remove(rid)
                reasons[rid] = "Category exemption: LPG"
    elif cat == "alcohol":
        if "R12" in applicable_rule_ids:
            applicable_rule_ids.remove("R12")
            reasons["R12"] = "Rule 6(1)(e) proviso: state excise"

    # Import rule R04
    if not is_import:
        if "R04" in applicable_rule_ids:
            applicable_rule_ids.remove("R04")
            reasons["R04"] = "Rule 6(1)(aa): applies only to imported packages"

    # Unit Sale Price R14
    is_exact_base_unit = (
        raw_qty_val == 1.0
        and qty_unit in ["kg", "L", "m", "N", "U", "piece", "pcs", "set", "pair"]
    )
    if pkg_type in ["multi_piece", "combination"] or is_exact_base_unit:
        if "R14" in applicable_rule_ids:
            applicable_rule_ids.remove("R14")
            reasons["R14"] = "Rule 6(11): unit sale price N/A for multi-piece/combination packs or 1 kg/L/m/unit"

    # Best Before R11
    if cat not in ["food", "cosmetic"] and declarations.best_before is None:
        if "R11" in applicable_rule_ids:
            applicable_rule_ids.remove("R11")
            reasons["R11"] = "Rule 6(1)(da): best-before mandatory only for perishable goods or when declared"

    # R28 Combination / Multi-piece components
    if pkg_type not in ["combination", "multi_piece"]:
        if "R28" in applicable_rule_ids:
            applicable_rule_ids.remove("R28")
            reasons["R28"] = "Rule 6(5): applies only to combination or multi-piece packages"

    # R34 Textile / Sheets / Container dimensions declaration
    if cat not in ["textile", "sheets", "container"]:
        if "R34" in applicable_rule_ids:
            applicable_rule_ids.remove("R34")
            reasons["R34"] = "Rules 14–17: applies only to textile, sheets, or container categories"

    return ApplicabilityModel(
        package_type=pkg_type,
        category=cat,
        is_import=is_import,
        channel=channel,
        exempt_reason=None,
        applicable_rule_ids=applicable_rule_ids,
        reasons=reasons,
    )
