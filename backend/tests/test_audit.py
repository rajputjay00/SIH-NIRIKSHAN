import os
import io
import json
import pytest
from fastapi.testclient import TestClient
from nirikshan import audit
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_audit_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_audit.db")
    monkeypatch.setenv("NIRIKSHAN_AUDIT_DB", db_file)
    audit.init_db()
    yield db_file


def test_genesis_entry():
    entry = audit.append("officer_1", "test_action", {"test_key": "val1"})
    assert entry["id"] == 1
    assert entry["prev_hash"] == audit.GENESIS_PREV_HASH
    assert entry["actor"] == "officer_1"
    assert entry["action"] == "test_action"
    recalculated = audit.compute_entry_hash(
        entry["ts"], entry["actor"], entry["action"], entry["payload_hash"], entry["prev_hash"]
    )
    assert entry["hash"] == recalculated


def test_chain_links_across_three_appends():
    e1 = audit.append("officer_1", "action_1", {"seq": 1})
    e2 = audit.append("officer_2", "action_2", {"seq": 2})
    e3 = audit.append("officer_3", "action_3", {"seq": 3})

    assert e1["prev_hash"] == audit.GENESIS_PREV_HASH
    assert e2["prev_hash"] == e1["hash"]
    assert e3["prev_hash"] == e2["hash"]

    ok, broken_id = audit.verify_chain()
    assert ok is True
    assert broken_id is None


def test_verify_chain_detects_tampering():
    e1 = audit.append("officer_1", "action_1", {"seq": 1})
    e2 = audit.append("officer_2", "action_2", {"seq": 2})
    e3 = audit.append("officer_3", "action_3", {"seq": 3})

    ok, broken_id = audit.verify_chain()
    assert ok is True

    # Directly tamper row 2 in SQLite
    with audit.get_connection() as conn:
        conn.execute("UPDATE audit_ledger SET payload = ? WHERE id = 2", ('{"seq":999}',))
        conn.commit()

    ok, broken_id = audit.verify_chain()
    assert ok is False
    assert broken_id == 2


def test_get_by_image_hash():
    audit.append("officer_1", "report_generated", {"image_sha256": "hash_111", "verdict": "PASS"})
    audit.append("officer_2", "report_generated", {"image_sha256": "hash_222", "verdict": "FAIL"})
    audit.append("officer_1", "report_generated", {"image_sha256": "hash_111", "verdict": "PASS_UPDATED"})

    entry = audit.get_by_image_hash("hash_111")
    assert entry is not None
    assert entry["payload"]["verdict"] == "PASS_UPDATED"

    missing = audit.get_by_image_hash("hash_999")
    assert missing is None


def test_verify_endpoints_and_safe_payload():
    # 404 test
    res = client.get("/api/verify/nonexistent123")
    assert res.status_code == 404
    assert "no report found" in res.json()["detail"]

    # Audit verify on clean DB
    res_audit = client.get("/api/audit/verify")
    assert res_audit.status_code == 200
    data_audit = res_audit.json()
    assert data_audit["ok"] is True
    assert data_audit["entries"] == 0

    # Generate a report via API
    img_path = os.path.join(os.path.dirname(__file__), "fixtures", "images", "synthetic", "four_violations.png")
    scan_path = os.path.join(os.path.dirname(__file__), "fixtures", "scan_results", "four_violations.json")

    with open(img_path, "rb") as f:
        img_bytes = f.read()
    with open(scan_path, "r", encoding="utf-8") as f:
        scan_data = f.read()

    response = client.post(
        "/api/report",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"result": scan_data, "officer_name": "Inspector Roy", "premises": "Delhi Warehouse"},
    )
    assert response.status_code == 200

    import hashlib
    img_hash = hashlib.sha256(img_bytes).hexdigest()

    # Hit verify endpoint for generated report
    v_res = client.get(f"/api/verify/{img_hash}")
    assert v_res.status_code == 200
    p = v_res.json()

    assert p["chain_verified"] is True
    assert p["image_sha256"] == img_hash
    assert p["officer_name"] == "Inspector Roy"
    assert p["premises"] == "Delhi Warehouse"
    assert "status" in p
    assert "counts" in p
    assert "findings" in p

    # Ensure payload contains NO image bytes or declarations
    assert "image" not in p
    assert "declarations" not in p
    assert "ocr" not in p

    # Hit audit verify endpoint
    res_audit2 = client.get("/api/audit/verify")
    assert res_audit2.status_code == 200
    data_audit2 = res_audit2.json()
    assert data_audit2["ok"] is True
    assert data_audit2["entries"] == 1
