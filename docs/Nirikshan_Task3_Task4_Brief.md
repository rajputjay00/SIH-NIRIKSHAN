# Nirikshan — Task 3 and Task 4 briefs

Run Task 3 first. Task 4 assumes the repo layout and dev environment from Task 3.
Reference: `Nirikshan_PRD_SIH26034.md` §6.1, §6.2, §8, §9.

---

## Task 3 — Docker Space, static frontend from FastAPI, reproducible dev environment

### Goal
Replace the Gradio/ZeroGPU launcher with a single Docker image that serves the built React app at `/` and the API at `/api`, runs locally with one command, and passes tests without any `PYTHONPATH` hacks.

### Changes

1. **Remove the Gradio/ZeroGPU layer.**
   - Delete `backend/app.py` (Starlette `Mount`, `app_kwargs`, ZeroGPU noop) and the `spaces`/`gradio` dependencies.
   - Hugging Face Space `README.md` front-matter: `sdk: docker`, `app_port: 7860`.

2. **Serve the SPA from FastAPI** (`backend/main.py`).
   - All API routes under an `APIRouter(prefix="/api")`: `/api/health`, `/api/scan`.
   - Mount `StaticFiles(directory="static", html=True)` at `/` **after** the router. Add a catch-all that returns `static/index.html` for unknown non-`/api` paths (SPA fallback).
   - `GET /api/health` returns `{status, model_loaded, model_version, rules_version|null, git_sha}`.

3. **Dockerfile** (multi-stage).
   - Stage 1 `node:20-alpine`: `npm ci && npm run build` in `frontend/` → `dist/`.
   - Stage 2 `python:3.12-slim`: install `backend/requirements.txt`; copy `frontend/dist` → `backend/static`; `CMD uvicorn main:app --host 0.0.0.0 --port 7860`.
   - Use `opencv-python-headless` (not `opencv-python`) — slim images have no libGL.
   - Pin versions: `rapidocr_onnxruntime==1.4.4`, `onnxruntime==1.22.1`, `numpy==2.2.6`, `fastapi`, `uvicorn[standard]`, `python-multipart`, `pillow`, `opencv-python-headless`, `pyyaml`.
   - Warm the OCR model in a FastAPI `lifespan` hook so the first request is not a 3 s cold start.
   - Set `OMP_NUM_THREADS`/`intra_op_num_threads` from env (`NIRIKSHAN_THREADS`, default = CPU count).

4. **Local dev.**
   - `docker-compose.yml`: `backend` (uvicorn `--reload`, port 8000) and `frontend` (Vite dev server, port 5173, proxy `/api` → `backend:8000`).
   - `Makefile` targets: `dev`, `test`, `build`, `lint`.
   - `backend/README.md`: the only supported non-Docker path is a venv: `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt -r requirements-dev.txt`. Document why (the site-packages/PYTHONPATH problem seen in Task 2).

5. **CI** — `.github/workflows/ci.yml`: on push/PR run `pytest` (backend), `npm run build` (frontend), `docker build`.

### Acceptance criteria
- `docker build -t nirikshan .` succeeds; `docker run -p 7860:7860 nirikshan` serves the UI at `http://localhost:7860/` and `GET /api/health` returns `model_loaded: true`.
- Uploading a real label photo through the UI in the container returns OCR lines (no mocks, no `PYTHONPATH`).
- `docker run nirikshan pytest -q` → all tests pass inside the image.
- `docker compose up` gives hot reload on both sides; `VITE_API_URL` unset works via proxy.
- HF Space rebuilt as a Docker Space and reachable; `app.py`, `spaces`, `gradio` gone from the repo.
- Second scan of the same image is faster than the first (warm-up works); timings logged per stage.
- Commit message: `Move to Docker Space; serve SPA from FastAPI; reproducible dev env`.

### Out of scope
No parser, rules or UI feature work in this task.

---

## Task 4 — Declarations extractor, applicability resolver, rules engine v0.1 (18 rules), evidence overlay

### Goal
Turn raw OCR lines into a rule-by-rule compliance verdict with evidence, per PRD §6.2. Deterministic, tested, no LLM.

### Backend package layout
```
backend/nirikshan/
  __init__.py
  schema.py          # pydantic models: OCRLine, Field, Declarations, Applicability, Finding, ScanResult
  normalize.py       # text normalisation helpers
  extract.py         # OCR lines -> Declarations
  applicability.py   # context + declarations -> applicable rule ids + reasons
  rules/
    catalogue.yaml   # the rules (data)
    engine.py        # YAML evaluator
    predicates.py    # present, regex, unit_matches, magnitude_unit_consistent, approx_equal, script_in, phone, email, pin
  version.py         # rules_version = "0.1.0+" + sha256(catalogue.yaml)[:12]; model_version
```

