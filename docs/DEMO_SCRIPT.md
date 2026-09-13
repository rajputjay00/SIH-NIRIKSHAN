# Nirikshan — 5-Minute Live Demonstration Script (SIH26034)

This script guides the presenter step-by-step through demonstrating **Nirikshan**, the Legal Metrology Packaged Commodities Compliance Platform, to judges and stakeholders.

---

## Demo Setup & Prerequisites
1. **Primary Device**: Laptop with Chrome/Edge browser open at `https://nirikshan.yellowsky-50e55bef.eastasia.azurecontainerapps.io` (or local `http://localhost:5173`).
2. **Secondary Device**: Smartphone connected to 4G/WiFi or local network.
3. **Bundled Test Assets**:
   - `four_violations.png` (Synthetic pack with missing MRP phrase, non-standard unit `gms`, missing consumer care email, missing origin country).
   - `Toothpaste` pack / `compliant_1.png` (Fully compliant packaging).

---

## Step 1: Landing Page & Problem Pitch (45 seconds)
- **Route**: `/` (Landing Page)
- **Script**:
  > "Distinguished Jury, under the Legal Metrology (Packaged Commodities) Rules 2011, millions of pre-packaged goods are sold daily in India. Ensuring every mandatory declaration—from MRP to Unit Sale Price and net quantity—is printed correctly requires intense manual effort. Nirikshan is an offline-capable, CPU-only platform that automates compliance verification using deterministic rules-as-code."
- **Action**: Hover over the 3D Hero Card to show perspective tilt & sheen. Point out the 35 rules counter. Click **"Start Inspection"** or **"See it work"**.
- **Fallback**: *If live internet/API is slow or fails, click "See it work" which automatically falls back to bundled `sample_result.json` analysis inside 15 seconds.*

---

## Step 2: Multi-Panel Inspection & Violation Detection (90 seconds)
- **Route**: `/app` (Inspector Flow)
- **Script**:
  > "Let's inspect a retail package. We select the context—Retail Package, General Category—and upload our PDP panel photos. Nirikshan downscales the image client-side to 2400px and runs RapidOCR on CPU in under 2 seconds."
- **Action**: Upload `four_violations.png` (or click photo). Click **"Run Inspection Scan"**. View the Verdict Banner (`Non-compliant`) and count chips (`FAIL: 4`). Tap **Findings Tab** to inspect specific rule failures:
  1. `R04` (Country of origin missing).
  2. `R08` (Non-standard unit `gms`).
  3. `R12` (MRP missing 'inclusive of all taxes').
  4. `R15` (Consumer care email missing).
- **Fallback**: *If camera photo is blurry or unreadable, select the bundled sample photo from gallery or re-scan using `/four_violations.png`.*

---

## Step 3: Evidence Overlay & Box Alignment (45 seconds)
- **Route**: `/app` → **Evidence Tab**
- **Script**:
  > "Crucially, Nirikshan adheres to a strict principle: 'Cite or shut up'. Every single finding is mapped to its exact bounding box on the original package artwork."
- **Action**: Switch to Evidence Tab. Click on a red box or click **"Show on image"** on a finding. Notice the selected box highlights in white while others dim. On mobile, tap box to open `BottomSheet`; on desktop, inspect the side panel card.
- **Fallback**: *If canvas touch event misses, select the rule card directly from Findings tab to auto-focus the Evidence bounding box.*

---

## Step 4: Phone-Laptop Review & SSE Pairing (60 seconds)
- **Route**: `/review` (Laptop Review & Pairing)
- **Script**:
  > "Field inspectors using mid-range mobile phones can pair live with a laptop session. As field scans are taken, results stream instantly over Server-Sent Events (SSE)."
- **Action**: Open `/review` on laptop. Show the 6-character pairing code & QR Code (`<origin>/app?session=CODE`). Scan QR or type code on phone. Perform a scan on phone—watch it fly into the laptop stack instantly!
- **Fallback**: *If SSE connection is blocked by local firewall, the system seamlessly falls back to 3-second HTTP polling or manual drag-and-drop on the laptop review panel.*

---

## Step 5: Rules-as-Code Explorer & Report Export (60 seconds)
- **Route**: `/rules` & `/app` → **Report Tab**
- **Script**:
  > "Nirikshan versioning ensures court admissibility. All 35 rules are encoded as data with Gazette citations and effective dates. Finally, we generate a bilingual PDF report with an embedded SHA-256 image hash and verification QR."
- **Action**:
  1. Navigate to `/rules` to show active vs planned rules, search filter, and card flip (`rotateY`). Point out `rules_version`.
  2. Return to `/app` → Report Tab. Click **"Download PDF Report"**—observe ink-fill animation and success tick.
- **Fallback**: *If PDF download fails due to browser popup blocker, click "Download JSON" for instantaneous machine-readable verdict export.*

---

## Summary Checklist for Presenter
| Step | Focus Feature | Primary Asset | Fallback Path |
|---|---|---|---|
| 1 | 3D Hero Card & Pitch | Landing (`/`) | "See it work" button |
| 2 | 4 Violations Detection | Inspector (`/app`) | Pre-loaded `/four_violations.png` |
| 3 | Bounding Box Canvas | Evidence Tab | Findings tab direct click |
| 4 | Phone-Laptop SSE Sync | Review (`/review`) | Direct drag-and-drop on review |
| 5 | Rules Explorer & PDF | Rules (`/rules`) | JSON download button |
