import os
from typing import Any, Dict, List
import cv2
import numpy as np
from PIL import Image

QUALITY_CONFIG = {
    "blur_threshold": 60.0,
    "glare_threshold": 0.08,
    "dark_threshold": 0.40,
}


def assess_quality(image: Image.Image) -> Dict[str, Any]:
    """Computes image quality metrics: blur_score, glare_ratio, dark_ratio and flags warnings."""
    max_side = int(os.getenv("NIRIKSHAN_MAX_SIDE", "2400"))
    width, height = image.size
    max_dim = max(width, height)
    if max_dim > max_side:
        scale = float(max_side) / max_dim
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        proc_img = image.resize((new_w, new_h), Image.Resampling.BILINEAR)
    else:
        proc_img = image

    img_rgb = proc_img.convert("RGB")
    img_np = np.array(img_rgb)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    glare_ratio = float((img_np[:, :, :3] > 245).all(axis=2).mean())
    dark_ratio = float((gray < 20).mean())

    warnings: List[str] = []
    if blur_score < QUALITY_CONFIG["blur_threshold"]:
        warnings.append("blurry")
    if glare_ratio > QUALITY_CONFIG["glare_threshold"]:
        warnings.append("glare")
    if dark_ratio > QUALITY_CONFIG["dark_threshold"]:
        warnings.append("dark")

    return {
        "blur_score": round(blur_score, 2),
        "glare_ratio": round(glare_ratio, 4),
        "dark_ratio": round(dark_ratio, 4),
        "warnings": warnings,
    }
