# Nirikshan — Product Requirements Document

**Rules-as-code compliance checking for packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011**

| | |
|---|---|
| Problem statement | **SIH26034** — Software System to check compliance of Packaged Commodities under Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels |
| Organisation | Ministry of Consumer Affairs, Food & Public Distribution — Department of Consumer Affairs (Legal Metrology Division) |
| Category | Software |
| Team | _________________ (team name / college / SPOC) |
| Version / date | v1.0 — 12 September 2026 |
| Status | Draft for internal hackathon → idea submission → finale build |

---

## 0. The pitch in 60 seconds

**Nirikshan** (निरीक्षण, "inspection") turns a phone photo of a package into a rule-by-rule compliance verdict under the LMPC Rules 2011, with every finding tied to the exact rule, the exact OCR line and the exact pixels that justify it.

It does three things no label scanner does together today:

1. **It checks the Rules as written, not a checklist.** 35 encoded checks cover presence, wording, units, arithmetic (unit sale price vs MRP), geometry (Rule 7 letter heights, Rule 8 clear space, Rule 9 contrast) and *applicability* (exemptions for ≤10 g packs, wholesale packs, food/cosmetic/drug carve-outs). Rules live as versioned YAML keyed to amendment dates. When the Ministry notifies the next amendment, the rules file changes; the code doesn't.
2. **It checks the product, not only the label.** The PS says "products, images and labels". Nirikshan accepts weighing-scale readings, applies the First Schedule maximum-permissible-error (MPE) table, runs the Fifth/Sixth Schedule sampling and corrected-average procedure, and prints the Seventh Schedule Form A/B data sheet that an officer fills by hand today.
3. **It produces evidence, not opinions.** Annotated image, hash-chained audit log, rule citation and a draft notice, generated offline on CPU, in Hindi or English, with no cloud AI in the loop. Anything the system is not sure about is `NEEDS_REVIEW`, never a guess.

**Why this wins.** Most entries for this PS will be "OCR → LLM → checklist". That is a prototype. Nirikshan is the tool a Legal Metrology Officer could carry into a market tomorrow, a Controller could run a district from, and a manufacturer could use to fix artwork before it is printed.

---

## 1. Problem

### 1.1 The regulation in one paragraph

Every pre-packaged commodity sold at retail in India must carry a fixed set of declarations: who manufactured, packed or imported it and their complete address; the common or generic name; net quantity in standard units; month and year of manufacture, packing or import; best-before where relevant; MRP inclusive of all taxes; unit sale price; consumer-care contact; and country of origin for imports (Rule 6). The Rules also govern *how* declarations appear: minimum letter and numeral heights scaled to the principal display panel (PDP) area (Rule 7), clear space around the quantity (Rule 8), contrast and language (Rule 9). They prohibit stickers that alter declarations, dual MRPs on identical goods, misleading qualifiers such as "approx." and non-SI units (Rules 6(3), 18(2A), 12(6), 13). Net contents are policed with the MPE table (First Schedule) and a statutory sampling and testing procedure (Rules 19–22, Schedules V–VII). Offences under Section 36 of the Legal Metrology Act 2009 escalate from fines to imprisonment on repeat; many are compoundable (Rule 32A). Major amendments: 2015 (consumer care details), 2017 (e-commerce, country of origin, best-before, new font table), 2021–22 (unit sale price, Second Schedule standard quantities removed, simplified MRP format), 2023 (e-commerce loose commodities, multi-piece packages).

### 1.2 Who is failed by the status quo

| Stakeholder | Today | Pain |
|---|---|---|
| Legal Metrology Officer / Inspector (state departments) | Reads each pack by eye, measures fonts with a ruler, writes Form A by hand, photographs on a personal phone | Slow, inconsistent between officers, weak evidence trail, disputes in court over "was the font really 1.2 mm" |
| Controller of Legal Metrology (state) | Paper registers and spreadsheets from districts | No aggregate view; repeat offenders across districts invisible; can't target inspections |
| Manufacturer / MSME packaging team | Consultancy audits at ₹ per label, days per turnaround; ~150 checkpoints to get right | Violations discovered after printing → relabel, recall, compounding fees |
| E-commerce marketplace compliance | Rule 6(10) obligations across millions of listings | No scalable way to verify seller-uploaded declarations |
| Consumer | Sees a label, cannot tell if it is lawful | Short-weight and MRP abuse go unreported |

### 1.3 Why existing approaches fall short

- **Manual inspection**: doesn't scale, no evidence standardisation.
- **Generic OCR apps**: extract text, know nothing about the Rules.
- **LLM/VLM-only prototypes** (what most hackathon teams will build): non-deterministic (two scans, two answers), hallucinate rule text, cannot measure millimetres, need cloud APIs, per-call cost, and send government inspection data off-premises.
- **Consultancy label audits**: correct but expensive and pre-market only; useless for field enforcement.

---

## 2. Goals, non-goals and success metrics

### 2.1 Goals

| ID | Goal |
|---|---|
| G1 | A Legal Metrology Officer gets a defensible, rule-cited compliance verdict for a retail package in under 10 seconds from a phone photo, online or offline. |
| G2 | Every FAIL is traceable: rule reference → requirement text → extracted value → image evidence. Zero un-cited findings. |
| G3 | The system covers the *whole* inspection, not just the label: declarations, geometry, net-quantity error, lot sampling, statutory forms. |
| G4 | Rules are data. A new amendment is a YAML change with an effective date, reviewed and versioned, not a code release. |
| G5 | Works in Hindi and English (Rule 9(4)) on a ₹10,000 Android phone with intermittent connectivity. |
| G6 | Deployable on government infrastructure with no external AI dependency. |

### 2.2 Non-goals (v1)

- Legal determination. Nirikshan is a review aid; the officer decides and signs.
- FSSAI, BIS, Drugs & Cosmetics or AGMARK content checks (out of scope, but the applicability resolver knows where LMPC stops and those laws start).
- Counterfeit / brand-authenticity detection.
- Automated scraping of marketplaces at scale (v1 checks a listing the user supplies).

### 2.3 Success metrics

