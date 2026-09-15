import json
import pytest
from fastapi.testclient import TestClient

from nirikshan import tol
from nirikshan.rules.engine import evaluate, load_catalogue
from nirikshan.applicability import resolve
from nirikshan.extract import extract
from nirikshan.schema import ContextModel, WeighingInput, LotInput, LotSample


# ---------------------------------------------------------------------------
# First Schedule MPE table
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("declared,unit,expected_mpe,band", [
    (25, "g", 2.3, "9.0%"),         # ≤ 50 g → 9 %  (2.25 → 2.3 after 0.1 rounding)
    (50, "g", 4.5, "9.0%"),
    (75, "ml", 4.5, "4.5 ml"),      # 50–100 → 4.5 g/ml
    (150, "g", 6.8, "4.5%"),        # 100–200 → 4.5 % (6.75 → 6.8)
    (250, "g", 9.0, "9.0 g"),       # 200–300 → 9 g
    (500, "g", 15.0, "3.0%"),       # 300–500 → 3 %
    (1, "kg", 15.0, "15.0 g"),      # 500–1000 → 15 g (1 kg = 1000 g)
    (5, "kg", 75.0, "1.5%"),        # 1000–10000 → 1.5 %
    (12, "kg", 150.0, "150.0 g"),   # 10–15 kg → 150 g
    (20, "L", 200.0, "1.0%"),       # > 15 L → 1 %
])
def test_mpe_table_i(declared, unit, expected_mpe, band):
    m = tol.mpe_for(declared, unit)
    assert m["table"] == "First Schedule Table I"
    assert m["mpe_base"] == pytest.approx(expected_mpe)
    assert m["band"] == band


def test_mpe_rounding_above_1000_rounds_up_to_whole_unit():
    # 1.5 % of 1234 g = 18.51 → next whole gram = 19
    assert tol.mpe_for(1234, "g")["mpe_base"] == 19.0


@pytest.mark.parametrize("declared,unit,expected_mpe", [
    (5, "m", 10.0),      # length ≤ 10 m → 2 % of 500 cm
    (50, "m", 50.0),     # > 10 m → 1 % of 5000 cm
    (2, "m2", 800.0),    # area ≤ 10 m² → 4 % of 20000 cm²
    (10, "N", 1.0),      # number → 2 % rounded up to whole unit
])
def test_mpe_table_ii(declared, unit, expected_mpe):
    m = tol.mpe_for(declared, unit)
    assert m["table"] == "First Schedule Table II"
    assert m["mpe_base"] == pytest.approx(expected_mpe)


def test_mpe_rejects_bad_input():
    with pytest.raises(ValueError):
        tol.mpe_for(0, "g")
    with pytest.raises(ValueError):
        tol.mpe_for(100, "oz")


# ---------------------------------------------------------------------------
# R31 single pack
# ---------------------------------------------------------------------------

def test_single_pack_pass_within_mpe():
    r = tol.check_single_pack(500, "g", gross=520, tare=30)   # net 490, MPE 15
    assert r["verdict"] == "PASS" and r["within_mpe"] and not r["exceeds_2x_mpe"]
    assert r["error_base"] == pytest.approx(-10.0)


def test_single_pack_fail_beyond_mpe():
    r = tol.check_single_pack(500, "g", net=480)              # short 20 > 15
    assert r["verdict"] == "FAIL" and not r["exceeds_2x_mpe"]


def test_single_pack_fail_aggravated_beyond_2x():
    r = tol.check_single_pack(500, "g", net=460)              # short 40 > 30
    assert r["verdict"] == "FAIL" and r["exceeds_2x_mpe"]
    assert "aggravated" in r["summary"]


def test_single_pack_excess_is_pass():
    r = tol.check_single_pack(500, "g", net=530)
    assert r["verdict"] == "PASS"


def test_single_pack_marginal_within_resolution_is_needs_review():
    r = tol.check_single_pack(500, "g", net=485.5, resolution=1.0)   # deficiency 14.5 vs MPE 15
    assert r["verdict"] == "NEEDS_REVIEW" and r["marginal"]


