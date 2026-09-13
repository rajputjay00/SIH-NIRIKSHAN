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
from nirikshan.schema import ContextModel, SurfaceResultModel
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
