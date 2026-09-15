"""Seventh Schedule Form A / Form B data sheet (Tol, R32)."""
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from jinja2 import Environment

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "form_ab.html")
IST = timezone(timedelta(hours=5, minutes=30))


def _g(value: Any) -> str:
    """Jinja filter: compact number formatting (500.0 -> '500', 14.5 -> '14.5')."""
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f.is_integer():
        return str(int(f))
    return f"{f:.4g}" if abs(f) < 1000 else f"{f:.2f}"


def render_form_html(
    lot_result: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    rules_version: str = "",
    language: str = "en",
) -> str:
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        source = f.read()
    env = Environment(autoescape=True)
    env.filters["g"] = _g
    template = env.from_string(source)
    generated_at = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
    return template.render(
        lot=lot_result,
        meta=meta or {},
        rules_version=rules_version,
        language=language,
        generated_at=generated_at,
    )


def generate_form_pdf(
    lot_result: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    rules_version: str = "",
    language: str = "en",
) -> bytes:
    """Renders Form A (weight) or Form B (volume/length/number) as PDF bytes."""
    import weasyprint

    html = render_form_html(lot_result, meta=meta, rules_version=rules_version, language=language)
    return weasyprint.HTML(string=html).write_pdf()