def test_single_pack_unit_conversion_kg_vs_g():
    r = tol.check_single_pack(1, "kg", net=990, measured_unit="g")
    assert r["declared_base"] == 1000.0 and r["verdict"] == "PASS"


def test_single_pack_requires_net_or_gross_and_tare():
    with pytest.raises(ValueError):
        tol.check_single_pack(500, "g", gross=520)


# ---------------------------------------------------------------------------
# R32 lot inspection
# ---------------------------------------------------------------------------

def test_sample_size_fifth_schedule():
    assert tol.sample_size_for(1) == 32
    assert tol.sample_size_for(4000) == 32
    assert tol.sample_size_for(4001) == 80


def test_tare_procedure():
    mpe = 15.0
    assert tol.determine_tare([4.0], mpe)["ok"]                        # 4 ≤ 0.3×15 = 4.5
    assert not tol.determine_tare([6.0], mpe)["ok"]                    # single tare too large
    assert not tol.determine_tare([6.0, 6.1, 6.2], mpe)["ok"]          # fewer than five
    five = tol.determine_tare([6.0, 6.1, 6.2, 6.0, 6.1], mpe)          # spread 0.2 ≤ 6.0
    assert five["ok"] and five["tare"] == pytest.approx(6.08)
    assert not tol.determine_tare([6.0, 6.1, 20.0, 6.0, 6.1], mpe)["ok"]  # spread too large
    assert tol.determine_tare([], mpe)["method"] == "none"


def _lot(nets, lot_size=1000, declared=500, unit="g"):
    return tol.lot_inspection(lot_size, declared, unit,
                              samples=[{"gross": n + 4.0} for n in nets], tares=[4.0])


def test_lot_approved():
    nets = [501, 502, 503] * 10 + [501, 502]
    r = _lot(nets)
    assert r["status"] == "APPROVED" and r["form"] == "A"
    assert r["sample_size_required"] == 32 and r["sample_size_weighed"] == 32
    assert r["corrected_average"] >= 500.0 and r["t1_count"] == 0 and r["t2_count"] == 0
    assert r["sample_correction_factor"] == 0.485


def test_lot_rejected_on_t2_error():
    nets = [505] * 31 + [460]                       # one package below 500 − 30
    r = _lot(nets)
    assert r["status"] == "REJECTED" and r["t2_count"] == 1
    assert any("2×MPE" in x for x in r["reasons"])


def test_lot_rejected_on_too_many_t1():
    nets = [505] * 29 + [480, 480, 480]             # three packages below 500 − 15, allowed 2
    r = _lot(nets)
    assert r["status"] == "REJECTED" and r["t1_count"] == 3


def test_lot_rejected_on_corrected_average():
    nets = [497.0, 498.0] * 16                      # mean 497.5, sd 0.5 → corrected 497.7 < 500
    r = _lot(nets)
    assert r["status"] == "REJECTED"
    assert any("Corrected average" in x for x in r["reasons"])


def test_lot_incomplete_when_sample_short():
    r = _lot([505] * 10)
    assert r["status"] == "INCOMPLETE" and r["sample_size_weighed"] == 10


def test_lot_incomplete_when_tare_invalid():
    r = tol.lot_inspection(1000, 500, "g", samples=[{"gross": 509}] * 32, tares=[9.0])  # 9 > 0.3×15
    assert r["status"] == "INCOMPLETE" and r["samples"][0]["net"] is None


def test_lot_per_sample_tare_and_volume_form_b():
    r = tol.lot_inspection(5000, 1, "L", samples=[{"gross": 1030, "tare": 25}] * 80, measured_unit="ml")
    assert r["form"] == "B" and r["sample_size_required"] == 80 and r["status"] == "APPROVED"


# ---------------------------------------------------------------------------
# Engine integration (catalogue R31 / R32)
# ---------------------------------------------------------------------------

LINES = [
    {"text": "MRP ₹100.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": [[10, 10], [200, 10], [200, 30], [10, 30]]},
    {"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": [[10, 40], [200, 40], [200, 60], [10, 60]]},
]


def _engine_verdict(rule_id, ctx):
    d = extract(LINES, 1600, 1200)
    findings, summary = evaluate(d, resolve(ctx, d), context=ctx)
    return {f.rule_id: f for f in findings}[rule_id], summary


