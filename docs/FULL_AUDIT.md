# Nirikshan — full cross-check (rules, features, API, UI, UX, NFRs)

Audited against `docs/Nirikshan_PRD_SIH26034.md`, `docs/Nirikshan_UI_Proposal.md` and
`docs/DEMO_SCRIPT.md`, after the all-rules overlay. Priorities are the PRD's own:
**P0** = M1 must-have, **P1** = M3 finale, **P2** = post-SIH.

Verdict up front: the **rules engine is essentially complete (34/35)**, but three promises made
elsewhere in the PRD are not met — **accessibility, the report verification page, and the
benchmark numbers**. Two of those are cheap. One of them is a live demo risk.

---

## 1. Ship-blockers — fix these first

### 1.1 The report QR points nowhere — **demo risk**
`report/render.py` embeds a QR whose payload is `NIRIKSHAN|<sha256>|<rules_version>|<timestamp>`,
and the PRD (§9.2, FR-P2) promises `GET /api/verify/{hash}` as a "public verification page". That
endpoint does not exist, and there is no `/verify` route in the frontend.

The demo script's own words at Step 5 are "court admissibility … embedded SHA-256 image hash and
verification QR". If a judge scans that QR on stage, nothing resolves. Either build the endpoint
(a stored-hash lookup returning scan date, rules_version and verdict) or change the QR to
self-contained text and drop the word "verification" from the script. **~1 hour either way.**

### 1.2 Accessibility is claimed and absent — **weakest point in the whole product**
PRD §7 promises "WCAG 2.1 AA colour contrast (*we check contrast for a living*), screen-reader
labels, Hindi UI". Actual state across all of `frontend/src`:

| Attribute | Occurrences |
|---|---|
| `alt=` | 7 |
| `aria-label`, `aria-live`, `aria-expanded`, `role=`, `tabIndex` | **0** |
| `@media (prefers-reduced-motion)` in CSS | **0** (the JS hook exists and is used, CSS animations are ungated) |

Every interactive element here is a `<button>` or `<input>`, so basic keyboard operation works —
but nothing is announced to a screen reader, the verdict banner does not live-announce, chips do
not expose selected state, and the evidence `<canvas>` has no text alternative at all. A judge who
asks "you check contrast for compliance — is your own UI accessible?" has an easy hit. Worst of
all, R22 *is* a contrast rule, so the irony is legible.

Minimum credible fix (~2–3 hours): `aria-label` on icon-only buttons and the language toggle,
`aria-pressed` on chips, `role="status"`/`aria-live="polite"` on the verdict banner and quality
ribbon, a text summary next to the evidence canvas, `alt` on remaining images, and one
`@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important } }`
block. Then run Lighthouse and put the score on a slide.

### 1.3 Benchmark numbers do not exist
PRD §2.3 and §10 promise field-extraction accuracy, per-rule precision/recall/F1, NEEDS_REVIEW
rate, latency distribution and a 5-user time-on-task study. `make_synthetic_labels.py` and the
benchmark harness exist; **the dataset and the numbers do not**. For a judged project this is worth
more than any remaining feature — even 60 real photos with a per-rule table beats a new rule.

---

## 2. Rules: 34 of 35

Implemented: R01–R17, R19–R35, plus C01–C05 cross-surface conflicts.

**Missing: R18 (Rule 7(2) Table-I — minimum letter/numeral height, 1.0/1.5/2.5/4.0/6.0 mm).**
It needs absolute millimetres, and the Maap scale layer that supplies them is not built:

| ID | Requirement | Pri | Status |
|---|---|---|---|
| FR-M1 | Scale card (ID-1, 4 ArUco markers), ±3%, also drives perspective correction | P1 | Not implemented |
| FR-M2 | Known object (ID-1 card or ₹ coin) in frame, ±5% | P1 | Not implemented |
| FR-M3 | Officer types one measured pack edge → scale from the quad, ±5–8% | P1 | Not implemented |
| — | PDP area per Rule 7(4) (rectangular / cylindrical 40% / other) | P1 | Not implemented |

The overlay added the *ratio-only* half of Maap — clear space (R20), glyph aspect (R19), contrast
(R22) — which is why those work with no scale at all. **FR-M3 is the cheap path to 35/35:** one
numeric input, `CAP_HEIGHT_FRACTION` already exists, R18 becomes arithmetic with a ±5–8% band →
`NEEDS_REVIEW` inside the band, exactly as the PRD specifies.

---

## 3. API §9.2 — 6 of 10 paths, and the paths differ

| PRD path | Status |
|---|---|
| `POST /api/scan` | ✅ (plus `/api/inspect` for multi-panel — an addition, not in the PRD) |
| `POST /api/listing/check` | ✅ new |
| `GET /api/rules` | ✅ — but **no `?version=` parameter**, so "historical catalogue" is unmet |
| `GET /api/health` | ✅ |
| `POST /api/scan/{id}/weigh` | ⚠️ shipped as `POST /api/tol/weigh` (stateless, not scan-scoped) |
| `POST /api/lot` | ⚠️ shipped as `POST /api/tol/lot` + `/api/tol/lot/form` |
| `GET /api/report/{scan_id}.pdf` / `.json` | ⚠️ shipped as `POST /api/report` (no scan-scoped GET) |
| `POST /api/scan/{id}/measure` | ❌ missing (blocked on Maap) |
| `GET /api/verify/{hash}` | ❌ **missing — see 1.1** |
| `GET /api/dashboard/stats` | ❌ missing (FR-G3) |

