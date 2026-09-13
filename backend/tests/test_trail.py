import pytest
from nirikshan.extract import extract
from nirikshan.applicability import resolve
from nirikshan.rules.engine import evaluate
from nirikshan.schema import ContextModel


def test_trail_presence_on_every_finding():
    lines = [
        {"text": "NET QUANTITY: 500 g", "confidence": 0.95, "bbox": [[10, 10], [100, 10], [100, 30], [10, 30]]},
        {"text": "MRP Rs. 150.00 INCL. OF ALL TAXES", "confidence": 0.95, "bbox": [[10, 50], [200, 50], [200, 70], [10, 70]]},
        {"text": "MFD BY: NIRIKSHAN LABS PVT LTD", "confidence": 0.95, "bbox": [[10, 90], [250, 90], [250, 110], [10, 110]]},
    ]

    decl = extract(lines, 800, 600)
    ctx = ContextModel(package_type="retail", category="general")
    app = resolve(ctx, decl)
    findings, summary = evaluate(decl, app, context=ctx)

    assert len(findings) > 0, "No findings generated"

    for f in findings:
        assert hasattr(f, "trail"), f"Finding {f.rule_id} missing trail attribute"
        assert f.trail is not None, f"Finding {f.rule_id} trail is None"
        assert len(f.trail) > 0, f"Finding {f.rule_id} trail is empty"

        for step in f.trail:
            assert isinstance(step, dict), f"Finding {f.rule_id} trail step is not a dict"
            assert "step" in step, f"Finding {f.rule_id} trail step missing 'step' key"
            assert "detail" in step, f"Finding {f.rule_id} trail step missing 'detail' key"
            assert len(step["step"]) > 0, f"Finding {f.rule_id} trail step key is empty"
            assert len(step["detail"]) > 0, f"Finding {f.rule_id} trail detail is empty"
