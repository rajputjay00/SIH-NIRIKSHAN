import io
import json
import asyncio
import importlib.metadata
import os
import subprocess
import logging
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from PIL import Image, ImageDraw, ImageFont

import ocr

logger = logging.getLogger("nirikshan.main")
MODEL_LOADED = False

try:
    MODEL_VERSION = f"rapidocr_{importlib.metadata.version('rapidocr_onnxruntime')}"
except Exception:
    MODEL_VERSION = "rapidocr_1.4.4"


def get_git_sha() -> str:
    sha = os.getenv("GIT_SHA")
    if sha:
        return sha
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "dev"


GIT_SHA = get_git_sha()


def create_warmup_image(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        font = ImageFont.truetype(font_path, 32)
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            raise RuntimeError("Neither DejaVuSans font nor load_default could be loaded")

    draw.text((50, 50), "NET QUANTITY: 1 kg", fill=(0, 0, 0), font=font)
    draw.text((50, 100), "MRP Rs. 150.00 INCL. OF ALL TAXES", fill=(0, 0, 0), font=font)
    draw.text((50, 150), "MFD BY: NIRIKSHAN LABS PVT LTD", fill=(0, 0, 0), font=font)
    return img


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL_LOADED
    try:
        # Warm up with both large (1600x1200) and standard (600x400) images
        res1 = ocr.extract_text(create_warmup_image(1600, 1200))
        res2 = ocr.extract_text(create_warmup_image(600, 400))
        if res1.get("lines") and res2.get("lines"):
            MODEL_LOADED = True
            logger.info("OCR model warmed up successfully")
        else:
            MODEL_LOADED = False
            logger.warning("OCR warm-up did not return any text lines")
    except Exception as e:
        MODEL_LOADED = False
        logger.warning(f"Failed to warm up OCR model: {e}", exc_info=True)
    yield


app = FastAPI(title="Nirikshan API", lifespan=lifespan)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
import time
from fastapi import Form
from nirikshan import EXTRACTOR_VERSION, extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate, load_catalogue
from nirikshan.quality import assess_quality
from nirikshan.schema import ContextModel, SurfaceResultModel, WeighingInput, LotInput
from nirikshan import tol
from nirikshan.geometry import attach_contrast
from nirikshan.nigrani import find_dual_mrp, fetch_listing_html, html_to_lines, lines_to_ocr, listing_presence, font_parity
from nirikshan.report.form_ab import generate_form_pdf
from pydantic import BaseModel, Field
from nirikshan.merge import merge_declarations
from nirikshan.conflicts import detect_conflicts

from nirikshan.version import RULES_VERSION

origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


from nirikshan.session import session_store

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "model_loaded": MODEL_LOADED,
        "model_version": MODEL_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "rules_version": RULES_VERSION,
        "git_sha": GIT_SHA,
    }


@router.get("/rules")
def get_rules_catalogue():
    return {
        "rules_version": RULES_VERSION,
        "rules": load_catalogue(),
    }


@router.post("/session")
def create_session():
    return session_store.create_session()


@router.get("/session/{code}/results")
def get_session_results(code: str):
    results = session_store.get_results(code)
    if results is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return results


