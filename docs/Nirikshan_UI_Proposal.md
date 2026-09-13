# Nirikshan — UI Redesign Proposal (Task 5.5)

**Direction in one line:** light, white-card, soft-blue interface (reference deck), navy from the logo, glass panels over imagery, big radii — *cinematic where it sells, restrained where it works.* Not a government portal; a product an inspector would want on their phone and a judge would remember.

Assets: `frontend/public/brand/logo-blue.svg`, `mark-blue.svg`, `icon-512.png`; tokens in `frontend/src/styles/tokens.css` (single source of truth for colours, radii, shadows, motion).

---

## 1. Principles

| # | Principle | What it means in practice |
|---|---|---|
| 1 | Two devices, one product | Phone = capture + verdict (inspector). Laptop = review + report + judging. Every screen responsive; layouts differ, data same. |
| 2 | Animation with a job | Every animation explains something (progress, cause→effect, where to look). Nothing loops idly on the working screens. |
| 3 | Evidence first | The image with boxes is the hero of every result; tables serve it, not the other way round. |
| 4 | 60 fps on a ₹12k phone | Transforms/opacity only, no layout thrash; `prefers-reduced-motion` honoured; images downscaled client-side before upload. |
| 5 | Bilingual by default | EN/हिं toggle in the header, persisted; all findings show `message_hi` when Hindi. |

---

## 2. Routes

| Route | Purpose | Primary device |
|---|---|---|
| `/` | Landing — pitch, live demo, how it works | Laptop (judges) |
| `/app` | Inspector flow — scan → verdict → evidence → report | Phone |
| `/review` | Laptop review + phone pairing (results from the phone appear here live) | Laptop |
| `/rules` | Rules explorer — the 35-rule catalogue, searchable, bilingual | Both |
| `/dashboard` | Controller view — later (Task 10) | Laptop |

---

## 3. Screens

### 3.1 Landing `/`
**Layout (desktop):** full-height hero, white card floating on a pale-blue gradient (blue-50 → white) with faint dot grid. Left: headline *"Rules-as-code compliance for every package"*, sub-line naming the Rules, two CTAs — **Start inspection** (→ `/app`) and **See it work** (runs the four_violations demo image through the real API right there, with the scan animation, then reveals the verdict card in the hero). Right: the blue mark, large.
**Sections below:** "How it works" — three glass cards (Scan → Rules → Evidence) staggered in on scroll; "35 rules, every one cited" — counter + a horizontal strip of rule pills that scrolls slowly (pauses on hover); "Built for the field" — phone-first, offline-ready, CPU-only, Hindi; footer with the tricolour logo, PS SIH26034, Ministry name, GitHub link.
**Mobile:** same order, single column, mark above headline.

**Animations:** mark assembles on load (arc segments draw in one after another 0→100% stroke-dashoffset, box rises with slight overshoot, check badge pops with a spring); headline words fade-up staggered 40 ms; CTAs lift on hover; demo run uses the same Analyzing animation as the app.

### 3.2 Inspector `/app` (phone-first, PWA-installable)

**A. Scan**
- Top bar: mark + "Nirikshan", EN/हिं toggle, backend status dot (green = model loaded).
- Centre: large **camera tile** (glass, dashed border, camera icon) — tap opens camera (`capture=environment`); secondary "Choose from gallery".
- Context chips row (scrollable): Package type (Retail · Wholesale · Multi-piece · Combination · Not for retail), Category (General · Food · Cosmetic · Drug · Seed · Alcohol · LPG · Bidi/incense · Textile), Imported toggle. Selected chip fills blue-500.
- Optional "Add another panel" after first photo (front/back) — up to 4 thumbnails, each removable. (Multi-panel merge stays backend Task; for now the first image is scanned, others stored for the report.)
- Bottom sticky button: **Run compliance scan**.
- Recent scans (this session): small cards with thumbnail, status colour, time; tap reopens.

**B. Analyzing**
- The photo fills the card. A **scan line** (blue-500, soft glow, 2 px) sweeps top→bottom in 1.2 s loops while the request is in flight.
- Stepper under the image: *Reading text → Understanding declarations → Checking 19 rules* — steps light up as `timings` arrive (we get everything at once, so stage 1 lights at response, 2 and 3 follow 250 ms apart).
- When OCR lines are known: each detected line's bbox flickers on in reading order (10–15 ms apart) — the "the machine has read it" moment.

**C. Verdict**
- Banner slides down from the top of the result card: **COMPLIANT** (pass green), **NON-COMPLIANT** (fail red), **OFFICER REVIEW REQUIRED** (amber), **EXEMPT** (blue-200 with the reason). For Compliant: a "stamp" effect — banner scales from 1.15→1 with slight rotation and a soft thud shadow. For Non-compliant: red banner with a single glow pulse, no shake.
- Count chips count up (0→n over 500 ms): FAIL · REVIEW · PASS · N/A.
- Quality warnings (blurry / glare / dark) as an amber ribbon under the banner with a "Retake" button.
- Tabs: **Findings · Evidence · Declarations · Report**.