| Metric | Internal round target | Finale target |
|---|---|---|
| Field extraction accuracy (exact match, 8 core fields) on NirikshanBench | ≥ 85% | ≥ 92% |
| Rule-level precision / recall (FAIL vs ground truth) | ≥ 0.85 / 0.80 | ≥ 0.92 / 0.90 |
| `NEEDS_REVIEW` rate on clean photos | ≤ 30% | ≤ 15% |
| End-to-end latency, p50 / p95 (2 vCPU, no GPU) | 3 s / 6 s | 2 s / 4 s |
| Officer time per package (label + weighing + form) | — | ≤ 90 s vs ~10 min manual (measured in user test) |
| Rule catalogue coverage (rules encoded / rules identified) | 18 / 35 | 35 / 35 |
| Hindi (Devanagari) declaration recall | — | ≥ 85% |

---

## 3. Users and jobs to be done

| Persona | Job to be done | Key screens |
|---|---|---|
| **Inspector (LMO)** — field officer, Android phone, 30–60 packs/day, often no signal in mandis | "Tell me what's wrong with this pack, prove it, and fill my form." | Scan → Verdict → Evidence → Weigh → Form A → Case |
| **Controller** — state HQ, wants targeting and statistics | "Where are violations concentrated, who repeats, what did my officers find this month?" | Dashboard, repeat-offender list, export |
| **Manufacturer / MSME packaging lead** | "Is my artwork legal before I print 2 lakh pouches?" | Upload artwork PDF/PNG → exact measurements → fix list |
| **Marketplace compliance analyst** | "Does this seller listing carry the Rule 6(10) declarations?" | Paste listing URL / upload screenshots → findings |
| **Consumer** (Phase 3) | "Is this pack short-weight or over-MRP? Report it." | Scan → plain-language result → report to NCH/INGRAM |

---

## 4. Product principles

1. **Deterministic core.** Same image, same rules version → same verdict. AI is used for reading (OCR), never for judging.
2. **Cite or shut up.** A finding without a rule reference and evidence crop is a bug.
3. **Conservative by design.** Uncertain reads, marginal measurements and unrecognised formats become `NEEDS_REVIEW` with an instruction to the officer, not a FAIL.
4. **Applicability first.** Decide *which* rules apply (exempt pack? wholesale? food? import?) before checking any of them. Wrong-rule findings destroy officer trust faster than missed ones.
5. **Offline-first, CPU-only.** Field reality is a 2G signal and a mid-range phone.
6. **Rules as data, forms as templates.** Amendments and state-specific notice formats are configuration.
7. **Human in the loop, machine in the log.** The officer signs; the system records what it saw, when, with what rules version.

---

## 5. Scope and phasing

| Phase | Gate | Scope |
|---|---|---|
| **M0 — Done** | — | React + FastAPI skeleton; RapidOCR (CPU) on `/scan`; upload validation; tests; HF Space |
| **M1 — Internal hackathon** | College shortlist (50 teams) | P0 features: applicability resolver, 18 core rules, evidence overlay, PDF report, bilingual UI, demo dataset (60 labels), pitch deck |
| **M2 — Idea submission / nomination** | SPOC nomination → national screening | PRD, architecture, benchmark numbers, video demo, letter of interest from a state LM office or consumer body (stretch) |
| **M3 — Grand finale (36 h)** | Finale jury | P1 features: full 35-rule catalogue, geometry checks with scale card, MPE + lot module + Form A/B, e-commerce mode, controller dashboard, Devanagari OCR, on-device OCR (stretch) |
| **M4 — Pilot** | Post-SIH | P2: manufacturer artwork pre-check, consumer mode, eMaap/state-portal integration, GS1 GTIN enrichment |

Priority key: **P0** must-have for M1, **P1** for M3, **P2** post-SIH.

---

## 6. Functional requirements

Modules carry short Hindi codenames so the team and judges can refer to them quickly.

### 6.1 Drishti — capture and OCR

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-D1 | Accept JPEG/PNG/WebP ≤ 10 MB via camera or upload; reject others with 415/413 (done). | P0 | M0 |
| FR-D2 | Guided capture overlay: frame the PDP, glare and blur warnings (Laplacian variance, specular-highlight ratio), auto multi-shot (3 frames) with sharpest-frame selection. | P0 | M1 |
| FR-D3 | Pre-processing: EXIF orientation, perspective correction (document quad detection or ArUco scale card), adaptive contrast, downscale to ≤1600 px long edge. | P0 | M1 |
| FR-D4 | OCR with RapidOCR (PP-OCR det + rec, ONNX Runtime CPU). Output lines with text, confidence, quad bbox. | P0 | M0 |
| FR-D5 | Devanagari recognition model (PaddleOCR `devanagari` rec, ONNX) run on the same detected boxes; script detection per line; Devanagari digits ०–९ normalised to ASCII. | P1 | M3 |
| FR-D6 | Post-OCR normalisation: whitespace-tolerant matching, common confusions (0/O, 1/l/I, 5/S, 8/B), unit tokens (`gms`→flag, `ltr`→flag, `Rs.`/`₹`/`INR`), fuzzy key matching (rapidfuzz) for label keys: Net Qty / Net Wt / Net Quantity, MRP / M.R.P. / Max Retail Price, Mfd / Mfg / Pkd / Packed on / Date of Import, Best Before / Use By, Customer Care / Consumer Care, Mfd by / Manufactured by / Packed by / Imported by / Marketed by, Country of Origin / Made in, Unit Sale Price / USP. | P0 | M1 |
| FR-D7 | Layout-aware key→value extraction using bbox adjacency (same line, next line below, right of colon), not an LLM. Produce the canonical `Declarations` object (§9.1) with per-field `value`, `raw`, `bbox`, `confidence`, `source_line_ids`. | P0 | M1 |
| FR-D8 | Multi-panel scans: allow 2–4 photos of one pack (front / back / side); merge extractions, keep panel provenance. | P1 | M3 |
| FR-D9 | Barcode / QR decode (pyzbar/zxing) → GTIN captured as INFO (Rule 6(4A) permits these). | P1 | M3 |
| FR-D10 | Optional local VLM triage for `NEEDS_REVIEW` lines only (small open-weight model, off by default, never changes a PASS/FAIL). | P2 | M4 |

### 6.2 Niyam — rules engine

**Verdict semantics.** Each rule returns one of `PASS`, `FAIL`, `NEEDS_REVIEW` (uncertain read or measurement), `N/A` (rule not applicable to this package), `MANUAL` (checklist item the officer confirms). Overall status: *Compliant* (no FAIL, no open NEEDS_REVIEW), *Non-compliant* (≥1 FAIL), *Officer review required*. A weighted score is shown for manufacturers only; enforcement is per-rule, not a score.