@router.get("/session/{code}/stream")
async def stream_session_results(code: str):
    sess = session_store.get_session(code)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    queue = session_store.subscribe(code)
    if not queue:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        try:
            while True:
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(record)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            session_store.unsubscribe(code, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def process_inspection(
    surface_images: List[Tuple[bytes, str, str]],
    context: ContextModel,
    session: Optional[str] = None,
) -> Dict[str, Any]:
    surface_results: List[SurfaceResultModel] = []
    total_preprocess = 0.0
    total_ocr = 0.0
    total_extract = 0.0

    for idx, (contents, fname, surface_name) in enumerate(surface_images, start=1):
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {fname} exceeds maximum allowed limit of 10 MB.",
            )
        try:
            image = Image.open(io.BytesIO(contents))
            image.verify()
            image = Image.open(io.BytesIO(contents))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Invalid or corrupt image file {fname}.",
            )

        w, h = image.size
        ocr_result = ocr.extract_text(image)
        quality_result = assess_quality(image)

        ext_start = time.perf_counter()
        decl_obj = extract(ocr_result.get("lines", []), w, h)
        try:  # R22: contrast in the OCR coordinate space (pre-processed image)
            proc_img, _, _ = ocr.preprocess(image)
            attach_contrast(decl_obj, proc_img)
        except Exception as exc:
            logger.warning(f"contrast measurement skipped: {exc}")
        ext_ms = (time.perf_counter() - ext_start) * 1000.0

        total_preprocess += ocr_result.get("preprocess_ms", 0.0)
        total_ocr += ocr_result.get("ocr_ms", 0.0)
        total_extract += ext_ms

        sres = SurfaceResultModel(
            id=idx,
            surface=surface_name or "front",
            image_size={"width": w, "height": h},
            scale=1.0,
            ocr=ocr_result,
            quality=quality_result,
            declarations=decl_obj,
        )
        surface_results.append(sres)

    merge_start = time.perf_counter()
    merged_declarations = merge_declarations(surface_results)
    conflicts = detect_conflicts(surface_results)
    merge_ms = (time.perf_counter() - merge_start) * 1000.0

    # R17: compare with earlier scans in the same session
    if session and context.dual_mrp is None:
        try:
            context.dual_mrp = find_dual_mrp(merged_declarations, session_store.get_results(session) or [])
        except Exception as exc:
            logger.warning(f"dual-MRP lookup skipped: {exc}")

    applicability_obj = resolve(context, merged_declarations)

    rules_start = time.perf_counter()
    findings_list, summary_obj = evaluate(
        merged_declarations,
        applicability_obj,
        quality=surface_results[0].quality if surface_results else None,
        context=context,
        conflicts=conflicts,
    )
    rules_ms = (time.perf_counter() - rules_start) * 1000.0

    total_elapsed = total_ocr + total_extract + merge_ms + rules_ms

    res = {
        "surfaces": [s.model_dump() for s in surface_results],
        "merged": merged_declarations.model_dump(),
        "conflicts": [c.model_dump() for c in conflicts],
        "applicability": applicability_obj.model_dump(),
        "findings": [f.model_dump() for f in findings_list],
        "summary": summary_obj.model_dump(),
        "rules_version": RULES_VERSION,
        "model_version": MODEL_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "timings": {
            "preprocess_ms": round(total_preprocess, 2),
            "ocr_ms": round(total_ocr, 2),
            "extract_ms": round(total_extract, 2),
            "merge_ms": round(merge_ms, 2),
            "rules_ms": round(rules_ms, 2),
            "elapsed_ms": round(total_elapsed, 2),
        },
    }

    if session and surface_images:
        session_store.add_scan_result(session, res, surface_images[0][0])

    return res


@router.post("/inspect")
async def inspect_images(
    request: Request,
    package_type: Optional[str] = Form("retail"),
    category: Optional[str] = Form("general"),
    is_import: Optional[bool] = Form(None),
    channel: Optional[str] = Form("physical"),
    net_quantity_value: Optional[float] = Form(None),
    net_quantity_unit: Optional[str] = Form(None),
    session: Optional[str] = Form(None),
    weighing: Optional[str] = Form(None),
    lot: Optional[str] = Form(None),
    geometry_checks: Optional[bool] = Form(False),
):
    form = await request.form()
    surface_images: List[Tuple[bytes, str, str]] = []

    # Check index 1..6 for file_i / image_i and surface_i
    for i in range(1, 7):
        file_obj = form.get(f"file_{i}") or form.get(f"image_{i}") or form.get(f"file{i}")
        surf_val = form.get(f"surface_{i}") or form.get(f"surface{i}")
        if file_obj and hasattr(file_obj, "read"):
            contents = await file_obj.read()
            if contents:
                surf_name = str(surf_val) if surf_val else ("front" if i == 1 else "other")
                surface_images.append((contents, getattr(file_obj, "filename", f"image_{i}.jpg"), surf_name))

    if not surface_images:
        # Fallback: iterate over all UploadFile items in form
        i = 1
        for k, v in form.items():
            if hasattr(v, "read") and hasattr(v, "filename") and v.filename:
                contents = await v.read()
                if contents:
                    surf_val = form.get(f"surface_{i}") or form.get("surface") or ("front" if i == 1 else "other")
                    surface_images.append((contents, v.filename, str(surf_val)))
                    i += 1
                    if len(surface_images) >= 6:
                        break

    if not surface_images:
        raise HTTPException(status_code=400, detail="At least 1 image file must be uploaded.")

    net_qty_override = None
    if net_quantity_value is not None and net_quantity_unit is not None:
        net_qty_override = {"value": net_quantity_value, "unit": net_quantity_unit}

    context = ContextModel(
        package_type=package_type or "retail",
        category=category or "general",
        is_import=is_import,
        channel=channel or "physical",
        net_quantity_override=net_qty_override,
        weighing=_parse_json_field(weighing, WeighingInput, "weighing"),
        lot=_parse_json_field(lot, LotInput, "lot"),
        geometry_checks=bool(geometry_checks),
    )

    return await process_inspection(surface_images, context, session)


