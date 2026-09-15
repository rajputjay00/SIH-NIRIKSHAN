# Nirikshan — all remaining rules implemented (R17, R19, R20, R22, R29, R30, R31, R32)

The rules catalogue is now complete: **34 of 34 LMPC rules implemented**, plus the 5 cross-surface
conflict checks (C01–C05). `frontend/src/data/planned_rules.json` no longer lists any of these as
planned. Rules version → `0.4.0+<catalogue hash>`.

Backend: **371 tests pass.** Frontend: `vitest` and `npm run build` both pass.

## IMPORTANT — before you apply

If the Antigravity agent already started R20, **discard its changes first** (this overlay includes
R20 plus seven more rules, and the two will collide in `catalogue.yaml`, `predicates.py`,
`applicability.py` and `geometry.py`). Stop the agent, revert its edits, then unzip.

## Apply and run locally

```powershell
# from the repo root: ...\nirikshan by claude\label-check
Expand-Archive -Path ..\..\nirikshan_all_rules.zip -DestinationPath . -Force

cd backend
python -m pytest tests -q                  # expect 371 passed + env-only failures (see below)
uvicorn backend.app.main:app --reload      # or your usual run command, from the repo root

# new terminal
cd frontend
npm install
npx vitest run
npm run build
npm run dev                                # http://localhost:5173
```

Expected failures in any environment without the OCR model or a Devanagari font — both pre-exist
this change and are unrelated to it:
- 11 × `ModuleNotFoundError: rapidocr_onnxruntime` (`test_scan_e2e.py`, `test_synthetic_suite.py`,
  and the OCR-dependent API tests)
- 1 × `test_report.py::test_report_pdf_generation_hi` (fails on the untouched repo too)

## What to click, to see it working

| Where | What |
|---|---|
| Scan form → **Geometry mode** chip | enables R19/R20; scan a label and the finding cards show the measured ratios |
| Findings tab → R20 / R19 / R22 card → expand | clear-space rows per direction, width÷height, contrast ratio, each with "estimated from the photo — confirm with a scale" |
| Review page → **Weigh / Lot** tab | R31 single-pack MPE check; Lot mode → statistics, Rule 19(6) criteria, **Form A/B PDF** |
| New nav item **Listing** (`/listing`) | paste a marketplace URL and/or upload screenshots → R29 present/missing declarations, R30 font parity |
| Scan the same product twice in one session (same session code) | R17 fires on the second scan if the MRP differs |
| `/rules` | all 34 rules now render as implemented |

## Rules added

| Rule | Ref | What it does | Verdicts |
|---|---|---|---|
| R17 | 18(2A) | same commodity (generic name + net qty) seen earlier in the session with a different MRP | PASS / NEEDS_REVIEW / INFO |
| R19 | 7(3) | glyph width ≥ ⅓ height, exempting `1 i I l` | PASS / NEEDS_REVIEW / INFO / N-A |
| R20 | 8(1) | clear space ≥ 1× numeral height above/below, ≥ 2× left/right | PASS / NEEDS_REVIEW / INFO / N-A |
| R22 | 9(1)(b) | luminance contrast of MRP / net-qty numerals vs background | PASS / NEEDS_REVIEW / INFO |
| R29 | 6(10) | Rule 6(1) declarations present on an e-commerce listing | PASS / **FAIL** / N-A |
| R30 | 31 | net quantity in the same font size as the MRP on the listing | PASS / **FAIL** / NEEDS_REVIEW / N-A |
| R31 | 22 + Sch. I | measured net content vs declared, against the MPE | PASS / **FAIL** / NEEDS_REVIEW / INFO |
| R32 | 19–21 + Sch. V–VII | lot sampling, tare, corrected average, Form A/B | PASS / **FAIL** / NEEDS_REVIEW / INFO |

**R19, R20 and R22 never return FAIL — by design.** An OCR line box is not a glyph box, so a
measured miss is `NEEDS_REVIEW` ("officer, confirm with a graduated scale"), never a violation.
R19/R20 are also opt-in: `N/A` unless `geometry_checks=true` is sent. R29/R30 only apply in listing
mode; on a pack scan they are `N/A`, and vice versa — a pack scan's physical rules are `N/A` on a
listing. No officer input → `INFO`, which does not change the overall status.