Undocumented extras worth adding to the PRD so the docs match the build: `POST /api/session`,
`GET /api/session/{code}/results`, `GET /api/session/{code}/stream` (SSE), `GET /api/tol/mpe`.

## 4. Data model §9.1

`Scan`, `Declarations`, `Applicability`, `Finding` ✅ (Finding now carries `measured`-style values
in `extracted` and the trail). `LotTest` ✅ as the `/api/tol/lot` response.
**`Measurement` ❌** (no `scale_method` / `mm_per_px` / `uncertainty_pct` / `pdp_area_cm2`).
**`Case` ❌. `AuditEntry` ❌** — no `prev_hash` / `hash` chain anywhere (see FR-P5 below).

---

## 5. Features by module

### Drishti — capture and OCR
✅ FR-D1 (type/size gates), FR-D3 (EXIF, downscale ≤1600/2400), FR-D4 (RapidOCR CPU), FR-D6
(normalisation, rapidfuzz keys), FR-D7 (bbox-adjacency extraction, no LLM), FR-D8 (multi-panel
merge with provenance), FR-D9 (barcode → GTIN as INFO).
⚠️ **FR-D2 partial** — backend `assess_quality` runs and the UI shows a "Quality Warning" ribbon,
but there is **no Retake button** (the UI proposal §3.2-C specifies one) and **no auto multi-shot
with sharpest-frame selection**.
❌ **FR-D5** — Devanagari *detection* exists (`detect_line_script`, `scripts_detected`); the
Devanagari **recognition model is not wired**, so a Hindi-only pack still fails to read. R23 can
therefore fire on script detection but the declarations come back empty.
❌ FR-D10 local VLM triage (P2, correctly deferred).

### Niyam — rules engine
✅ Verdict semantics, applicability resolver with every branch the PRD lists (26(a), 3, 24,
6(1)(a) Expl. III, 6(1)(d) provisos, 26(c), 6(1)(e) proviso, 6(11) provisos, 6(10)/31),
FR-N1 YAML, FR-N2 semver + content hash, FR-N3 date-aware via `effective_from`/`effective_to` and
`reference_date`, FR-N4 ≥3 positive/≥3 negative fixtures for **every** rule, FR-N5 explain trail.
This module is the strongest part of the build and matches the PRD closely.

### Maap — see §2. Ratio checks ✅, mm scale ❌.

### Tol — net quantity, MPE, lot
✅ FR-T1 (First Schedule Tables I/II, MPE, >MPE and >2×MPE aggravated), FR-T3 (32/80 sample, Sixth
Schedule tare procedure, mean/SD/corrected average, Rule 19(6) criteria), FR-T4 (Form A/B PDF with
signature blocks). ✅ FR-T2 manual half. ❌ FR-T2 Bluetooth/serial (P2), ❌ FR-T5 GTIN cross-check (P2).

### Jaal — e-commerce
✅ FR-J1 (URL fetched server-side + screenshots), FR-J2 (listing text + image OCR → R29/R30),
FR-J3 (present vs missing declarations). ❌ FR-J4 batch CSV (P2).

### Pramaan — evidence and reports
✅ FR-P1 (overlay with colour-coded boxes), FR-P2 (PDF with officer/premises/date, verdict table,
citations, rules version, image SHA-256, QR), FR-P3 (JSON export).
❌ **FR-P4** draft show-cause / notice text — not implemented.
⚠️ **FR-P5** — per-image SHA-256 exists, but **no append-only hash-chained log**. Small build,
directly supports the "court-admissible" claim. High value per hour.
⚠️ UI proposal §3.2-E promises a **"Download evidence PNG"** button; the canvas renders but I found
no export action.

### Nigrani — case management and controller dashboard
❌ FR-G1 (roles, JWT, per-state tenancy), ❌ FR-G2 (Case lifecycle), ❌ FR-G3 (dashboard,
repeat-offender list, CSV), ❌ FR-G4 (IndexedDB offline queue + sync).
Note: **R17 now produces exactly the dual-MRP hits FR-G3's repeat-offender list is meant to
consume** — a read-only dashboard is now a small step with visible payoff.

### Poorv — artwork pre-check
❌ FR-A1–A3 (P2/M4, correctly out of scope).

### Bhasha — language
✅ FR-B1 (EN/HI UI, 136 keys, parity test enforced), FR-B2 (bilingual rule messages, report
language). ⚠️ FR-B3 partial — Hindi keys and messages ✅, Devanagari OCR ❌ (FR-D5).

### Administration
❌ FR-X1 rules editor (read-only `/rules` explorer exists; no diff/publish flow),
❌ FR-X2 editable taxonomy/lexicon (hard-coded), ❌ FR-X3 state notice templates (P2).