**D. Findings tab**
- Cards, grouped: FAIL → NEEDS_REVIEW → PASS → N/A (N/A collapsed under "Not applicable (n)" with reasons).
- Card: rule pill (R12), rule ref (Rule 6(1)(e)), verdict badge, message (EN/HI); tap expands: extracted / expected / fix hint, and **Show on image** (switches to Evidence with that box highlighted).
- Cards enter staggered (60 ms) from 8 px below.

**E. Evidence tab**
- Image with boxes drawn **sequentially** (FAIL first, red; then amber; then green, 40 ms apart), rule ids as small labels. Pinch-zoom/pan on phone, scroll-zoom on desktop. Tap a box → its finding card slides up as a bottom sheet (phone) or highlights in a side list (desktop). "Download evidence PNG".

**F. Declarations tab**
- Grid of cards (2-col phone, 3–4-col desktop): label, value, confidence bar (blue-500 fill), raw in mono under it (2-line clamp, expand), "Not found" ghosted; "Declared on crimp" chip where applicable; entities listed as small address cards with role tags.

**G. Report tab**
- Glass sheet: Officer name, Premises, Remarks, Language (EN/HI) — remembered for the session.
- **Download PDF** (progress ring while /api/report runs), **Download JSON**, **Share** (Web Share API where available).

### 3.3 Review `/review` (laptop)
- Left column (30%): **Pair your phone** — QR code + 6-character code; "Waiting for phone…" pulse. Once paired, incoming scans stack here as thumbnails with status; the newest opens on the right automatically with a slide-in.
- Right column (70%): the same result view as `/app` but desktop layout — image + evidence on the left, findings list on the right, declarations below; Report actions in the header.
- Fallback: "Or upload here" drop-zone (drag-and-drop) — works without a phone.
- Backend: `POST /api/session` → code; `POST /api/scan?session=CODE` stores the result in an in-memory store (TTL 2 h); `GET /api/session/CODE/events` (SSE) or polling every 2 s pushes new results to the laptop. Stateless enough for now; Task 10 moves it to the DB.

### 3.4 Rules explorer `/rules`
- Search + filters (verdict severity, implemented / planned, category). Cards: rule id, rule ref, title (EN/HI), severity dot, "Implemented" or "Planned" tag.
- Click → detail drawer: what the rule requires (plain words), how Nirikshan checks it, fix hint, source notification. Data from `GET /api/rules` (implemented) + a static JSON for the planned 16.
- Why: judges ask "which rules do you cover?" — this answers it in 10 seconds and shows the rules-as-code idea.

### 3.5 Global
- Header: mark + wordmark (blue), nav (App · Review · Rules), EN/हिं, status dot. Footer: tricolour logo small, PS id, version (`rules_version`, `git_sha` from /api/health).
- Toasts for errors (network, 413, 415), skeletons while loading, empty states with a one-line hint.
- Keyboard focus rings, AA contrast (verified with the tokens), touch targets ≥ 44 px.

---

## 4. Animation spec

| Element | Animation | Timing | Tool |
|---|---|---|---|
| Logo mark (landing) | arc segments stroke-draw sequentially; box rise; check spring pop | 1.4 s total, ease-out | Framer Motion (SVG) |
| Hero text | words fade-up, 40 ms stagger | 280 ms each | Framer Motion |
| Scan line | vertical sweep with glow, loops while pending | 1.2 s loop | CSS keyframes |
| OCR line flicker | bboxes appear in reading order | 12 ms apart | Canvas + rAF |
| Stepper | steps light up | 250 ms apart | Framer Motion |
| Verdict banner | slide-down + stamp (scale 1.15→1, rotate −2°→0) | 420 ms spring | Framer Motion |
| Count chips | count-up | 500 ms | Framer Motion `animate()` |
| Findings cards | staggered fade-up | 60 ms stagger | Framer Motion |
| Evidence boxes | sequential draw, FAIL first | 40 ms apart | Canvas + rAF |
| Tab switch | shared-layout underline slide, content cross-fade | 200 ms | Framer Motion `layoutId` |
| Bottom sheet (phone) | spring from bottom, drag to dismiss | spring | Framer Motion drag |
| Pairing | QR fade-in; "waiting" pulse; incoming scan slides in | — | Framer Motion |
| Reduced motion | all of the above become instant/opacity-only | — | `prefers-reduced-motion` |

---

## 5. Components (build once, reuse)

`Button` (primary/secondary/ghost), `Chip` (selectable), `Card` / `GlassCard`, `VerdictBanner`, `CountChip`, `RuleCard`, `EvidenceCanvas` (owns bbox mapping via `utils/bbox.js`), `DeclarationCard`, `EntityCard`, `Stepper`, `ScanLine`, `Tabs`, `BottomSheet`, `Drawer`, `Toast`, `Skeleton`, `LanguageToggle`, `StatusDot`, `QRPair`, `Logo`.

