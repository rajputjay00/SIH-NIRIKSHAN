from typing import Any, Dict, List, Optional, Tuple
from nirikshan.schema import (
    MRP,
    ConsumerCare,
    DateField,
    Declarations,
    EntityBlock,
    FieldModel,
    NetQuantity,
    SurfaceResultModel,
    UnitSalePrice,
)

PDP_SURFACE_PRIORITY = {"front": 5, "back": 4, "side": 3, "bottom": 2, "crimp": 1, "other": 0}
CRIMP_SURFACE_PRIORITY = {"crimp": 5, "front": 4, "back": 3, "side": 2, "bottom": 1, "other": 0}


def get_surface_priority(surface_name: str, is_date_or_crimp: bool = False) -> int:
    s_lower = (surface_name or "other").lower()
    mapping = CRIMP_SURFACE_PRIORITY if is_date_or_crimp else PDP_SURFACE_PRIORITY
    return mapping.get(s_lower, 0)


def score_candidate(field_obj: Optional[FieldModel], surface_name: str, is_date_or_crimp: bool = False) -> float:
    if not field_obj:
        return -1.0

    has_val = getattr(field_obj, "value", None) is not None or getattr(field_obj, "name", None) is not None
    is_decl_elsewhere = getattr(field_obj, "declared_elsewhere", None) is not None

    if not has_val and not is_decl_elsewhere:
        return -1.0

    score = 0.0
    if has_val:
        score += 1000.0
    elif is_decl_elsewhere:
        score += 100.0

    src = getattr(field_obj, "source", None)
    if src and src not in ["unkeyed", "unparsed"]:
        score += 500.0

    score += get_surface_priority(surface_name, is_date_or_crimp) * 10.0
    conf = getattr(field_obj, "confidence", 0.0) or 0.0
    score += float(conf)

    return score


def merge_declarations(surface_results: List[SurfaceResultModel]) -> Declarations:
    if not surface_results:
        return Declarations()

    if len(surface_results) == 1:
        s0 = surface_results[0]
        decl = s0.declarations.model_copy(deep=True)
        for fname in ["manufacturer", "packer", "importer", "marketer", "country_of_origin", "generic_name", "net_quantity", "mrp", "unit_sale_price", "mfg_date", "best_before", "consumer_care", "gtin"]:
            fval = getattr(decl, fname)
            if fval:
                fval.surface_id = s0.id
                fval.surface = s0.surface
        return decl

    field_names = [
        "manufacturer", "packer", "importer", "marketer",
        "country_of_origin", "generic_name", "net_quantity",
        "mrp", "unit_sale_price", "mfg_date", "best_before",
        "consumer_care", "gtin"
    ]

    merged_kwargs: Dict[str, Any] = {}
    crimp_surface_result = next((s for s in surface_results if (s.surface or "").lower() == "crimp"), None)

    for fname in field_names:
        is_date = fname in ["mfg_date", "best_before"]
        candidates: List[Tuple[float, FieldModel, SurfaceResultModel]] = []
        any_declared_crimp = False

        for sres in surface_results:
            fobj = getattr(sres.declarations, fname, None)
            if fobj:
                if getattr(fobj, "declared_elsewhere", None) in ["crimp", "Crimp"]:
                    any_declared_crimp = True
                sc = score_candidate(fobj, sres.surface, is_date)
                if sc > 0:
                    candidates.append((sc, fobj, sres))

        if not candidates:
            continue

        # Crimp resolution check: declared_elsewhere="crimp" on one surface and found on crimp surface
        crimp_fobj = getattr(crimp_surface_result.declarations, fname, None) if crimp_surface_result else None
        crimp_has_val = crimp_fobj and (getattr(crimp_fobj, "value", None) is not None or getattr(crimp_fobj, "name", None) is not None)

        if (any_declared_crimp or (candidates and getattr(candidates[0][1], "declared_elsewhere", None))) and crimp_has_val:
            merged_field = crimp_fobj.model_copy(deep=True)
            merged_field.declared_elsewhere = None
            merged_field.source = "crimp_resolved"
            merged_field.surface_id = crimp_surface_result.id
            merged_field.surface = crimp_surface_result.surface
        else:
            candidates.sort(key=lambda x: x[0], reverse=True)
            winning_score, winning_obj, winning_surface = candidates[0]
            merged_field = winning_obj.model_copy(deep=True)
            merged_field.surface_id = winning_surface.id
            merged_field.surface = winning_surface.surface

            if (winning_surface.surface or "").lower() == "crimp" and any_declared_crimp and getattr(merged_field, "value", None) is not None:
                merged_field.declared_elsewhere = None
                merged_field.source = "crimp_resolved"

        merged_kwargs[fname] = merged_field

    all_entities = []
    all_mrp_candidates = []
    all_scripts = set()
    all_texts = []
    multi_unit_note = False

    for sres in surface_results:
        decl = sres.declarations
        if decl.entities:
            for e in decl.entities:
                eb = e.model_copy(deep=True)
                eb.surface_id = sres.id
                eb.surface = sres.surface
                all_entities.append(eb)
        if decl.mrp_candidates:
            for c in decl.mrp_candidates:
                c_copy = c.model_copy(deep=True)
                c_copy.surface_id = sres.id
                c_copy.surface = sres.surface
                all_mrp_candidates.append(c_copy)
        if decl.scripts_detected:
            all_scripts.update(decl.scripts_detected)
        if decl.all_text:
            all_texts.append(decl.all_text)
        if decl.multi_unit_note:
            multi_unit_note = True

    merged_kwargs["entities"] = all_entities
    merged_kwargs["mrp_candidates"] = all_mrp_candidates
    merged_kwargs["scripts_detected"] = list(all_scripts)
    merged_kwargs["multi_unit_note"] = multi_unit_note
    merged_kwargs["all_text"] = "\n".join(all_texts) if all_texts else None

    return Declarations(**merged_kwargs)