---

## 6. UI vs the UI proposal

| Proposal | Status |
|---|---|
| Routes `/`, `/app`, `/review`, `/rules` | ✅ all four, plus new `/listing` |
| `/dashboard` (Task 10) | ❌ not built |
| Landing: hero, "See it work" running the real API on `four_violations.png` with sample fallback | ✅ |
| Inspector: camera tile with `capture="environment"`, context chips, multi-panel thumbnails, sticky scan button | ✅ |
| Analyzing: scan line, stepper, bbox flicker | ✅ (`ScanLine` component) |
| Verdict: banner, count chips counting up, quality ribbon | ✅ banner + chips; ⚠️ ribbon has no Retake |
| Tabs Findings / Evidence / Declarations / Report | ✅ (+ new **Weigh / Lot** tab) |
| Findings grouped FAIL → REVIEW → PASS → N/A, expandable, "Show on image" | ✅ |
| Evidence: sequential boxes, pinch-zoom, tap → bottom sheet / side list | ✅; ❌ PNG download |
| Declarations: cards with confidence bars, mono raw, crimp chip | ✅ |
| Report: officer/premises/remarks/language, PDF + JSON + **Share (Web Share API)** | ✅ PDF/JSON, persisted premises; ❌ Share |
| Review: QR + 6-char pairing, SSE stack, upload fallback | ✅ |
| Rules explorer: search, filters, implemented/planned tags, detail drawer | ✅ — and after the overlay `planned_rules.json` is down to 8 entries, so the page now honestly shows 34 implemented |
| Design system: tokens.css single source, CSS Modules, no Tailwind, motion gated on `useReducedMotion` | ✅ maintained by the new components (MeasurementRows, TolPanel, ListingPage — zero hex literals) |

Overall the UI is ahead of most SIH builds and matches its own proposal closely. The gaps are the
three small affordances (Retake, evidence PNG, Share) and accessibility.

## 7. NFRs §7

| Area | Status |
|---|---|
| Performance (p50 ≤2 s, p95 ≤4 s, CPU-only, ≥20 scans/min) | ⚠️ plausible and designed for, **not measured** — no latency distribution recorded |
| Offline / PWA installable | ✅ PWA, service worker, offline indicator. ❌ capture queue (FR-G4), ❌ on-device OCR (stretch) |
| Device support (Android 10+, mid-range) | ⚠️ untested on a real low-end device as far as the repo shows |
| Determinism | ✅ fixed model + rules version, reproducible verdicts — well executed |
| Security (JWT, RBAC, TLS, hash-chained log, rate limits, validation) | ⚠️ size/type validation ✅, TLS via host ✅; **no auth, no RBAC, no rate limits, no hash chain** |
| Privacy (DPDP-aligned, no third-party calls by default) | ✅ by design; note `/api/listing/check` does make an outbound fetch — user-initiated only, worth one line in the privacy note |
| Deployability (single Docker image + Postgres; HF Spaces) | ✅ Dockerfile, CI to GHCR, Azure Container Apps + HF Space live |
| Accessibility | ❌ see 1.2 |

## 8. Demo script §15 / DEMO_SCRIPT.md — dry-run check

Steps 1–5 all map to working routes. Two snags to fix before the finale:
1. **Step 5 says "verification QR"** — see 1.1. Reword or build the endpoint.
2. The script's rule-count language ("35 rules") should read **34 implemented, 1 pending scale
   calibration** unless you land FR-M3 + R18. Judges do check.
Also: the script does not yet mention the **Weigh / Lot** tab or the **Listing** page, which are now
two of the strongest differentiators. Add ~30 seconds for Form A/B generation — a statutory form
coming out of the tool is the single most credible artefact in the demo.

---

## 9. Recommended order for the time left

| # | Work | Why | Rough effort |
|---|---|---|---|
| 1 | `/api/verify/{hash}` + `/verify` page (or reword the QR) | closes a live demo failure | 1 h |
| 2 | Accessibility pass + Lighthouse score on a slide | the one gap a judge can hit immediately, and R22 makes it ironic | 2–3 h |
| 3 | FR-M3 + **R18** | takes the catalogue to 35/35, no CV needed | 3–4 h |
| 4 | FR-P5 hash-chained audit log | makes "court-admissible" true rather than implied | 2 h |
| 5 | §10 benchmark: 60 real photos, per-rule P/R/F1, latency table | worth more than any feature to a jury | 1 day, parallelisable |
| 6 | Retake button, evidence PNG download, Web Share | three small affordances the UI proposal already promised | 2 h |
| 7 | FR-G3 read-only controller dashboard | high visual impact; R17 already feeds the repeat-offender list | 4–6 h |
| 8 | FR-D5 Devanagari rec model | real capability gain, but needs an owner and ONNX work | 1 day |

State FR-G1/G2 (auth, tenancy, case lifecycle), FR-X1/X2 (rules editor, editable lexicon) and all
P2 items as **designed and scoped, not built**. That is a normal and defensible answer for a
36-hour finale — far better than a half-built auth system in the demo path.