---

## 6. Tech

React 18 + Vite (existing), `react-router-dom`, `framer-motion`, `lucide-react`, `qrcode.react`, `vite-plugin-pwa` (manifest + installable; offline shell only for now). Styling: vanilla CSS modules on top of `tokens.css` (no Tailwind — keeps the tokens honest). Fonts: Plus Jakarta Sans + Noto Sans Devanagari via Google Fonts with `display=swap` and a local fallback. i18n: `src/i18n/{en,hi}.json` + a tiny `useT()` hook. Client-side image downscale to 2400 px before upload (saves 4G time). Tests: `test_bbox.js` kept; add Vitest for `i18n` completeness (every key in both files) and `mapBbox`.

---

## 7. Out of scope for 5.5
Dashboard (Task 10), offline queue/sync (Task 10), Devanagari OCR (Task 11), geometry screens (Task 7). The layout leaves room for a "Measure" tab and a "Lot" tab so they slot in later.

---

## 8. Acceptance (for the agent prompt)
1. Lighthouse (mobile, throttled) on `/app`: Performance ≥ 85, Accessibility ≥ 95.
2. Every animation in §4 present and disabled under `prefers-reduced-motion`.
3. All existing API fields rendered: quality warnings, exempt_reason, entities, declared_elsewhere chips, N/A reasons.
4. EN/हिं toggle switches every visible string (i18n completeness test) and finding messages.
5. `/review` pairing works between a phone and a laptop on the live URL; fallback upload works.
6. `/rules` lists all 35 rules with implemented/planned status from the catalogue + static JSON.
7. PDF/JSON download works from the phone and the laptop.
8. No regressions: existing backend tests untouched; CI green.

---

## 9. Open questions for you
- Landing page demo: run the real API live (needs backend awake — cold start 30 s) or play a pre-recorded scan (instant)? *Recommendation: real API with a "warming up…" state, fallback to recorded if health fails.*
- Pairing code: QR only, or also a typed 6-character code? *Recommendation: both.*
- Dark mode: skip for now (reference is light; inspectors use it in sunlight).

---

## 10. Extended animation set (added on request — still purposeful, all GPU-only, all off under reduced-motion)

| Where | Animation | Why it earns its place |
|---|---|---|
| Landing hero background | 3 soft blue gradient orbs drifting slowly (30 s loops), faint dot-grid parallax on scroll | depth without noise |
| Landing hero card | mouse-move 3D tilt (±6°) with a light sheen that follows the cursor | the "not a govt site" moment |
| Landing "35 rules" | digits flip like a split-flap board on scroll-in; the rule-pill strip scrolls and pauses on hover | states the number memorably |
| Landing before/after | slider between raw photo and annotated evidence (drag the divider) | shows the product in one gesture |
| Route transitions | blue-50 curtain wipe (left→right, 350 ms) between routes; shared-element morph of the scan thumbnail into the result hero image | continuity between screens |
| Capture | shutter flash (white 120 ms) + the photo "drops" into the card with a spring bounce | confirms the capture |
| Analyzing | scan line **plus** a faint hex/mesh grid that lights along the line; detected text lines get a 1-frame typewriter label | makes the wait feel like work |
| Analyzing stepper | each step's icon draws itself (stroke-draw) when it completes | progress you can see |
| Verdict | after the stamp, a single ripple ring expands from the banner and fades (Compliant only) | reward without confetti |
| Count chips | numbers roll like an odometer | satisfying, quick |
| Chips / buttons | magnetic hover (button nudges 2 px toward the cursor), press scale 0.97 | tactile |
| Findings card | expand = card grows with content (layout animation); "Show on image" flies a ghost of the rule pill to its box on the canvas | cause→effect made visible |
| Evidence box selected | box pulses twice and the rest dim to 60 % | focus |
| Declarations | confidence bars fill from 0 in sequence; "Declared on crimp" chip wobbles once on first reveal | draws the eye to what matters |
| Report download | the PDF icon fills bottom-to-top like ink while /api/report runs; on success it lifts and a check appears | progress for a 3–5 s wait |
| Review pairing | QR fades in; on pair success the QR morphs into a check inside a ring; each incoming scan flies in from the left column and lands in the viewer | the phone→laptop story, visibly |
| Rules explorer | filter changes reflow cards with layout animation; card click flips to the detail side | exploration feels alive |
| Header | status dot heartbeat (2 s) when healthy; EN/हिं toggle letters morph | tiny life |
| Skeletons | shimmer sweep while loading | standard, but done in blue-50 |
| Errors | toast slides in from the top with a red left rail; the offending field shakes once (3 px) | clear, not loud |

Budget rule: no more than one *ambient* animation per screen (orbs on landing, heartbeat in the header); everything else is triggered by an action or data arriving.
