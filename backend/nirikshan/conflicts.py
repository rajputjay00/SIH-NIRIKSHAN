from typing import Any, Dict, List, Optional
from rapidfuzz import fuzz

from nirikshan.schema import ConflictModel, ConflictSurfaceModel, SurfaceResultModel


def detect_conflicts(surface_results: List[SurfaceResultModel]) -> List[ConflictModel]:
    if len(surface_results) < 2:
        return []

    conflicts: List[ConflictModel] = []

    # 1. MRP Conflict (value differs > ₹0.01)
    mrp_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        mrp = sres.declarations.mrp
        if mrp and mrp.value is not None:
            mrp_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value=round(float(mrp.value), 2),
                    bbox=mrp.bbox,
                )
            )

    if len(mrp_surfaces) >= 2:
        vals = set(s.value for s in mrp_surfaces)
        if len(vals) > 1:
            conflicts.append(
                ConflictModel(
                    field="mrp",
                    surfaces=mrp_surfaces,
                    severity="high",
                )
            )

    # 2. Net Quantity Conflict (value/unit differ after normalization)
    nq_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        nq = sres.declarations.net_quantity
        if nq and nq.value is not None and nq.unit:
            u_lower = str(nq.unit).lower()
            val_base = float(nq.value)
            if u_lower in ["kg", "l", "ltr"]:
                val_base = val_base * 1000.0
            nq_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value={"raw_val": nq.value, "unit": nq.unit, "base_g_ml": round(val_base, 2)},
                    bbox=nq.bbox,
                )
            )

    if len(nq_surfaces) >= 2:
        base_vals = set(s.value["base_g_ml"] for s in nq_surfaces)
        units = set(str(s.value["unit"]).lower() for s in nq_surfaces)
        # conflict if base values differ or units mismatch (e.g. g vs ml or kg vs g)
        if len(base_vals) > 1 or (len(units) > 1 and not ({"g", "kg"}.issuperset(units) or {"ml", "l", "ltr"}.issuperset(units))):
            conflicts.append(
                ConflictModel(
                    field="net_quantity",
                    surfaces=nq_surfaces,
                    severity="medium",
                )
            )

    # 3. Manufacturing Date Conflict
    date_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        d = sres.declarations.mfg_date
        if d and (d.month is not None or d.year is not None):
            date_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value={"month": d.month, "year": d.year},
                    bbox=d.bbox,
                )
            )

    if len(date_surfaces) >= 2:
        dates_set = set((s.value["month"], s.value["year"]) for s in date_surfaces)
        if len(dates_set) > 1:
            conflicts.append(
                ConflictModel(
                    field="mfg_date",
                    surfaces=date_surfaces,
                    severity="medium",
                )
            )

    # Best Before Date Conflict
    bb_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        d = sres.declarations.best_before
        if d and (d.month is not None or d.year is not None):
            bb_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value={"month": d.month, "year": d.year},
                    bbox=d.bbox,
                )
            )

    if len(bb_surfaces) >= 2:
        dates_set = set((s.value["month"], s.value["year"]) for s in bb_surfaces)
        if len(dates_set) > 1:
            conflicts.append(
                ConflictModel(
                    field="best_before",
                    surfaces=bb_surfaces,
                    severity="medium",
                )
            )

    # 4. Primary Entity / Manufacturer Conflict (similarity < 0.8)
    entity_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        pe = sres.declarations.primary_entity
        if pe and (pe.name or pe.value):
            name_str = (pe.name or pe.value or "").strip()
            entity_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value=name_str,
                    bbox=pe.bbox,
                )
            )

    if len(entity_surfaces) >= 2:
        names = [s.value for s in entity_surfaces]
        has_mismatch = False
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                sim = fuzz.token_sort_ratio(names[i].lower(), names[j].lower()) / 100.0
                if sim < 0.8:
                    has_mismatch = True
                    break
            if has_mismatch:
                break

        if has_mismatch:
            conflicts.append(
                ConflictModel(
                    field="primary_entity",
                    surfaces=entity_surfaces,
                    severity="medium",
                )
            )

    # 5. Country of Origin Conflict
    coo_surfaces: List[ConflictSurfaceModel] = []
    for sres in surface_results:
        coo = sres.declarations.country_of_origin
        if coo and coo.value:
            val_str = str(coo.value).strip().lower()
            coo_surfaces.append(
                ConflictSurfaceModel(
                    id=sres.id,
                    surface=sres.surface,
                    value=str(coo.value).strip(),
                    bbox=coo.bbox,
                )
            )

    if len(coo_surfaces) >= 2:
        vals = set(s.value.lower() for s in coo_surfaces)
        if len(vals) > 1:
            conflicts.append(
                ConflictModel(
                    field="country_of_origin",
                    surfaces=coo_surfaces,
                    severity="high",
                )
            )

    return conflicts
