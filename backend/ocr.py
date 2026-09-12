import logging
import time
from typing import Any, Dict
import numpy as np
from PIL import Image

logger = logging.getLogger("nirikshan.ocr")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def extract_text(image: Image.Image) -> Dict[str, Any]:
    # 1. Preprocess: convert to RGB
    if image.mode != "RGB":
        image = image.convert("RGB")

    # 2. Downscale if longest side > 1600 px
    width, height = image.size
    max_dim = max(width, height)
    if max_dim > 1600:
        scale = 1600.0 / max_dim
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 3. Run RapidOCR & measure execution time
    img_np = np.array(image)
    start_time = time.perf_counter()
    engine = get_engine()
    result, _ = engine(img_np)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    logger.info(f"OCR processing completed in {elapsed_ms:.2f} ms")

    # 4. Format output lines & full_text
    lines = []
    text_list = []

    if result:
        for item in result:
            bbox_raw, text, confidence = item[0], item[1], item[2]
            bbox = [[float(pt[0]), float(pt[1])] for pt in bbox_raw]

            line_obj = {
                "text": str(text),
                "confidence": round(float(confidence), 4),
                "bbox": bbox,
            }
            lines.append(line_obj)
            text_list.append(str(text))

    full_text = "\n".join(text_list)

    return {
        "full_text": full_text,
        "lines": lines,
        "elapsed_ms": round(elapsed_ms, 2),
    }
