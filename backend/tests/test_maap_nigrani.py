import io
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from nirikshan import geometry, nigrani
from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel


def bb(x, y, w, h):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def label(gap_above=5, gap_below=5):
    """MRP line, net quantity line, manufacturer line stacked with the given gaps."""
    y_nq = 10 + 30 + gap_above
    y_mfr = y_nq + 30 + gap_below
    return [
        {"text": "MRP ₹100.00 (Incl. of all taxes)", "confidence": 0.95, "bbox": bb(10, 10, 300, 30)},
        {"text": "Net Qty: 500 g", "confidence": 0.95, "bbox": bb(10, y_nq, 160, 30)},
        {"text": "Mfd by: Test Foods Pvt Ltd, Satna 485001", "confidence": 0.9, "bbox": bb(10, y_mfr, 400, 30)},
    ]


def verdicts(lines, ctx, *ids, decl_patch=None):
    d = extract(lines, 1600, 1200)
    if decl_patch:
        decl_patch(d)
    f, s = evaluate(d, resolve(ctx, d), context=ctx)
    fb = {x.rule_id: x for x in f}
    return [fb[i] for i in ids], s


# ---------------------------------------------------------------------------
# R20 — clear space
# ---------------------------------------------------------------------------

def test_clear_space_ratios():
    cs = geometry.clear_space(bb(100, 100, 200, 30), [(1, bb(100, 40, 200, 30)), (2, bb(400, 100, 100, 30))])
    # numeral height = 0.72 × 30 = 21.6 ; above gap 30 → 1.39× ok ; right gap 100 → 4.6× ok
    assert cs["numeral_height_px"] == 21.6
    assert cs["gaps"]["above"]["ratio"] == pytest.approx(1.39, abs=0.01) and cs["gaps"]["above"]["ok"]
    assert cs["gaps"]["right"]["ok"] and cs["gaps"]["below"]["ratio"] is None
    assert cs["all_ok"]


def test_clear_space_flags_intruding_text_and_overlap():
    cs = geometry.clear_space(bb(100, 100, 200, 30), [(1, bb(100, 90, 200, 20)), (2, bb(305, 100, 80, 30))])
    assert cs["gaps"]["above"]["gap_px"] == 0.0 and not cs["gaps"]["above"]["ok"]   # overlapping box
    assert not cs["gaps"]["right"]["ok"]                                            # 5 px < 2× numeral height
    assert cs["all_ok"] is False and cs["worst_direction"] in ("above", "right")


def test_r20_gated_by_geometry_flag():
    (f,), _ = verdicts(label(), ContextModel(), "R20")
    assert f.verdict == "N/A"


def test_r20_needs_review_when_tight_and_pass_when_spaced():
    (tight,), _ = verdicts(label(5, 5), ContextModel(geometry_checks=True), "R20")
    (spaced,), _ = verdicts(label(60, 60), ContextModel(geometry_checks=True), "R20")
    assert tight.verdict == "NEEDS_REVIEW" and "above" in tight.extracted
    assert spaced.verdict == "PASS"
    assert tight.evidence_bbox is not None


# ---------------------------------------------------------------------------
# R19 — width / height
# ---------------------------------------------------------------------------

def test_aspect_estimate_regular_and_condensed():
    reg = geometry.aspect_estimate("Net Qty: 500 g", bb(0, 0, 160, 30))
    cond = geometry.aspect_estimate("NET QUANTITY 500 g", bb(0, 0, 60, 40))
    assert reg["ok"] and reg["ratio"] > 0.34
    assert not cond["ok"]
    assert geometry.aspect_estimate("1", bb(0, 0, 10, 30)) is None      # too short to judge


def test_r19_verdicts():
    lines = label(60, 60)
    (ok,), _ = verdicts(lines, ContextModel(geometry_checks=True), "R19")
    assert ok.verdict == "PASS"
    condensed = [dict(l) for l in lines]
    condensed[1] = {**condensed[1], "bbox": bb(10, 100, 50, 40)}         # squeezed net quantity
    (bad,), _ = verdicts(condensed, ContextModel(geometry_checks=True), "R19")
    assert bad.verdict == "NEEDS_REVIEW"


