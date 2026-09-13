import time
import pytest
from fastapi.testclient import TestClient
from main import app
from nirikshan.session import session_store, SESSION_TTL_SECONDS, MAX_SCANS_PER_SESSION

client = TestClient(app)

def test_create_session():
    response = client.post("/api/session")
    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert "created_at" in data

def test_session_store_scan_and_list():
    res = client.post("/api/session")
    code = res.json()["code"]

    dummy_result = {"summary": {"status": "Compliant"}, "filename": "test.png"}
    session_store.add_scan_result(code, dummy_result)

    list_res = client.get(f"/api/session/{code}/results")
    assert list_res.status_code == 200
    scans = list_res.json()
    assert len(scans) == 1
    assert scans[0]["result"]["summary"]["status"] == "Compliant"

def test_session_404_invalid_code():
    res = client.get("/api/session/INVALID/results")
    assert res.status_code == 404

def test_session_max_scans_limit():
    res = client.post("/api/session")
    code = res.json()["code"]

    for i in range(MAX_SCANS_PER_SESSION + 5):
        session_store.add_scan_result(code, {"scan": i})

    scans = session_store.get_results(code)
    assert len(scans) == MAX_SCANS_PER_SESSION
    assert scans[0]["result"]["scan"] == MAX_SCANS_PER_SESSION + 4

def test_session_expiry_ttl():
    res = client.post("/api/session")
    code = res.json()["code"]

    # Force expiration
    session_store._sessions[code]["created_at_ts"] -= (SESSION_TTL_SECONDS + 10)

    list_res = client.get(f"/api/session/{code}/results")
    assert list_res.status_code == 404

def test_sse_smoke_test():
    res = client.post("/api/session")
    code = res.json()["code"]

    queue = session_store.subscribe(code)
    assert queue is not None

    session_store.add_scan_result(code, {"test": "sse"})

    record = queue.get_nowait()
    assert record["result"]["test"] == "sse"
    session_store.unsubscribe(code, queue)