### 4.1 `normalize.py`
- `squash(text)`: lowercase, strip, remove all whitespace → used for key matching (`"NET QUANTITY"`, `"NETQUANTITY"`, `"Net Qty."` all match).
- Confusion map applied only inside numeric contexts: `O→0`, `l/I→1`, `S→5`, `B→8`.
- Devanagari digits `०-९` → ASCII (prepares for Task 6).
- Currency tokens: `₹`, `Rs`, `Rs.`, `INR`, `र`, `रु` → `INR`.
- Unit tokens (keep `raw_unit`, set `unit_nonstandard=True` for anything not in the standard set):
  standard `g, kg, ml, L, l, cm, m, N, U, piece(s), pcs, pair, set`; nonstandard `gm, gms, grams, ltr, lt, litre, oz, lb, doz, dozen`.

### 4.2 `extract.py`
- Key lexicon (English now; Hindi keys added in Task 6): manufacturer keys (`mfd by, manufactured by, mfg by, made by`), packer (`packed by, pkd by`), importer (`imported by`), marketer (`marketed by`), origin (`country of origin, made in`), net quantity (`net qty, net quantity, net wt, net weight, net vol, net volume, net content(s), contents`), mrp (`mrp, m.r.p, max retail price, maximum retail price`), dates (`mfd, mfg date, date of mfg, pkd, packed on, date of import, best before, use by, exp`), consumer care (`consumer care, customer care, consumer complaints, for feedback`), unit sale price (`unit sale price, usp, per 100 g, per kg` patterns).
- Layout-aware value resolution, in order: same line after the key; the line immediately below whose bbox overlaps horizontally; the line to the right on the same baseline. Never skip more than 2 lines.
- Consumer care block: from the key line, absorb following lines until a blank gap > 1.5× line height; extract `phone` (10-digit or 1800/1860), `email`, remaining text → `name/address`.
- Manufacturer/packer/importer blocks: same absorption logic; extract 6-digit `pin`, state name via a list.
- Every `Field` = `{value, raw, bbox (union of source line quads), confidence (min of source lines), source_line_ids[]}`.
- Net quantity: parse `value` (float), `unit`, `raw_unit`, `count` when "N ×" pattern present; MRP: `value`, `currency`, `incl_taxes_phrase: bool`; USP: `value`, `per_unit`.
- `scripts_detected`: `latin`, `devanagari`, `other` per line (Unicode ranges).

### 4.3 `applicability.py`
Inputs: `package_type` (retail | wholesale | multi_piece | combination | export | not_for_retail; default retail), `category` (general | food | cosmetic | drug | seed | alcohol | lpg | bidi_incense | electronics | textile | sheets | container; default general), `is_import` (bool, default inferred from importer key), `channel` (physical | ecommerce; default physical), `net_quantity` (from extraction or supplied).
Emit `Applicability{package_type, category, is_import, channel, exempt_reason, applicable_rule_ids[], reasons{rule_id: text}}` implementing:
- Rule 26(a): ≤10 g/ml → no rules apply (exempt_reason set); 10–20 g/ml → only R06 and R12.
- Rule 3: >25 kg/L or `not_for_retail` → Chapter II rules N/A.
- Rule 24: wholesale → only R27.
- food: R01/R02 and R10 marked N/A with reason "per FSS Act (Rule 6(1)(a) Expl. III, 6(1)(d) proviso)"; R35 reported as INFO.
- cosmetic: R10 N/A (D&C Rules); seed: R10 N/A; bidi_incense: R10 and R12 N/A; lpg: R10, R12 N/A; alcohol: R12 N/A (state excise); drug: all N/A (Rule 26(c)).
- R04 only when `is_import`.
- R14 N/A when `package_type in (multi_piece, combination)` or when net quantity is exactly 1 kg/1 L/1 m/1 unit.

