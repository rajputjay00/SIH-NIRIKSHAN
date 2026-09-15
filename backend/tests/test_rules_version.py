import os
import hashlib
from nirikshan.version import RULES_VERSION


CATALOGUE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "nirikshan", "rules", "catalogue.yaml")
)
HASH_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "fixtures", "rules", "CATALOGUE_HASH")
)


def test_rules_version_matches_catalogue_hash():
    assert os.path.exists(CATALOGUE_PATH), "catalogue.yaml missing"
    assert os.path.exists(HASH_FILE_PATH), "CATALOGUE_HASH missing"

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    curr_hash = hashlib.sha256(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")).hexdigest()[:12]

    with open(HASH_FILE_PATH, "r", encoding="utf-8") as f:
        stored_hash = f.read().strip()

    assert curr_hash == stored_hash, (
        f"catalogue.yaml changed (current hash: {curr_hash}, stored: {stored_hash}) — "
        "bump version in version.py and update CATALOGUE_HASH"
    )

    assert RULES_VERSION.endswith(curr_hash)