**Applicability resolver (runs first).** Inputs: net quantity (parsed or entered), package type (retail / wholesale / multi-piece / combination / export / "not for retail sale"), commodity category (general / food / cosmetic / drug / seed / alcohol / LPG / bidi & incense / electronics & spares / textile / sheets / containers), import flag, sale channel (physical / e-commerce). Output: the set of applicable rule IDs with reasons. Decision points encoded:

- Rule 26(a): ≤ 10 g/ml → all rules N/A; 10–20 g/ml → only MRP and net quantity apply.
- Rule 3: > 25 kg/25 L, cement/fertiliser/farm produce > 50 kg bags, industrial/institutional packs → Chapter II N/A.
- Rule 24: wholesale package → only name/address, identity, count or net quantity.
- Rule 6(1)(a) Expl. III and Rule 7(5): food → name/address and date per FSS Act; LMPC font rules apply only to net quantity, MRP, best-before and consumer care.
- Rule 6(1)(d) provisos: cosmetics dates per Drugs & Cosmetics Rules; certified seeds exempt from date; bidi, incense sticks and PSU LPG exempt from date; bidi and APM LPG exempt from MRP.
- Rule 26(c): DPCO-scheduled formulations exempt (medical devices not).
- Rule 6(1)(e) proviso: alcoholic beverages → state excise MRP regime.
- Rule 6(11) provisos: unit sale price N/A where MRP equals unit price, and for combination, group and multi-piece packages (2023 amendment).
- Rule 6(10) / Rule 31: e-commerce listing mode.

**Rule catalogue (v1.0).** Rule references are to the LMPC Rules 2011 as amended. "Method" is the deterministic check; geometry rules depend on §6.3.

