import io
import importlib.metadata
import os
import subprocess
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
        ocr.extract_text(create_warmup_image(1600, 1200))
        ocr.extract_text(create_warmup_image(600, 400))
        MODEL_LOADED = True
    except Exception as e:
        MODEL_LOADED = False
        logger.warning(f"Failed to warm up OCR model: {e}")
    yield


app = FastAPI(title="Nirikshan API", lifespan=lifespan)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
import time
from fastapi import Form
from nirikshan import EXTRACTOR_VERSION, extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate, load_catalogue
from nirikshan.schema import ContextModel
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


@router.post("/scan")
async def scan_image(
    file: UploadFile = File(...),
    package_type: Optional[str] = Form("retail"),
    category: Optional[str] = Form("general"),
    is_import: Optional[bool] = Form(None),
    channel: Optional[str] = Form("physical"),
    net_quantity_value: Optional[float] = Form(None),
    net_quantity_unit: Optional[str] = Form(None),
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
        image = Image.open(io.BytesIO(contents))
        image.verify()
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid or corrupt image file.",
        )

    width, height = image.size
    ocr_result = ocr.extract_text(image)

    extract_start = time.perf_counter()
    declarations_obj = extract(ocr_result.get("lines", []), width, height)
    extract_ms = (time.perf_counter() - extract_start) * 1000.0

    # Build context and run applicability & rules engine
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

    applicability_obj = resolve(context, declarations_obj)

    rules_start = time.perf_counter()
    findings_list, summary_obj = evaluate(declarations_obj, applicability_obj)
    rules_ms = (time.perf_counter() - rules_start) * 1000.0

    total_elapsed = ocr_result.get("elapsed_ms", 0.0) + extract_ms + rules_ms

    return {
        "filename": file.filename,
        "width": width,
        "height": height,
        "ocr": ocr_result,
        "declarations": declarations_obj.model_dump(),
        "applicability": applicability_obj.model_dump(),
        "findings": [f.model_dump() for f in findings_list],
        "summary": summary_obj.model_dump(),
        "rules_version": RULES_VERSION,
        "model_version": MODEL_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "timings": {
            "preprocess_ms": ocr_result.get("preprocess_ms", 0.0),
            "ocr_ms": ocr_result.get("ocr_ms", 0.0),
            "extract_ms": round(extract_ms, 2),
            "rules_ms": round(rules_ms, 2),
            "elapsed_ms": round(total_elapsed, 2),
        },
    }



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
