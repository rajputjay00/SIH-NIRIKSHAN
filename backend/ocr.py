import logging
import os
import time
from typing import Any, Dict, Optional, Tuple
import numpy as np
from PIL import Image, ImageOps

from nirikshan.normalize import normalize_line_text

logger = logging.getLogger("nirikshan.ocr")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_engine = None


def get_thread_count() -> int:
    env_val = os.getenv("NIRIKSHAN_THREADS")
    if env_val and env_val.isdigit():
        return int(env_val)
    return os.cpu_count() or 4


def get_engine():
    global _engine
    if _engine is None:
        threads = get_thread_count()
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["OPENBLAS_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)

        from rapidocr_onnxruntime import RapidOCR

        model_dir = os.path.join(os.path.dirname(__file__), "models")
        rec_model_path = os.path.join(model_dir, "en_PP-OCRv3_rec_infer.onnx")
        rec_keys_path = os.path.join(model_dir, "en_dict.txt")

        kwargs: Dict[str, Any] = {"intra_op_num_threads": threads}
        if os.path.exists(rec_model_path) and os.path.exists(rec_keys_path):
            kwargs["rec_model_path"] = rec_model_path
            kwargs["rec_keys_path"] = rec_keys_path

        _engine = RapidOCR(**kwargs)
    return _engine


def preprocess(image: Image.Image) -> Tuple[Image.Image, Dict[str, int], float]:
    """Applies EXIF transpose, RGB conversion, and downscaling <= NIRIKSHAN_MAX_SIDE px.
    Returns (processed_image, image_size_dict, scale).
    """
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
        image = image.convert("RGB")

    max_side = int(os.getenv("NIRIKSHAN_MAX_SIDE", "2400"))
    width, height = image.size
    max_dim = max(width, height)
    scale = 1.0
    if max_dim > max_side:
        scale = float(max_side) / max_dim
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    image_size = {"width": image.width, "height": image.height}
    return image, image_size, round(scale, 4)


def detect_barcode(img_np: np.ndarray) -> Optional[Dict[str, Any]]:
    try:
        import cv2
        if hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector"):
            detector = cv2.barcode.BarcodeDetector()
            ok, decoded_info, decoded_type, points = detector.detectAndDecode(img_np)
            if ok and decoded_info:
                for info, p in zip(decoded_info, points if points is not None else []):
                    if info and str(info).strip():
                        bbox = [[float(pt[0]), float(pt[1])] for pt in p] if p is not None else None
                        return {"value": str(info).strip(), "bbox": bbox}
    except Exception as e:
        logger.debug(f"Barcode detection error: {e}")
    return None


def extract_text(image: Image.Image) -> Dict[str, Any]:
    # Stage 1: Preprocessing (EXIF transpose, RGB conversion & downscaling <= NIRIKSHAN_MAX_SIDE px)
    preprocess_start = time.perf_counter()
    image, image_size, scale = preprocess(image)
    img_np = np.array(image)
    preprocess_ms = (time.perf_counter() - preprocess_start) * 1000.0

    # Barcode detection on image pixels
    barcode_data = detect_barcode(img_np)

    # Stage 2: RapidOCR Inference
    ocr_start = time.perf_counter()
    engine = get_engine()
    result, _ = engine(img_np)
    ocr_ms = (time.perf_counter() - ocr_start) * 1000.0

    elapsed_ms = preprocess_ms + ocr_ms

    logger.info(
        f"OCR Timings - Preprocess: {preprocess_ms:.2f} ms, OCR Inference: {ocr_ms:.2f} ms, Total: {elapsed_ms:.2f} ms (image_size={image_size})"
    )

    # Stage 3: Formatting Output Lines & Normalizing Text
    lines = []
    text_list = []

    if result:
        for item in result:
            bbox_raw, text, confidence = item[0], item[1], item[2]
            bbox = [[float(pt[0]), float(pt[1])] for pt in bbox_raw]
            norm_text = normalize_line_text(str(text))
            if not norm_text:
                continue

            line_obj = {
                "text": norm_text,
                "confidence": round(float(confidence), 4),
                "bbox": bbox,
            }
            lines.append(line_obj)
            text_list.append(norm_text)

    full_text = "\n".join(text_list)

    return {
        "full_text": full_text,
        "lines": lines,
        "barcode": barcode_data,
        "image_size": {"width": image.width, "height": image.height},
        "scale": round(scale, 4),
        "preprocess_ms": round(preprocess_ms, 2),
        "ocr_ms": round(ocr_ms, 2),
        "elapsed_ms": round(elapsed_ms, 2),
    }