| ID | Rule | Requirement (paraphrased) | Method | Output |
|---|---|---|---|---|
| R01 | 6(1)(a) | Name and address of manufacturer; of packer too if different; of importer for imports | Detect role keys + entity block | FAIL if none |
| R02 | 10(1) Expl. I | "Complete address": premises, street, city, state, PIN | 6-digit PIN regex, state-name lookup | FAIL (no PIN) / NEEDS_REVIEW |
| R03 | 6(1)(a) Expl. I–II | Responsible entity: unqualified name = manufacturer; brand owner shown as marketer is deemed responsible; first-listed manufacturer prosecuted | Derive `responsible_entity` for the notice | INFO |
| R04 | 6(1)(aa) | Country of origin / manufacture / assembly on imported packs | If importer key found, require origin key | FAIL |
| R05 | 6(1)(b) | Common or generic name; multi-product packs list name and quantity of each | Generic-name heuristic (not brand-only), commodity lexicon | NEEDS_REVIEW if brand only |
| R06 | 6(1)(c), 12, 13(2)–(3) | Net quantity in SI units; g below 1 kg, kg at/above; ml below 1 L, L at/above; cm/m; number as N/U/piece/pair/set | Parse value+unit; unit–magnitude consistency (e.g. "1500 g" → should be kg; "0.5 kg" → should be g) | FAIL |
| R07 | 13(4) | No dozen, score, gross, great gross | Regex | FAIL |
| R08 | 13(5) | SI units only; 'L' permitted for litre; non-standard abbreviations (gms, ltr, oz, lb) | Unit token whitelist | FAIL (configurable severity) |
| R09 | 12(6) | No qualifiers creating a misleading impression of quantity: minimum, not less than, average, about, approximately | Regex within net-quantity line | FAIL |
| R10 | 6(1)(d) | Month and year of manufacture / pre-packing / import, in words or numerals; category exceptions via resolver | Date regex (MM/YYYY, Mon-YYYY, DD/MM/YYYY) near Mfd/Pkd/Imported keys | FAIL / N/A |
| R11 | 6(1)(da) | Best-before or use-by for goods that become unfit over time (unless another law provides) | Presence when category perishable | NEEDS_REVIEW |
| R12 | 6(1)(e), 2(m) | MRP declared as maximum retail price in ₹/Rs, inclusive of all taxes | Regex: MRP key + amount + "incl(usive)? of all taxes" | FAIL if phrase or currency missing |
| R13 | 6(1)(e) | Paise rounding (nearest rupee / 50 paise, 2017 text; relaxed by 2022 amendment) | Numeric check gated by rules version | WARN |
| R14 | 6(11) | Unit sale price in ₹ per g/kg, ml/L, cm/m or unit, two decimals; N/A where equal to MRP or for multi-piece/combination/group packs | Presence + arithmetic: USP ≈ MRP ÷ quantity (±1% or ±₹0.01) | FAIL / N/A |
| R15 | 6(2) | Consumer care: name, address, telephone, e-mail | Phone regex (10-digit, 1800-xxx), email regex, name/address block | FAIL per missing element |
| R16 | 6(3)–(4) | No stickers altering mandatory declarations; a lower-MRP sticker is allowed only if it does not cover the original MRP | Second-MRP detection; sticker edge/colour discontinuity heuristic | NEEDS_REVIEW |
| R17 | 18(2A) | No different MRPs for an identical pre-packaged commodity | Cross-scan match on (brand, generic name, net quantity) → differing MRPs | WARN + case link |
| R18 | 7(2) Table-I | Minimum letter/numeral height by PDP area: 1.0 / 1.5 / 2.5 / 4.0 / 6.0 mm (1.5 / 3.0 / 4.0 / 6.0 / 6.0 mm if moulded) | mm-per-px scale × bbox height; PDP area per 7(4) | FAIL / NEEDS_REVIEW with ± uncertainty |
| R19 | 7(3) | Width of letter/numeral ≥ one-third of height (except 1, i, I, l) | Glyph aspect from character segmentation | NEEDS_REVIEW |
| R20 | 8(1) | Clear space around net-quantity declaration: ≥ 1× numeral height above/below, ≥ 2× left/right | Bbox gap geometry | FAIL / NEEDS_REVIEW |
| R21 | 9(1)(a) | Declarations legible and prominent | OCR confidence + blur score thresholds | NEEDS_REVIEW |
| R22 | 9(1)(b) | MRP and net-quantity numerals in a colour contrasting with background (moulded glass/plastic excepted) | Luminance contrast ratio within bbox (Otsu foreground vs background) | NEEDS_REVIEW below threshold |
| R23 | 9(4) | Declarations in Hindi (Devanagari) or English; other languages only in addition | Script detection on key declarations | FAIL if neither script |
| R24 | 9(2)–(3) | Not read through liquid; outer wrapper carries declarations unless transparent | Officer checklist | MANUAL |
| R25 | 26(a) | Exemption ≤ 10 g/ml; 10–20 g/ml only MRP + net quantity | Applicability resolver | N/A gating |
| R26 | 3 | > 25 kg/L, > 50 kg bags of cement/fertiliser/farm produce, industrial/institutional packs excluded | Resolver ("not for retail sale" key) | N/A gating |
| R27 | 24 | Wholesale package: name/address, identity, count or net quantity | Wholesale mode | FAIL |
| R28 | 6(5) | Multi-component commodity: declarations on main pack plus information about accompanying packs | Officer checklist | MANUAL |
| R29 | 6(10) | E-commerce: mandatory Rule 6(1) declarations displayed on the platform (subject to the sub-rule's exceptions) | Listing mode: parse title, bullets, spec table, images | FAIL |
| R30 | 31 | Advertisement/listing quoting MRP must show net quantity in the same font size | Listing mode: compare rendered text sizes / image bbox heights | FAIL / NEEDS_REVIEW |
| R31 | 22, First Schedule | Net-quantity deficiency within MPE (Table I by weight/volume; Table II by length/area/number) | Weighing input → MPE calc; flag > MPE and > 2× MPE | FAIL |
| R32 | 19–21, Schedules V–VII | Lot sampling (32 / 80), tare procedure, corrected average, approval criteria, Form A/B | Lot module (§6.4) | REPORT |
| R33 | 6(4A) | Barcode/GTIN/QR, e-code, scheme logos permitted in addition | Decode, enrich | INFO |
| R34 | 6(1)(f), 14–17 | Dimensions for textiles, sheets (usable sheet count and size), container-type goods | Category-specific prompts | NEEDS_REVIEW |
| R35 | 7(5), 6(1)(a) Expl. III | For goods under another law (FSS Act etc.) LMPC font rules apply only to net quantity, MRP, expiry/best-before and consumer care | Resolver | Gating |

**Rules-as-code requirements**

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-N1 | Rules stored as YAML (Appendix B): id, rule ref, applicability predicate, check, severity, evidence field, message (en/hi), `effective_from`/`effective_to`, source URL to the notification. | P0 | M1 |
| FR-N2 | Rules versioned in git; each scan records `rules_version` (semantic version + content hash) so a verdict can be reproduced later in court. | P0 | M1 |
| FR-N3 | Evaluate against the rules in force on the scan date (or a date the officer selects, e.g. the pack's manufacture month). | P1 | M3 |
| FR-N4 | Regression suite: every rule has ≥ 3 positive and ≥ 3 negative fixture labels; CI fails on any verdict change without a rules-version bump. | P0 | M1 |
| FR-N5 | "Explain" panel per finding: rule excerpt, our interpretation, extracted value, evidence crop, and for manufacturers a "how to fix". | P0 | M1 |

### 6.3 Maap — geometry and measurement

Rule 7, 8 and 9 checks need millimetres, and a photo has only pixels. Nirikshan establishes a mm-per-pixel scale by one of four methods, each with a stated uncertainty:

| ID | Method | Uncertainty | Pri |
|---|---|---|---|
| FR-M1 | **Nirikshan scale card**: a printable card (ID-1 size, 85.60 × 53.98 mm) with four ArUco markers placed beside the pack; markers also drive perspective correction. | ±3% | P1 |
| FR-M2 | **Known object**: any ID-1 card (bank/PAN/Aadhaar card) or a ₹ coin detected in frame. | ±5% | P1 |
| FR-M3 | **Declared dimension**: officer enters one measured edge of the pack (e.g. width 120 mm); scale from the detected package quad. | ±5–8% | P1 |
| FR-M4 | **Artwork mode**: vector PDF/AI export → exact heights, no estimation (§6.8). | 0 | P2 |

Derived checks: letter/numeral height (cap-height of the OCR box, corrected for descenders), width/height ratio, clear-space distances (Rule 8), PDP area per Rule 7(4) (rectangular: height × width of the panel; cylindrical: 40% of height × circumference; other: 40% of total surface, entered by officer). Any measurement within the uncertainty band of a threshold is `NEEDS_REVIEW` with the instruction "confirm with a graduated scale", never FAIL.

### 6.4 Tol — net quantity, MPE and lot inspection

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-T1 | Single-pack check: officer enters gross and tare (or net) weight/volume/length/count; system applies First Schedule Table I/II, shows MPE in g/ml/% and the deficiency; flags > MPE (FAIL) and > 2× MPE (aggravated). | P1 | M3 |
| FR-T2 | Weighing-scale input: manual entry (P1); Bluetooth/serial capture from Class III scales (P2). | P1/P2 | M3/M4 |
| FR-T3 | Lot mode per Rule 19 and Fifth Schedule: sample size 32 (lot < 4000) or 80; tare procedure per Sixth Schedule para 3 (single tare if ≤ 0.3 × MPE, else five tares and average if spread ≤ 0.4 × MPE); mean, standard deviation and corrected average per paras 8–10; approval criteria per Rule 19(6). | P1 | M3 |
| FR-T4 | Generate Seventh Schedule **Form A** (weight) / **Form B** (volume/length) data sheet as PDF, pre-filled, with signature blocks. | P1 | M3 |
| FR-T5 | Cross-check declared net quantity vs GTIN master data where available (GS1 India DataKart) as INFO. | P2 | M4 |

### 6.5 Jaal — e-commerce listing mode

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-J1 | Input: listing URL (fetched server-side where permitted) or uploaded screenshots + product images. | P1 | M3 |
| FR-J2 | Extract declarations from listing text (title, bullets, specification table) and from product images via Drishti; evaluate R29 (Rule 6(10)) and R30 (Rule 31 font parity). | P1 | M3 |
| FR-J3 | Report which declarations are present on the platform vs only on the physical pack image. | P1 | M3 |
| FR-J4 | Batch mode (CSV of URLs) for marketplace compliance teams; per-seller summaries. | P2 | M4 |

### 6.6 Pramaan — evidence and reports

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-P1 | Evidence overlay: original image with colour-coded boxes (green PASS, red FAIL, amber NEEDS_REVIEW) and rule tags; downloadable PNG. | P0 | M1 |
| FR-P2 | Inspection report PDF: header (officer, place, date/time, GPS if permitted), verdict table with rule citations, evidence crops, rules version, SHA-256 of each original image, QR code to an online verification page. | P0 | M1 |
| FR-P3 | Machine-readable JSON export of the full `Declarations` + `Findings` objects. | P0 | M1 |
| FR-P4 | Draft show-cause / notice text from a state-configurable template, pre-filled with responsible entity (R03), findings and Section 36 / Rule 32A references. Officer edits before use. | P1 | M3 |
| FR-P5 | Append-only, hash-chained audit log (each entry hashes the previous) for scans, edits and sign-offs. | P1 | M3 |

### 6.7 Nigrani — case management and controller dashboard

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-G1 | Roles: Inspector, Controller, Admin, Manufacturer, Consumer (read-only). JWT auth, per-state tenancy. | P1 | M3 |
| FR-G2 | Case = one pack or lot at one premises; states: Open → Notice drafted → Compounded / Prosecuted / Closed. | P1 | M3 |
| FR-G3 | Dashboard: violations by rule, commodity category, manufacturer, district and month; repeat-offender list (R17 dual-MRP hits, ≥ 3 FAIL cases); CSV export. | P1 | M3 |
| FR-G4 | Offline queue: scans captured without connectivity are stored locally (IndexedDB) and synced; conflict-free by design (append-only). | P1 | M3 |

### 6.8 Poorv — manufacturer pre-print artwork check

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-A1 | Upload vector artwork (PDF/SVG) or a print-ready PNG with declared physical size; run the full catalogue with exact mm measurements (FR-M4). | P2 | M4 |
| FR-A2 | Fix list ranked by severity with the rule excerpt and a compliant example. | P2 | M4 |
| FR-A3 | Self-declaration PDF the manufacturer can keep on file (not a certificate). | P2 | M4 |

### 6.9 Bhasha — language

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-B1 | UI in English and Hindi; large touch targets; readable in sunlight (high-contrast theme). | P0 | M1 |
| FR-B2 | Rule messages in English and Hindi; report PDF in the officer's chosen language. | P0 | M1 |
| FR-B3 | Devanagari OCR (FR-D5); Hindi keys (शुद्ध वज़न / निवल मात्रा, अधिकतम खुदरा मूल्य, उपभोक्ता सेवा, निर्माता, आयातक, पैक करने की तिथि). | P1 | M3 |

### 6.10 Administration

| ID | Requirement | Pri | Phase |
|---|---|---|---|
| FR-X1 | Rules editor: view catalogue, diff versions, set effective dates, run regression suite before publishing. | P1 | M3 |
| FR-X2 | Commodity taxonomy and key lexicon editable without code. | P1 | M3 |
| FR-X3 | Notice templates per state. | P2 | M4 |

---

## 7. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Scan (OCR + rules) p50 ≤ 2 s, p95 ≤ 4 s on 2 vCPU / 4 GB, no GPU. ≥ 20 scans/min per container; stateless API scales horizontally. |
| Offline | PWA installable; capture, queue and view past results offline; sync on reconnect. Stretch (M3): on-device OCR via ONNX Runtime Web (PP-OCR models are ~10 MB) so even the verdict works with zero signal. |
| Device | Works on Android 10+ mid-range phones (2 GB RAM browser budget) and desktop Chrome/Edge/Firefox. |
| Determinism | Fixed model versions, fixed pre-processing, seeded any stochastic step; verdict reproducible from (image, rules_version, model_version). |
| Security | JWT auth, RBAC, TLS, signed report PDFs (SHA-256 of image embedded), hash-chained audit log, rate limits, input validation (done for size/type). |
| Privacy | DPDP Act 2023 aligned: inspection images contain no personal data by design; officer identity is the only PII; consumer reports optional and pseudonymous; configurable retention; no third-party calls by default. |
| Deployability | Single Docker image (backend + built frontend) + PostgreSQL; runs on NIC/MeghRaj, a state data centre, or a laptop; demo on Hugging Face Spaces (Docker). |
| Accessibility | WCAG 2.1 AA colour contrast (we check contrast for a living), screen-reader labels, Hindi UI. |
| Observability | Structured logs, per-stage timings (pre-process / OCR / rules / report), error rates, `NEEDS_REVIEW` rate as a product health metric. |
| Licensing | Apache-2.0 code; PP-OCR/RapidOCR models Apache-2.0; benchmark dataset CC-BY-4.0. |

---

## 8. Architecture and stack

```
 Phone / desktop (React PWA, Vite, Tailwind)
   │  camera capture · guidance overlay · offline queue (IndexedDB) · evidence viewer · dashboard
   ▼  HTTPS / JSON
 FastAPI (Python 3.12)
   ├─ drishti/   pre-process (OpenCV) → RapidOCR (ONNX Runtime CPU) → Devanagari rec → normalise → extract
   ├─ niyam/     applicability resolver → YAML rule evaluator → findings
   ├─ maap/      scale estimation (ArUco / known object / declared edge) → mm geometry
   ├─ tol/       MPE tables · lot statistics · Form A/B
   ├─ jaal/      listing fetch/parse → same extractor → R29/R30
   ├─ pramaan/   overlay renderer · PDF (WeasyPrint) · hash chain · QR verify
   └─ nigrani/   cases · dashboard aggregates · RBAC
 PostgreSQL (SQLite in dev) · object store for images (local FS / MinIO / S3-compatible)
 Docker Compose · GitHub Actions (pytest + rule regression) · HF Space for public demo
```

**Key choices and why**

- **RapidOCR on ONNX Runtime CPU** (already integrated): open-weight, small, fast, deployable inside government networks; no per-call cost. Devanagari support via the PaddleOCR Devanagari recognition model exported to ONNX and run on the same detector.
- **Deterministic rule evaluator over YAML** rather than an LLM judge: reproducible, testable, citable, and the Ministry's own officers can review the rules file.
- **OpenCV for geometry**: ArUco detection, homography, blur/glare metrics, contrast measurement. No learned model needed.
- **PostgreSQL** for cases and aggregates; append-only tables for audit.
- **WeasyPrint** for PDF reports and statutory forms from HTML templates (bilingual fonts: Noto Sans + Noto Sans Devanagari).
- **Optional, off by default**: local VLM for NEEDS_REVIEW triage; GS1 lookup; eMaap/state portal connectors.

---

## 9. Data model and API

### 9.1 Canonical objects

```
Scan            id, created_at, officer_id, premises, gps?, images[], rules_version, model_version, status
Declarations    manufacturer{name,address,pin,role}, packer, importer, marketer,
                country_of_origin, generic_name, net_quantity{value,unit,raw}, count,
                mfg_date{month,year,raw}, best_before, mrp{value,currency,incl_taxes_phrase,raw},
                unit_sale_price{value,per}, consumer_care{name,address,phone,email},
                gtin, scripts_detected[], stickers_detected, extra[]
                — every field: value, raw, bbox, confidence, source_line_ids, panel_id
Applicability   package_type, category, import, channel, exempt_reason?, applicable_rule_ids[]
Finding         rule_id, verdict, severity, measured?, threshold?, uncertainty?, evidence_bbox, message_en, message_hi
Measurement     scale_method, mm_per_px, uncertainty_pct, pdp_area_cm2, per-field heights
LotTest         lot_size, sample_size, tare_method, samples[{gross,tare,net,error}], mean, sd, corrected_avg, approved, form_pdf
Case            scan_ids[], responsible_entity, state, notice_pdf, history[]
AuditEntry      ts, actor, action, payload_hash, prev_hash, hash
```

### 9.2 API (v1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/scan` | Image(s) + optional context (package_type, category, net_qty) → Declarations, Applicability, Findings, overlay URL |
| POST | `/api/scan/{id}/measure` | Scale method + inputs → Measurement, re-evaluated geometry findings |
| POST | `/api/scan/{id}/weigh` | Gross/tare/net → MPE finding |
| POST | `/api/lot` | Lot definition + samples → LotTest, Form A/B PDF |
| POST | `/api/listing/check` | URL or screenshots → Findings (R29, R30) |
| GET | `/api/report/{scan_id}.pdf` / `.json` | Evidence report |
| GET | `/api/verify/{hash}` | Public verification page for a report QR |
| GET | `/api/rules?version=` | Rule catalogue (current or historical) |
| GET | `/api/dashboard/stats?state=&from=&to=` | Aggregates for Controllers |
| GET | `/api/health` | Liveness (done) |

---

## 10. Dataset and evaluation — NirikshanBench

There is no public benchmark for LMPC label compliance. Building one is both an engineering necessity and a contribution the Ministry can reuse.

| Slice | Size (M1 → M3) | Source | Notes |
|---|---|---|---|
| Real retail photos | 60 → 200 | Team photographs from local kirana, pharmacy, cosmetics, hardware and textile shops; 3 angles each; phone cameras | Covers food, cosmetics, drugs, textiles, hardware, imports, ≤ 20 g sachets, > 25 kg bags |
| E-commerce listings | 0 → 100 | Screenshots of marketplace product pages (fair-use, research) | For Rule 6(10) / Rule 31 |
| Synthetic labels | 40 → 150 | Generator with controlled violations (missing phrase, `gms`, dual MRP, 0.8 mm text, "approx.", Hindi-only, etc.) rendered at known mm scale | Ground truth for geometry rules is exact |
| Artwork PDFs | 0 → 20 | Sample vector artworks (own designs) | For Poorv mode |

**Annotation**: per image, ground-truth `Declarations` and per-rule verdict, double-annotated by two team members with a third adjudicating; 50 items reviewed with a practising Legal Metrology consultant or officer if access can be arranged (see §16).

**Reported metrics** (§2.3): field extraction accuracy, per-rule precision/recall/F1, NEEDS_REVIEW rate, latency distribution, and inspector time-on-task from a 5-user test (3 packs each, manual vs Nirikshan).

**Ablations to show judges**: OCR-only vs OCR + normalisation; rules with vs without applicability resolver (shows false-FAIL reduction on exempt packs); geometry with scale card vs declared edge.

---

## 11. Competitive landscape and differentiation

Public prior work for this exact PS exists (e.g. "LabelLens" — Gemini Vision transcription + deterministic checks; "SatyaLabel" — deterministic checker with PDF reports). Consultancies offer manual label audits. Against all of these:

| Dimension | Typical hackathon entry | Nirikshan |
|---|---|---|
| Judgement | LLM/VLM decides | Deterministic rules; AI only reads |
| Rule depth | Presence of ~8 fields | 35 checks: presence, wording, units, arithmetic, geometry, applicability |
| Applicability | Same checks for every pack | Resolver for exemptions and other-law carve-outs (food, cosmetics, drugs, wholesale, ≤ 20 g, > 25 kg, e-commerce) |
| Measurement | "Font looks small" | mm-calibrated heights, clear space, contrast with uncertainty bands |
| Product check | Label only | MPE, lot sampling, corrected average, Form A/B |
| Evidence | Text output | Annotated image, hash-chained log, rules-version stamp, QR-verifiable PDF, draft notice |
| Amendments | Code change | YAML with effective dates and regression suite |
| Language | English | English + Hindi (Rule 9(4)) UI, OCR and reports |
| Connectivity / cost | Cloud API, per call | Offline-capable, CPU-only, zero API cost, government-deployable |
| Users | One | Inspector, Controller, Manufacturer, Marketplace, Consumer |
| Benchmark | None | NirikshanBench with published metrics |

---

## 12. Mapping to SIH evaluation and the idea-submission template

| SIH criterion | Where Nirikshan scores |
|---|---|
| Novelty / innovation | Rules-as-code with effective dating; mm geometry from a phone; statutory lot procedure and Form A/B automation; applicability resolver |
| Complexity | OCR + layout extraction + geometry + statistics + case management, all CPU-bound and offline-capable |
| Clarity | Every finding cites a rule; demo shows a wrong pack fixed end-to-end |
| Feasibility | M0 already running (OCR on HF Space, tests green); open-weight models; no GPU |
| Sustainability | Apache-2.0, no API bills, config-driven amendments, runs on state infrastructure |
| Scale of impact | Every state LM department, every manufacturer, every marketplace; consumer mode later |
| User experience | Bilingual, sunlight-readable, 3-tap scan, offline queue |
| Future work | Artwork pre-check, GS1 enrichment, eMaap integration, on-device OCR, consumer reporting to NCH |

**Idea-PPT section → PRD section**: Proposed Solution → §0, §6; Technical Approach → §8, §9; Feasibility & Viability → §5, §13, §14; Impact & Benefits → §1.2, §11; Research & References → §17.

---

## 13. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OCR fails on curved, glossy, tiny or dense print | High | High | Guided multi-shot capture, glare/blur gating, perspective correction, multi-panel merge; degrade to NEEDS_REVIEW rather than FAIL; report NEEDS_REVIEW rate honestly |
| Wrong legal interpretation of a rule | Medium | Very high | Every rule carries the source notification link; conservative defaults; validation session with an LM officer/consultant; "review aid" disclaimer; officer sign-off |
| Font-height estimate wrong | Medium | High | Uncertainty bands; NEEDS_REVIEW inside the band; scale card preferred; artwork mode exact |
| Devanagari OCR quality | Medium | Medium | Separate rec model; script-aware normalisation; measure recall on benchmark; keep English path independent |
| Judges ask "why not just a frontier VLM?" | High | Medium | Show the same pack scanned twice by a VLM with different answers; show cost, offline, data-sovereignty and citation arguments; VLM allowed only as optional triage |
| Scope creep before internal round | High | High | P0 only for M1; feature flags for P1; PRD phase gates |
| Dev environment instability (Windows/pip site-packages issue seen in M0) | High | Medium | Dev container / Docker Compose from day one; `venv` per developer; CI as source of truth |
| Rule text changes mid-competition | Low | Medium | Effective-dated YAML absorbs it; that is the feature |
| Unauthorised scraping concerns in e-commerce mode | Medium | Medium | User-supplied URLs/screenshots only; respect robots; batch mode for platform-side users |

---

## 14. Delivery plan

### 14.1 Internal hackathon (M1) — next 2–3 weeks

| Week | Deliverable |
|---|---|
| 1 | Docker Compose dev env; whitespace-tolerant extractor (FR-D6/D7); applicability resolver; rules YAML v0.1 with 18 rules (R01, R02, R04, R05, R06–R12, R14, R15, R23, R25, R26, R27, R35); regression fixtures; evidence overlay |
| 2 | PDF report + JSON export; bilingual UI; 60-image NirikshanBench slice with annotations; metrics script; guided capture |
| 3 | Pitch deck (SIH template), 3-minute video, dry-run demo on 5 real packs, backup offline demo laptop |

### 14.2 Finale (M3) — 36-hour build plan (team of 6)

| Hours | Track A (vision) | Track B (rules/backend) | Track C (product) |
|---|---|---|---|
| 0–6 | Devanagari rec integration; scale-card detection + homography | Rules R16–R22, R29–R31 encoded with fixtures | Case model, RBAC, dashboard skeleton |
| 6–14 | Contrast, clear-space, height measurement with uncertainty | Lot module: MPE tables, tare logic, statistics, Form A/B PDF | E-commerce listing mode UI; offline queue |
| 14–24 | Multi-panel merge; benchmark run; ablations | Notice template; hash chain; QR verify page | Controller dashboard charts; Hindi report |
| 24–32 | Bug bash on 30 real packs | Rules-version diff view; regression green | Demo script rehearsal ×3; slides |
| 32–36 | Freeze, deploy to HF Space + local backup | — | Final rehearsal, jury Q&A prep |

### 14.3 Post-SIH pilot (M4)

Approach the state Controller of Legal Metrology through the college SPOC / Ministry mentor for a 4-week field pilot with 5 inspectors; success = inspector time per pack, NEEDS_REVIEW rate in the field, and officer-rated usefulness. Publish NirikshanBench.

---

## 15. Demo script (5 minutes)

1. **Compliant pack (30 s).** Scan a well-labelled biscuit pack → all green, each row shows its rule reference. Tap a row → evidence crop + rule excerpt.
2. **Non-compliant pack (75 s).** Scan a pack with "Net Wt 200 gms", "MRP Rs 45" (no "inclusive of all taxes"), no e-mail in consumer care, no country of origin though "Imported by" is printed → four FAILs, each with the pixels highlighted. Show the Hindi message toggle.
3. **Applicability (30 s).** Scan a 10 g shampoo sachet → engine reports Rule 26(a): only MRP and net quantity apply; everything else N/A. Then a 30 kg rice bag → Chapter II not applicable. "We don't produce false violations."
4. **Measurement (45 s).** Place the scale card next to the pack → letter heights in mm with ± band; PDP area computed; one value inside the band → NEEDS_REVIEW with "confirm with scale" instruction.
5. **Product, not just label (60 s).** Enter gross and tare for three sample packs → MPE from First Schedule, one pack over MPE → FAIL; open lot mode → sample size 32, corrected average, approval criteria → generate Form A PDF with signature blocks.
6. **E-commerce (30 s).** Paste a listing screenshot → Rule 6(10) findings; net quantity smaller than MRP text → Rule 31 flag.
7. **Controller view + rules as data (30 s).** Dashboard: violations by rule and district, repeat offender. Open the YAML, show `effective_from` on the unit-sale-price rule; re-evaluate an old scan against the 2021 rules version → verdict changes, log records both.
8. **Close (20 s).** Airplane mode on → scan still works (if on-device OCR landed) or queues and syncs. "Offline, CPU-only, cited, signed."

Backup: a pre-recorded video of steps 2–5 and a local laptop deployment in case the venue network fails.

---

## 16. Open questions to validate with the Ministry mentor / an LM officer

1. Exact current text of Rule 6(10) exceptions for e-commerce declarations, and whether Rule 31 is applied to marketplace listings in practice.
2. Post-2022 MRP format: is paise rounding still enforced anywhere, or should R13 default to off?
3. Fifth Schedule (2017) column 4 — number of packages permitted to exceed MPE per sample size — and the Sixth Schedule para 10 corrected-average formula (images in most online copies; transcribe from the Gazette notification).
4. Enforcement practice on "gms"/"ltr": treated as a violation, a warning, or tolerated?
5. Preferred notice formats per state; whether eMaap or state portals expose APIs for case filing.
6. Interest in NirikshanBench as a Ministry-hosted dataset; any existing internal label datasets.
7. Whether Controllers want dual-MRP detection across scans (R17) surfaced automatically or only on request.

---

## 17. References

- Legal Metrology (Packaged Commodities) Rules, 2011 with amendments — https://indiankanoon.org/doc/100694501/
- Rule 7 (PDP area, Table-I letter heights, 2017 substitution) — https://indiankanoon.org/doc/151004919/
- Legal Metrology Act, 2009 (Section 36 penalties) — India Code
- LMPC Amendment Rules 2017, G.S.R. 629(E) (e-commerce, country of origin, best-before, font table)
- LMPC Amendment Rules 2021/2022 (unit sale price, Second Schedule omitted) — summaries: https://www.lexology.com/library/detail.aspx?g=6ccd7e9e-d07e-43ac-b34a-dcec794dd1a2 ; https://www.teamleaseregtech.com/updates/article/16577/legal-metrology-packaged-commodities-amendment-rules-2022/
- LMPC Amendment Rules 2023 (e-commerce loose commodities, multi-piece packages) — https://teamleaseregtech.com/updates/article/27030/legal-metrology-packaged-commodities-amendment-rules-2023/
- Department of Consumer Affairs FAQs on LMPC Rules — https://taxguru.in/corporate-law/faqs-legal-metrology-packaged-commodities-rules-2011.html
- SIH 2026 problem statement catalogue — https://github.com/NoBugNinja/Smart-India-Hackathon-SIH-2026-Problem-Statements
- Prior public solutions for SIH26034: https://github.com/SIH-SnackOverflow/sih-snackoverflow ; https://satyalabel.vercel.app/
- RapidOCR — https://github.com/RapidAI/RapidOCR ; PaddleOCR multilingual models — https://github.com/PaddlePaddle/PaddleOCR

---

## Appendix A — Reference tables encoded in Niyam/Tol

**A.1 Rule 7 Table-I (post-2017): minimum height of numerals and letters**

| PDP area A (cm²) | Printed (mm) | Blown / formed / moulded (mm) |
|---|---|---|
| A < 50 | 1.0 | 1.5 |
| 50 ≤ A < 100 | 1.5 | 3.0 |
| 100 ≤ A < 500 | 2.5 | 4.0 |
| 500 ≤ A < 2500 | 4.0 | 6.0 |
| A ≥ 2500 | 6.0 | 6.0 |

Width ≥ ⅓ height except numeral 1 and letters i, I, l (Rule 7(3)). PDP area per Rule 7(4): rectangular → height × width of the panel side; cylindrical → 40% × height × circumference; other → 40% of total surface (tops, bottoms, flanges, shoulders and necks excluded).

**A.2 First Schedule Table I: MPE on net quantity by weight or volume**

| Declared quantity (g or ml) | MPE |
|---|---|
| up to 50 | 9% |
| 50–100 | 4.5 g/ml |
| 100–200 | 4.5% |
| 200–300 | 9 g/ml |
| 300–500 | 3% |
| 500–1000 | 15 g/ml |
| 1000–10 000 | 1.5% |
| 10 000–15 000 | 150 g/ml |
| above 15 000 | 1% |

Percentages rounded to 0.1 g/ml up to 1000 g/ml, to the next whole g/ml above.

**A.3 First Schedule Table II: MPE by length, area, number** — length 2% up to 10 m then 1%; area 4% up to 10 m² then 1%; number 2%.

**A.4 Fifth Schedule sample size** — lot < 4000 → 32 packages; lot > 4000 → 80. Sixth Schedule tare rule — single tare acceptable if ≤ 0.3 × MPE; otherwise five tares, averaged if their spread ≤ 0.4 × MPE.

**A.5 Rule 26(a) small-pack rule** — ≤ 10 g/10 ml exempt; 10–20 g/ml must declare MRP and net quantity only.

---

## Appendix B — Rules-as-code example

```yaml
- id: LMPC.6.1.e.MRP_INCL_TAXES
  rule_ref: "Rule 6(1)(e) read with Rule 2(m)"
  title_en: "MRP must be declared as maximum retail price inclusive of all taxes"
  title_hi: "एमआरपी को 'सभी करों सहित अधिकतम खुदरा मूल्य' के रूप में घोषित किया जाना चाहिए"
  applies_when: "pkg.type == 'retail' and not app.exempt and app.category != 'bidi'"
  inputs: [decl.mrp]
  check:
    all:
      - present: decl.mrp.value
      - regex: { field: decl.mrp.raw, pattern: "(?i)\\b(m\\.?r\\.?p|max(imum)?\\s*retail\\s*price)\\b" }
      - regex: { field: decl.mrp.raw, pattern: "(?i)incl(usive|\\.)?\\s*of\\s*all\\s*taxes" }
      - regex: { field: decl.mrp.raw, pattern: "(₹|Rs\\.?|INR)" }
  on_fail: { verdict: FAIL, severity: high }
  on_uncertain: { when: "decl.mrp.confidence < 0.75", verdict: NEEDS_REVIEW }
  evidence: decl.mrp.bbox
  fix_hint_en: "Print as: MRP ₹ 45.00 (inclusive of all taxes)"
  effective_from: "2018-01-01"
  source: "G.S.R. 629(E), 23 June 2017"

- id: LMPC.6.11.UNIT_SALE_PRICE
  rule_ref: "Rule 6(11)"
  applies_when: >
    pkg.type == 'retail' and not app.exempt
    and pkg.subtype not in ['multi_piece','combination','group']
    and not (decl.net_quantity.value in [1] and decl.net_quantity.unit in ['kg','L','m','unit'])
  check:
    all:
      - present: decl.unit_sale_price.value
      - unit_matches: { qty: decl.net_quantity, usp_per: decl.unit_sale_price.per }   # g if <1 kg, kg if >1 kg, etc.
      - approx_equal: { lhs: decl.unit_sale_price.value, rhs: "decl.mrp.value / decl.net_quantity.normalised", tol_pct: 1, tol_abs: 0.01 }
  on_fail: { verdict: FAIL, severity: medium }
  effective_from: "2024-01-01"
  source: "LMPC (Amendment) Rules 2022 and 2023"
```

---

## Appendix C — Idea abstract for the SIH submission (≈150 words)

Nirikshan is an offline-capable, CPU-only compliance checker for pre-packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. An inspector photographs a package; open-weight OCR (RapidOCR, English and Devanagari) extracts the declarations; an applicability resolver determines which rules apply to that pack (small-pack exemptions, wholesale packs, food and cosmetic carve-outs, imports, e-commerce); and a deterministic rules engine evaluates 35 encoded checks spanning presence, wording, SI units, unit-sale-price arithmetic, letter heights and clear space measured in millimetres via a printed scale card, contrast and language. Weighing inputs are checked against the First Schedule maximum permissible error, and lot inspections follow the Fifth–Seventh Schedule procedure with auto-generated Form A/B. Every finding cites its rule and highlights the evidence pixels; reports are hash-verified PDFs in Hindi or English. Rules are versioned YAML with effective dates, so amendments need no code change. Controllers get a dashboard of violations and repeat offenders; manufacturers get a pre-print artwork check. No cloud AI, no per-scan cost, deployable on government infrastructure.