## New modules

- `backend/nirikshan/geometry.py` — clear space, glyph aspect, Otsu + WCAG contrast, and
  `attach_geometry` / `attach_contrast` hooks.
- `backend/nirikshan/nigrani.py` — dual-MRP matching across session scans; listing HTML → text
  (stdlib `html.parser`, no new scraping dependency); Rule 6(1) presence; font parity.
- `backend/nirikshan/tol.py` — First Schedule MPE tables, single-pack check, Fifth/Sixth Schedule
  lot procedure.
- `backend/nirikshan/report/form_ab.{py,html}` — Seventh Schedule Form A / Form B PDF.

## New API

```
GET  /api/tol/mpe?declared_value=500&unit=g
POST /api/tol/weigh            {declared_value, declared_unit, gross, tare | net, resolution}
POST /api/tol/lot              {lot_size, declared_value, declared_unit, tares[], samples[]}
POST /api/tol/lot/form         same + officer/premises/packer/commodity/lot_id → PDF
POST /api/listing/check        url and/or file_1..file_6, is_import
```
`/api/scan` and `/api/inspect` additionally accept optional form fields `geometry_checks`
("true"/"false"), `weighing` (JSON) and `lot` (JSON).

## Frontend

`components/MeasurementRows/` (measured ratios inside the existing RuleCard explanation area),
`components/TolPanel/` (Weigh / Lot tab), `pages/ListingPage/` (`/listing` route + nav item).
CSS Modules and `styles/tokens.css` variables only — no Tailwind, no new dependency, no hex
literals, motion gated on `useReducedMotion()`. All new strings exist in **both** `en.json` and
`hi.json` (the i18n parity test enforces it).

## Numbers you must confirm before the finale

Statutory values are taken from the Rules. These are **my estimates**, each a named constant with a
comment, and each echoed back in the result so an officer sees what was applied:

| Constant | File | Value | Why it is an estimate |
|---|---|---|---|
| `CAP_HEIGHT_FRACTION` | `geometry.py` | 0.72 | numeral height as a fraction of an OCR line box |
| `GLYPH_WIDTH_FRACTION` | `geometry.py` | 0.80 | ink width as a fraction of character advance |
| `CONTRAST_PASS_RATIO` | `geometry.py` | 3.0 | Rule 9(1)(b) says "contrast", not a number; 3:1 is the WCAG large-text threshold |
| `font_parity` ok / marginal | `nigrani.py` | 0.90 / 0.75 | tolerance for measuring font size from screenshot boxes |
| `LOT_CRITERIA` (T1 allowed) | `tol.py` | 2 (n=32), 5 (n=80) | Fifth Schedule column 4 is an image in most online copies; values follow OIML R 87 — **confirm against G.S.R. 629(E)** |
| `SAMPLE_CORRECTION_FACTOR` | `tol.py` | 0.485 (n=32), 0.295 (n=80) | Sixth Schedule para 10 formula t(0.995,n−1)/√n — **confirm** |
| `LOT_SIZE_THRESHOLD` | `tol.py` | 4000 | lots ≤ 4000 → 32 samples, larger → 80 — **confirm** |

The two marked **confirm** are your PRD §16 open question 3. Everything else is defensible as
"an estimate, clearly labelled, that only ever asks for officer confirmation".

## Known gaps

- R31 is not applied in the Rule 26(a) 10–20 g branch (`test_applicability` asserts that branch is
  exactly `[R06, R12]`). Legally the MPE still applies; one line in `applicability.py` plus that
  test if you want it.
- R16 advanced sticker detection and R33 reflective-barcode hardening are still as they were — this
  overlay does not touch them.
- Bluetooth/serial scale capture (PRD FR-T2) is not included; weights are typed in.
- `/api/listing/check` fetches only the URL the user pastes. No crawling, no batch scraping.
