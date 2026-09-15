import hashlib
import os

MODEL_VERSION = "rapidocr_1.4.4"
EXTRACTOR_VERSION = "0.1.0"

CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "rules", "catalogue.yaml")
if os.path.exists(CATALOGUE_PATH):
    with open(CATALOGUE_PATH, "rb") as f:
        catalogue_bytes = f.read()
    RULES_VERSION = "0.4.0+" + hashlib.sha256(catalogue_bytes).hexdigest()[:12]
else:
    RULES_VERSION = "0.4.0+unknown"