# ---------------------------------------------------------------------------
# R22 — contrast
# ---------------------------------------------------------------------------

def _img_with_text(color):
    img = Image.new("RGB", (400, 120), "white")
    ImageDraw.Draw(img).text((20, 40), "MRP Rs 100.00 NET 500 g", fill=color)
    return img


def test_contrast_measurement():
    dark = geometry.contrast_in_box(_img_with_text((0, 0, 0)), bb(10, 30, 300, 40))
    light = geometry.contrast_in_box(_img_with_text((205, 205, 205)), bb(10, 30, 300, 40))
    assert dark["ok"] and dark["ratio"] > 5
    assert not light["ok"] and light["ratio"] < 3
    assert geometry.contrast_in_box(_img_with_text((0, 0, 0)), bb(0, 0, 4, 4)) is None   # too small


def test_r22_info_without_image_and_review_on_low_contrast():
    (info,), _ = verdicts(label(60, 60), ContextModel(), "R22")
    assert info.verdict == "INFO"

    def low(d):
        d.mrp.contrast = {"ratio": 1.5, "min_ratio": 3.0, "ok": False}
        d.net_quantity.contrast = {"ratio": 12.0, "min_ratio": 3.0, "ok": True}
    (rev,), _ = verdicts(label(60, 60), ContextModel(), "R22", decl_patch=low)
    assert rev.verdict == "NEEDS_REVIEW" and "MRP" in rev.extracted

    def good(d):
        d.mrp.contrast = {"ratio": 9.0, "min_ratio": 3.0, "ok": True}
        d.net_quantity.contrast = {"ratio": 12.0, "min_ratio": 3.0, "ok": True}
    (ok,), _ = verdicts(label(60, 60), ContextModel(), "R22", decl_patch=good)
    assert ok.verdict == "PASS"


def test_attach_contrast_on_real_image_geometry():
    img = _img_with_text((0, 0, 0))
    lines = [{"text": "MRP Rs 100.00 NET 500 g", "confidence": 0.9, "bbox": bb(10, 30, 300, 40)}]
    d = extract(lines, 400, 120)
    geometry.attach_contrast(d, img)
    assert d.mrp is not None and d.mrp.contrast and d.mrp.contrast["ok"]


# ---------------------------------------------------------------------------
# R17 — dual MRP across scans
# ---------------------------------------------------------------------------

def prior(mrp, name="Wheat Atta", qty=500, unit="g", sid="scan_1"):
    return {"id": sid, "created_at": "2026-09-14T10:00:00Z",
            "result": {"merged": {"generic_name": {"value": name}, "net_quantity": {"value": qty, "unit": unit}, "mrp": {"value": mrp}}}}


def named_label():
    return label(60, 60) + [{"text": "Common name: Wheat Atta", "confidence": 0.9, "bbox": bb(10, 300, 300, 30)}]


def test_product_key_and_conflicts():
    d = extract(named_label(), 1600, 1200)
    assert nigrani.product_key(d) == "wheat atta|500g"
    res = nigrani.find_dual_mrp(d, [prior(100.0), prior(95.0, sid="scan_2"), prior(100.0, qty=1, unit="kg", sid="scan_3")])
    assert len(res["matches"]) == 2 and [c["scan_id"] for c in res["conflicts"]] == ["scan_2"]


def test_r17_verdicts():
    d = extract(named_label(), 1600, 1200)
    for priors, expected in (([], "INFO"), ([prior(100.0)], "PASS"), ([prior(95.0)], "NEEDS_REVIEW")):
        ctx = ContextModel(dual_mrp=nigrani.find_dual_mrp(d, priors))
        f = {x.rule_id: x for x in evaluate(d, resolve(ctx, d), context=ctx)[0]}["R17"]
        assert f.verdict == expected, priors


# ---------------------------------------------------------------------------
# R29 / R30 — listing mode
# ---------------------------------------------------------------------------

