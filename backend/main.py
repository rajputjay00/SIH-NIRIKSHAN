import io
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import ocr

MODEL_LOADED = False
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL_LOADED
    # Warm up the OCR model with a tiny 10x10 image on startup
    try:
        dummy_img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        ocr.extract_text(dummy_img)
        MODEL_LOADED = True
    except Exception as e:
        MODEL_LOADED = False
        print(f"Failed to warm up OCR model: {e}")
    yield


app = FastAPI(title="Nirikshan API", lifespan=lifespan)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
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
        "rules_version": None,
        "git_sha": GIT_SHA,
    }


@router.post("/scan")
async def scan_image(file: UploadFile = File(...)):
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

    # Stub: Legal Metrology compliance parser (to be implemented in Task 4)
    # compliance_result = parse_legal_metrology(ocr_result)

    return {
        "filename": file.filename,
        "width": width,
        "height": height,
        "ocr": ocr_result,
    }


# Include API Router
app.include_router(router)

# Serve Static Files / SPA Fallback
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not Found")