@router.post("/scan")
async def scan_image(
    file: UploadFile = File(...),
    package_type: Optional[str] = Form("retail"),
    category: Optional[str] = Form("general"),
    is_import: Optional[bool] = Form(None),
    channel: Optional[str] = Form("physical"),
    net_quantity_value: Optional[float] = Form(None),
    net_quantity_unit: Optional[str] = Form(None),
    session: Optional[str] = Form(None),
    weighing: Optional[str] = Form(None),
    lot: Optional[str] = Form(None),
    geometry_checks: Optional[bool] = Form(False),
):
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format. Allowed formats: JPEG, PNG, WebP.",
        )

    contents = await file.read()
    net_qty_override = None
    if net_quantity_value is not None and net_quantity_unit is not None:
        net_qty_override = {"value": net_quantity_value, "unit": net_quantity_unit}

    context = ContextModel(
        package_type=package_type or "retail",
        category=category or "general",
        is_import=is_import,
        channel=channel or "physical",
        net_quantity_override=net_qty_override,
        weighing=_parse_json_field(weighing, WeighingInput, "weighing"),
        lot=_parse_json_field(lot, LotInput, "lot"),
        geometry_checks=bool(geometry_checks),
    )

    inspect_res = await process_inspection([(contents, file.filename or "image.jpg", "front")], context, session)

    s0 = inspect_res["surfaces"][0]
    res = {
        "filename": file.filename,
        "width": s0["image_size"]["width"],
        "height": s0["image_size"]["height"],
        "ocr": s0["ocr"],
        "quality": s0["quality"],
        "declarations": inspect_res["merged"],
        "applicability": inspect_res["applicability"],
        "findings": inspect_res["findings"],
        "summary": inspect_res["summary"],
        "rules_version": inspect_res["rules_version"],
        "model_version": inspect_res["model_version"],
        "extractor_version": inspect_res["extractor_version"],
        "timings": inspect_res["timings"],
    }
    return res