### 4.4 `rules/catalogue.yaml` — 18 rules in v0.1
R01, R02, R04, R05, R06, R07, R08, R09, R10, R11, R12, R14, R15, R23, R25, R26, R27, R35 (definitions in PRD §6.2 table). Schema per rule:
```yaml
- id: R12
  key: LMPC.6.1.e.MRP_INCL_TAXES
  rule_ref: "Rule 6(1)(e) read with Rule 2(m)"
  title_en: ...
  title_hi: ...
  severity: high | medium | low
  check: { all: [ {present: decl.mrp.value}, {regex: {field: decl.mrp.raw, pattern: "..."}}, ... ] }
  on_fail: FAIL
  on_uncertain: { when: "decl.mrp.confidence < 0.75", verdict: NEEDS_REVIEW }
  evidence: decl.mrp.bbox
  message_en: ...
  message_hi: ...
  fix_hint_en: ...
  effective_from: "2018-01-01"
  source: "G.S.R. 629(E), 23 June 2017"
```
Applicability is decided by `applicability.py`, not in YAML; rules not in `applicable_rule_ids` produce `N/A` findings with the resolver's reason.

Predicates to implement in `predicates.py`: `present`, `absent`, `regex`, `unit_matches` (g if <1 kg etc.), `magnitude_unit_consistent` (1500 g → FAIL, 0.5 kg → FAIL), `unit_standard`, `approx_equal` (USP vs MRP ÷ normalised quantity, tol 1% or ₹0.01), `script_in`, `phone`, `email`, `pin`, `no_qualifier_words` (approx, about, minimum, not less than, average), `no_count_words` (dozen, score, gross).

### 4.5 `engine.py` and API
- `evaluate(declarations, applicability, catalogue) -> list[Finding]`; `Finding{rule_id, rule_ref, verdict, severity, extracted, expected, evidence_bbox, message_en, message_hi, fix_hint_en}`.
- `summary`: `status` = Compliant | Non-compliant | Officer review required; counts by verdict.
- `POST /api/scan` accepts optional form fields `package_type, category, is_import, channel, net_quantity`; response:
  `{ocr, declarations, applicability, findings, summary, rules_version, model_version, timings{preprocess_ms, ocr_ms, extract_ms, rules_ms}}`.
- `GET /api/rules` returns the catalogue and `rules_version`.

### 4.6 Tests and fixtures
- `backend/tests/fixtures/lines/<rule>_<pass|fail>_<n>.json`: OCR-line JSON (text, confidence, bbox) so rule tests bypass OCR. **≥3 positive and ≥3 negative per rule**, including whitespace-collapsed variants (`NETQUANTITY`, `MRPRs.45`).
- `backend/tests/test_extract.py`, `test_applicability.py`, `test_rules.py` (parametrised over fixtures), `test_scan_e2e.py` (marked `slow`): 6 synthetic label PNGs generated by `scripts/make_synthetic_labels.py` using a real TTF (DejaVuSans, 28–40 px), run through real OCR, expected verdicts asserted.
- Regression guard: `test_rules_version.py` fails if `catalogue.yaml` hash changes without bumping the version string.

### 4.7 Frontend
- Context form above upload: package type, category, import checkbox (defaults retail/general/unchecked).
- Results: summary banner; findings table (rule ref, verdict badge, message, expand → extracted/expected/fix hint); `N/A` rows collapsed under "Not applicable (n)".
- Evidence overlay: render the image on a `<canvas>`, draw each finding's `evidence_bbox` (green PASS, red FAIL, amber NEEDS_REVIEW); clicking a table row highlights its box. "Download evidence PNG" button.
- Keep the raw OCR panel behind a toggle.

### Acceptance criteria
- On the six synthetic labels: expected verdicts exactly; on the two "clean" ones, zero FAIL and ≤1 NEEDS_REVIEW.
- A label with `Net Wt 200 gms`, `MRP Rs 45` (no tax phrase), consumer care without e-mail, `Imported by` but no origin → R08, R12, R15, R04 FAIL, each with a non-empty `evidence_bbox`.
- A 10 g sachet with `net_quantity=10 g` → every finding `N/A` with `exempt_reason` = Rule 26(a); at 15 g only R06 and R12 evaluated.
- `category=food` → R01/R02/R10 `N/A` with the FSS reason; R12/R06/R15 still evaluated.
- `rules_version` present in every response and changes when the YAML changes.
- All tests pass in Docker; `pytest -m "not slow"` runs under 10 s.
- Commit message: `Add declarations extractor, applicability resolver, rules engine v0.1 (18 rules) and evidence overlay`.

### Out of scope (later tasks)
Geometry/scale card (Task 5), Devanagari OCR and Hindi keys (Task 6), PDF report and hash chain (Task 7), lot/MPE module (Task 8), e-commerce mode (Task 9), dashboard (Task 10).