def test_engine_r31_info_without_weighing_does_not_change_status():
    f, s = _engine_verdict("R31", ContextModel())
    assert f.verdict == "INFO"
    assert s.counts["INFO"] >= 1


@pytest.mark.parametrize("net,verdict", [(490, "PASS"), (480, "FAIL"), (460, "FAIL")])
def test_engine_r31_verdicts(net, verdict):
    f, _ = _engine_verdict("R31", ContextModel(weighing=WeighingInput(net=net)))
    assert f.verdict == verdict
    assert f.evidence_bbox is not None            # evidence = net quantity bbox


def test_engine_r31_marginal_needs_review():
    f, _ = _engine_verdict("R31", ContextModel(weighing=WeighingInput(net=485.5, resolution=1)))
    assert f.verdict == "NEEDS_REVIEW"


def test_engine_r31_declared_override_when_ocr_missed_quantity():
    d = extract([LINES[0]], 1600, 1200)           # no net quantity line
    ctx = ContextModel(weighing=WeighingInput(net=480, declared_value=500, declared_unit="g"))
    f = {x.rule_id: x for x in evaluate(d, resolve(ctx, d), context=ctx)[0]}["R31"]
    assert f.verdict == "FAIL"


def test_engine_r32_verdicts():
    ok = ContextModel(lot=LotInput(lot_size=1000, tares=[4.0], samples=[LotSample(gross=505)] * 32))
    bad = ContextModel(lot=LotInput(lot_size=1000, tares=[4.0], samples=[LotSample(gross=505)] * 31 + [LotSample(gross=460)]))
    short = ContextModel(lot=LotInput(lot_size=1000, tares=[4.0], samples=[LotSample(gross=505)] * 5))
    assert _engine_verdict("R32", ContextModel())[0].verdict == "INFO"
    assert _engine_verdict("R32", ok)[0].verdict == "PASS"
    assert _engine_verdict("R32", bad)[0].verdict == "FAIL"
    assert _engine_verdict("R32", short)[0].verdict == "NEEDS_REVIEW"


def test_r31_r32_not_applicable_when_exempt():
    ctx = ContextModel(net_quantity_override={"value": 8, "unit": "g"}, weighing=WeighingInput(net=5))
    f, _ = _engine_verdict("R31", ctx)
    assert f.verdict == "N/A"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_api_mpe(client):
    r = client.get("/api/tol/mpe", params={"declared_value": 500, "unit": "g"})
    assert r.status_code == 200 and r.json()["mpe_base"] == 15.0


def test_api_weigh(client):
    r = client.post("/api/tol/weigh", json={"declared_value": 500, "declared_unit": "g", "gross": 510, "tare": 30})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "FAIL" and body["finding"]["rule_id"] == "R31"
    assert body["finding"]["fix_hint_en"]
    assert body["rules_version"]


def test_api_weigh_bad_input(client):
    r = client.post("/api/tol/weigh", json={"declared_value": 500, "declared_unit": "g", "gross": 510})
    assert r.status_code == 400


def test_api_lot_and_form_pdf(client):
    payload = {
        "lot_size": 1000, "declared_value": 500, "declared_unit": "g", "tares": [4.0],
        "samples": [{"gross": 505}] * 32,
        "officer": "LMO Test", "premises": "Test mandi", "packer": "Test Foods Pvt Ltd, Satna 485001",
        "commodity": "Atta", "lot_id": "L-42",
    }
    r = client.post("/api/tol/lot", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED" and r.json()["finding"]["verdict"] == "PASS"

    r2 = client.post("/api/tol/lot/form", json=payload)
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("application/pdf")
    assert r2.content[:4] == b"%PDF"
    assert "Form_A" in r2.headers["content-disposition"]


def test_api_inspect_accepts_weighing_json_field(client):
    """The multipart field is parsed; a bad JSON string is a 400, not a 500."""
    from PIL import Image
    import io
    buf = io.BytesIO(); Image.new("RGB", (60, 40), "white").save(buf, format="PNG")
    r = client.post("/api/scan", files={"file": ("x.png", buf.getvalue(), "image/png")},
                    data={"weighing": "{not json"})
    assert r.status_code == 400