def _parse_json_field(raw: Optional[str], model, name: str):
    """Parse an optional JSON-encoded multipart field into a pydantic model."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return model.model_validate(json.loads(raw))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid '{name}' JSON: {exc}")


# ---------------------------------------------------------------------------
# Tol — net quantity (R31) and lot inspection (R32), Rules 19–22 + Schedules
# ---------------------------------------------------------------------------

class WeighRequest(BaseModel):
    declared_value: float
    declared_unit: str
    gross: Optional[float] = None
    tare: Optional[float] = None
    net: Optional[float] = None
    unit: Optional[str] = None          # unit of the readings; defaults to declared_unit
    resolution: Optional[float] = None  # scale readability in the reading unit


class LotRequest(LotInput):
    declared_value: float
    declared_unit: str


class LotFormRequest(LotRequest):
    officer: Optional[str] = None
    premises: Optional[str] = None
    packer: Optional[str] = None
    commodity: Optional[str] = None
    lot_id: Optional[str] = None
    instrument: Optional[str] = None
    date: Optional[str] = None
    remarks: Optional[str] = None
    language: Optional[str] = "en"


def _finding_from_tol(rule_id: str, verdict: str, extracted: str, message_en: str, message_hi: str) -> Dict[str, Any]:
    rule = next((r for r in load_catalogue() if r["id"] == rule_id), {})
    return {
        "rule_id": rule_id,
        "rule_ref": rule.get("rule_ref", ""),
        "verdict": verdict,
        "severity": rule.get("severity", "high"),
        "extracted": extracted,
        "expected": extracted,
        "evidence_bbox": None,
        "evidence_refs": [],
        "message_en": message_en,
        "message_hi": message_hi,
        "fix_hint_en": rule.get("fix_hint_en") if verdict == "FAIL" else None,
        "trail": [
            {"step": "input", "detail": "Officer-entered measurement (Tol)"},
            {"step": "predicate_check", "detail": extracted},
            {"step": "verdict", "detail": f"Final verdict {verdict}: {message_en}"},
        ],
    }


@router.get("/tol/mpe")
def get_mpe(declared_value: float, unit: str):
    """First Schedule maximum permissible error for a declared quantity."""
    try:
        return tol.mpe_for(declared_value, unit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/tol/weigh")
def weigh_single_pack(req: WeighRequest):
    """R31: compare one weighed package with its declared quantity."""
    try:
        res = tol.check_single_pack(
            declared_value=req.declared_value, unit=req.declared_unit,
            gross=req.gross, tare=req.tare, net=req.net,
            measured_unit=req.unit, resolution=req.resolution,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rule = next((r for r in load_catalogue() if r["id"] == "R31"), {})
    if res["verdict"] == "PASS":
        msg_en, msg_hi = f"Compliant: {rule.get('title_en', '')}", f"अनुपालन: {rule.get('title_hi', '')}"
    elif res["verdict"] == "NEEDS_REVIEW":
        msg_en = "Deficiency is within the scale resolution of the MPE limit — confirm on a verified balance before recording a verdict."
        msg_hi = "कमी MPE सीमा के तराजू-रिज़ॉल्यूशन के भीतर है — निर्णय दर्ज करने से पहले सत्यापित तराजू पर पुष्टि करें।"
    else:
        msg_en, msg_hi = rule.get("message_en", ""), rule.get("message_hi", "")
    res["finding"] = _finding_from_tol("R31", res["verdict"], res["summary"], msg_en, msg_hi)
    res["rules_version"] = RULES_VERSION
    return res


@router.post("/tol/lot")
def inspect_lot(req: LotRequest):
    """R32: Rule 19–21 lot inspection (sample size, tare, corrected average, criteria)."""
    try:
        res = tol.lot_inspection(
            lot_size=req.lot_size, declared_value=req.declared_value, unit=req.declared_unit,
            samples=[s.model_dump() for s in req.samples], tares=list(req.tares or []),
            measured_unit=req.unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    rule = next((r for r in load_catalogue() if r["id"] == "R32"), {})
    verdict = {"APPROVED": "PASS", "REJECTED": "FAIL", "INCOMPLETE": "NEEDS_REVIEW"}[res["status"]]
    if verdict == "PASS":
        msg_en, msg_hi = f"Compliant: {rule.get('title_en', '')}", f"अनुपालन: {rule.get('title_hi', '')}"
    elif verdict == "FAIL":
        msg_en = "Lot rejected under Rule 19(6): corrected average below the declared quantity or too many packages beyond the permissible error."
        msg_hi = "नियम 19(6) के अंतर्गत लॉट अस्वीकृत: संशोधित औसत घोषित मात्रा से कम है या अनुमेय त्रुटि से अधिक पैकेज हैं।"
    else:
        msg_en = "Lot inspection incomplete — weigh the full Fifth Schedule sample with a valid tare determination before recording a verdict."
        msg_hi = "लॉट निरीक्षण अधूरा — निर्णय दर्ज करने से पहले वैध टेयर निर्धारण के साथ पाँचवीं अनुसूची का पूरा नमूना तोलें।"
    res["finding"] = _finding_from_tol("R32", verdict, res["summary"], msg_en, msg_hi)
    res["rules_version"] = RULES_VERSION
    return res


@router.post("/tol/lot/form")
def lot_form_pdf(req: LotFormRequest):
    """Seventh Schedule Form A (weight) / Form B (volume, length, number) as PDF."""
    try:
        res = tol.lot_inspection(
            lot_size=req.lot_size, declared_value=req.declared_value, unit=req.declared_unit,
            samples=[s.model_dump() for s in req.samples], tares=list(req.tares or []),
            measured_unit=req.unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    meta = {
        "officer": req.officer, "premises": req.premises, "packer": req.packer,
        "commodity": req.commodity, "lot_id": req.lot_id, "instrument": req.instrument,
        "date": req.date, "remarks": req.remarks,
    }
    try:
        pdf_bytes = generate_form_pdf(res, meta=meta, rules_version=RULES_VERSION, language=req.language or "en")
    except Exception as e:
        logger.error(f"Failed to generate Form {res.get('form')} PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Form generation error: {str(e)}")

    filename = f"Nirikshan_Form_{res['form']}_{int(time.time())}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


# ---------------------------------------------------------------------------
# Jaal — e-commerce listing mode (R29 Rule 6(10), R30 Rule 31)
# ---------------------------------------------------------------------------

@router.post("/listing/check")
async def check_listing(
    request: Request,
    url: Optional[str] = Form(None),
    is_import: Optional[bool] = Form(None),
    fetch: Optional[bool] = Form(True),
):
    """Check a marketplace listing: page text (fetched server-side from ``url``)
    and/or listing screenshots uploaded as file_1..file_6."""
    form = await request.form()
    surface_results: List[SurfaceResultModel] = []
    sources: List[str] = []
    idx = 0

    if url and fetch:
        try:
            html = await asyncio.to_thread(fetch_listing_html, url)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not fetch listing: {exc}")
        texts = html_to_lines(html)
        if not texts:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No readable text on the listing page")
        idx += 1
        lines = lines_to_ocr(texts)
        decl = extract(lines, 1600, 10 + 30 * len(lines))
        surface_results.append(SurfaceResultModel(
            id=idx, surface="listing_html", image_size={"width": 1600, "height": 10 + 30 * len(lines)}, scale=1.0,
            ocr={"lines": lines, "source": "html", "url": url}, quality=None, declarations=decl,
        ))
        sources.append("html")

    for i in range(1, 7):
        file_obj = form.get(f"file_{i}") or form.get(f"image_{i}")
        if not (file_obj and hasattr(file_obj, "read")):
            continue
        contents = await file_obj.read()
        if not contents:
            continue
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Screenshot exceeds 10 MB.")
        try:
            image = Image.open(io.BytesIO(contents)); image.verify(); image = Image.open(io.BytesIO(contents))
        except Exception:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Invalid screenshot image.")
        idx += 1
        w, h = image.size
        ocr_result = ocr.extract_text(image)
        decl = extract(ocr_result.get("lines", []), w, h)
        surface_results.append(SurfaceResultModel(
            id=idx, surface="screenshot", image_size={"width": w, "height": h}, scale=1.0,
            ocr=ocr_result, quality=assess_quality(image), declarations=decl,
        ))
        sources.append("screenshot")

    if not surface_results:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide a listing url and/or at least one screenshot (file_1).")

    merged = merge_declarations(surface_results)
    mode = "mixed" if len(set(sources)) > 1 else sources[0]
    context = ContextModel(package_type="retail", category="general", is_import=is_import, channel="ecommerce",
                           listing={"mode": mode, "url": url, "sources": sources})
    applicability_obj = resolve(context, merged)
    findings_list, summary_obj = evaluate(merged, applicability_obj, context=context)

    presence = listing_presence(merged, bool(applicability_obj.is_import))
    parity = font_parity(merged) if "screenshot" in sources else None
    return {
        "mode": mode,
        "url": url,
        "surfaces": [s.model_dump() for s in surface_results],
        "merged": merged.model_dump(),
        "applicability": applicability_obj.model_dump(),
        "findings": [f.model_dump() for f in findings_list],
        "summary": summary_obj.model_dump(),
        "listing": {"presence": presence, "font_parity": parity},
        "rules_version": RULES_VERSION,
        "model_version": MODEL_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
    }


@router.post("/report")
async def create_report(
    file: UploadFile = File(...),
    result: str = Form(...),
    officer_name: Optional[str] = Form(None),
    premises: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
):
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format. Allowed formats: JPEG, PNG, WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 10 MB.",
        )

    try:
        result_data = json.loads(result)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid result JSON format.",
        )

    try:
        from nirikshan.report.render import generate_report_pdf
        pdf_bytes = generate_report_pdf(
            image_bytes=contents,
            result_data=result_data,
            officer_name=officer_name,
            premises=premises,
            remarks=remarks,
            language=language or "en",
        )
    except Exception as e:
        logger.error(f"Failed to generate report PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation error: {str(e)}",
        )

    filename = f"Nirikshan_Report_{int(time.time())}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# Catch-all for unknown /api/* paths to return JSON 404 (not HTML)
@router.get("/{api_path:path}")
async def api_404_fallback(api_path: str):

    return JSONResponse(status_code=404, content={"detail": "API route not found"})


@router.post("/{api_path:path}")
async def api_post_404_fallback(api_path: str):
    return JSONResponse(status_code=404, content={"detail": "API route not found"})


# Include API Router
app.include_router(router)

# Serve Static Files & SPA Fallback for non-/api paths (Path Traversal Safe)
static_dir = os.path.join(os.path.dirname(__file__), "static")
assets_dir = os.path.join(static_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    base = os.path.realpath(static_dir)
    target = os.path.realpath(os.path.join(static_dir, full_path))
    if os.path.isfile(target) and target.startswith(base + os.sep):
        return FileResponse(target)
    index_path = os.path.join(base, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<!DOCTYPE html><html><body><div id='root'></div></body></html>", status_code=200)