FULL_HTML = """<html><head><title>Atta</title><style>.x{}</style></head><body>
<h1>Fresh Wheat Atta 5 kg</h1><script>var a=1;</script>
<ul><li>MRP: ₹250.00 (inclusive of all taxes)</li><li>Net Quantity: 5 kg</li>
<li>Manufactured by: Test Foods Pvt Ltd, Industrial Area, Satna 485001</li>
<li>Consumer care: 1800-123-4567, care@testfoods.in</li><li>Common name: Wheat Atta</li></ul>
<table><tr><td>Country of Origin</td><td>India</td></tr></table></body></html>"""
SPARSE_HTML = "<html><body><h1>Wheat Atta 5 kg</h1><p>MRP ₹250</p></body></html>"


def test_html_to_lines_strips_script_and_style():
    lines = nigrani.html_to_lines(FULL_HTML)
    assert "var a=1;" not in " ".join(lines) and ".x{}" not in " ".join(lines)
    assert any("Net Quantity: 5 kg" in l for l in lines)


def test_listing_presence_and_r29():
    ctx = ContextModel(channel="ecommerce", listing={"mode": "html"})
    d = extract(nigrani.lines_to_ocr(nigrani.html_to_lines(FULL_HTML)), 1600, 400)
    a = resolve(ctx, d)
    assert a.applicable_rule_ids == ["R29", "R30"] and "R12" in a.reasons
    pres = nigrani.listing_presence(d, is_import=False)
    assert not pres["missing"]
    fb = {x.rule_id: x for x in evaluate(d, a, context=ctx)[0]}
    assert fb["R29"].verdict == "PASS" and fb["R30"].verdict == "NEEDS_REVIEW"   # html → font not measurable

    d2 = extract(nigrani.lines_to_ocr(nigrani.html_to_lines(SPARSE_HTML)), 1600, 200)
    fb2 = {x.rule_id: x for x in evaluate(d2, resolve(ctx, d2), context=ctx)[0]}
    assert fb2["R29"].verdict == "FAIL" and "Consumer care" in fb2["R29"].extracted


def test_r30_font_parity_from_screenshot_boxes():
    ctx = ContextModel(channel="ecommerce", listing={"mode": "screenshot"})
    big_mrp = [
        {"text": "MRP ₹250.00 (inclusive of all taxes)", "confidence": 0.95, "bbox": bb(10, 10, 400, 40)},
        {"text": "Net Quantity: 5 kg", "confidence": 0.95, "bbox": bb(10, 80, 150, 20)},
    ]
    equal = [big_mrp[0], {**big_mrp[1], "bbox": bb(10, 80, 300, 40)}]
    marginal = [big_mrp[0], {**big_mrp[1], "bbox": bb(10, 80, 240, 33)}]
    for lines, expected in ((big_mrp, "FAIL"), (equal, "PASS"), (marginal, "NEEDS_REVIEW")):
        d = extract(lines, 800, 200)
        f = {x.rule_id: x for x in evaluate(d, resolve(ctx, d), context=ctx)[0]}["R30"]
        assert f.verdict == expected, lines


def test_r29_r30_not_applicable_on_pack_scan():
    (r29, r30), _ = verdicts(label(60, 60), ContextModel(), "R29", "R30")
    assert r29.verdict == "N/A" and r30.verdict == "N/A"


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def test_listing_endpoint_html(client, monkeypatch):
    import main
    monkeypatch.setattr(main, "fetch_listing_html", lambda url, timeout=10.0: FULL_HTML)
    r = client.post("/api/listing/check", data={"url": "https://example.com/p/atta"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "html" and body["applicability"]["applicable_rule_ids"] == ["R29", "R30"]
    fb = {f["rule_id"]: f for f in body["findings"]}
    assert fb["R29"]["verdict"] == "PASS" and fb["R30"]["verdict"] == "NEEDS_REVIEW"
    assert body["listing"]["presence"]["missing"] == []


def test_listing_endpoint_requires_input(client):
    assert client.post("/api/listing/check", data={}).status_code == 400
    assert client.post("/api/listing/check", data={"url": "ftp://x"}).status_code == 400


def test_scan_accepts_geometry_flag(client):
    buf = io.BytesIO(); Image.new("RGB", (60, 40), "white").save(buf, format="PNG")
    r = client.post("/api/scan", files={"file": ("x.png", buf.getvalue(), "image/png")},
                    data={"geometry_checks": "true", "weighing": "{bad"})
    assert r.status_code == 400      # the weighing JSON is rejected before OCR runs
