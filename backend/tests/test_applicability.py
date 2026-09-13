import pytest
from nirikshan.applicability import resolve
from nirikshan.schema import ContextModel, Declarations, EntityBlock, NetQuantity, FieldModel


def test_10g_sachet_exempt():
    decl = Declarations(net_quantity=NetQuantity(value=10.0, unit="g"))
    ctx = ContextModel()
    app = resolve(ctx, decl)
    assert app.applicable_rule_ids == []
    assert "Rule 26(a)" in (app.exempt_reason or "")


def test_15g_sachet_limited_rules():
    decl = Declarations(net_quantity=NetQuantity(value=15.0, unit="g"))
    ctx = ContextModel()
    app = resolve(ctx, decl)
    assert sorted(app.applicable_rule_ids) == ["R06", "R12"]
    assert "R01" not in app.applicable_rule_ids
    assert "10–20 g/ml" in app.reasons["R01"]


def test_30kg_bag_chapter_ii_exempt():
    decl = Declarations(net_quantity=NetQuantity(value=30.0, unit="kg"))
    ctx = ContextModel()
    app = resolve(ctx, decl)
    assert app.applicable_rule_ids == []
    assert "Rule 3" in (app.exempt_reason or "")


def test_food_category_exemptions():
    decl = Declarations(net_quantity=NetQuantity(value=500.0, unit="g"))
    ctx = ContextModel(category="food")
    app = resolve(ctx, decl)
    assert "R01" not in app.applicable_rule_ids
    assert "R02" not in app.applicable_rule_ids
    assert "R10" not in app.applicable_rule_ids
    assert "FSS Act" in app.reasons["R01"]
    assert "R06" in app.applicable_rule_ids
    assert "R12" in app.applicable_rule_ids
    assert "R35" in app.applicable_rule_ids


def test_wholesale_package():
    decl = Declarations(net_quantity=NetQuantity(value=50.0, unit="kg"))
    ctx = ContextModel(package_type="wholesale")
    app = resolve(ctx, decl)
    assert app.applicable_rule_ids == ["R27"]
    assert "Rule 24" in app.reasons["R01"]


def test_import_inference():
    # Inferred imported true when importer present
    decl_imp = Declarations(importer=EntityBlock(name="ImportCorp", value="ImportCorp"))
    app_imp = resolve(ContextModel(), decl_imp)
    assert app_imp.is_import is True
    assert "R04" in app_imp.applicable_rule_ids

    # Inferred imported false when importer absent
    decl_local = Declarations()
    app_local = resolve(ContextModel(), decl_local)
    assert app_local.is_import is False
    assert "R04" not in app_local.applicable_rule_ids


def test_multipiece_r14_exempt():
    decl = Declarations(net_quantity=NetQuantity(value=500.0, unit="g"))
    ctx = ContextModel(package_type="multi_piece")
    app = resolve(ctx, decl)
    assert "R14" not in app.applicable_rule_ids
    assert "Rule 6(11)" in app.reasons["R14"]


def test_drug_dpco_exempt():
    decl = Declarations(net_quantity=NetQuantity(value=100.0, unit="ml"))
    ctx = ContextModel(category="drug")
    app = resolve(ctx, decl)
    assert app.applicable_rule_ids == []
    assert "Rule 26(c)" in (app.exempt_reason or "")
    from nirikshan.rules.engine import evaluate
    findings, summary = evaluate(decl, app)
    assert summary.status == "Exempt"


def test_10g_sachet_summary_status_exempt():
    decl = Declarations(net_quantity=NetQuantity(value=10.0, unit="g"))
    ctx = ContextModel()
    app = resolve(ctx, decl)
    from nirikshan.rules.engine import evaluate
    findings, summary = evaluate(decl, app)
    assert summary.status == "Exempt"

