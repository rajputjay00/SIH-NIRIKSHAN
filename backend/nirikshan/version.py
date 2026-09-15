import hashlib
import os

MODEL_VERSION = "rapidocr_1.4.4"
EXTRACTOR_VERSION = "0.1.0"

CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "rules", "catalogue.yaml")
if os.path.exists(CATALOGUE_PATH):
    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    normalized_bytes = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    RULES_VERSION = "0.4.0+" + hashlib.sha256(normalized_bytes).hexdigest()[:12]
else:
    RULES_VERSION = "0.4.0+unknown"
