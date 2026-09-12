import io
import os
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

import ocr

app = FastAPI(title="Nirikshan API")

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/scan")
async def scan_image(file: UploadFile = File(...)):
    # 1. Content-Type check (HTTP 415)
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format. Allowed formats: JPEG, PNG, WebP.",
        )

    contents = await file.read()

    # 2. File size check (HTTP 413)
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed limit of 10 MB.",
        )

    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
        image = Image.open(io.BytesIO(contents))  # Re-open after verify
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid or corrupt image file.",
        )

    width, height = image.size

    # 3. Extract text using RapidOCR
    ocr_result = ocr.extract_text(image)

    # Stub: Legal Metrology compliance parser (to be implemented)
    # compliance_result = parse_legal_metrology(ocr_result)

    return {
        "filename": file.filename,
        "width": width,
        "height": height,
        "ocr": {
            "full_text": ocr_result["full_text"],
            "lines": ocr_result["lines"],
        },
    }
