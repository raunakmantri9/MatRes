# Plan: MatRes Hackathon — Detailed Step-by-Step Execution

## Context

**Deadline:** June 6, 2026 IST (June 5 5pm PT)
**Working days:**
| Day | Date | Hours |
|-----|------|-------|
| Day 1 | Fri May 23 | ~5 hrs |
| Day 2 | Sat May 24 | 8-12 hrs |
| Day 3 | Sun May 25 | 8-12 hrs |
| Day 4 | Mon May 26 | ~5 hrs |
| Day 5 | Fri May 30 | ~5 hrs |
| Day 6 | Sat May 31 | 8-12 hrs |
| Buffer | Sun Jun 1 – Thu Jun 5 | Emergency only |

**No need to wait for hackathon credits.** ₹28,365 GCP free trial covers everything. Start now.

---

## PRE-WORK — ✅ ALL DONE (completed May 21)

### Step P1 — Enable APIs on GCP ✅
- aiplatform.googleapis.com (Vertex AI)
- generativelanguage.googleapis.com (Gemini)
- run.googleapis.com (Cloud Run)
- secretmanager.googleapis.com (Secret Manager)
- GCP project: **Materials Resilience Agent**

### Step P2 — Install tools locally ✅
All packages installed in venv at:
`/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/venv/`

To activate in any new terminal:
```bash
source "/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/venv/bin/activate"
```

To install new packages (use venv pip directly, not system pip):
```bash
"/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/venv/bin/pip" install <package>
```

### Step P3 — Materials Project API key ✅
Key saved in `.env`

### Step P4 — GitHub repo ✅
- Repo: https://github.com/raunakmantri9/MatRes (private → make public on Day 6)
- Local path: `/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/`
- `.env` gitignored and removed from history

---

## DAY 1 — Fri May 23 (~5 hrs): Project Scaffold + Schemas + Data Start

### Step 1.1 — Create folder structure (10 min) ✅ Already done
```bash
cd "/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes"
mkdir -p agents data schemas bom_fixtures mcp_servers ui deploy docs
touch agents/__init__.py schemas/__init__.py mcp_servers/__init__.py
```

### Step 1.2 — Verify .env ✅ Already done
`.env` is at `/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/.env`
Confirm `GOOGLE_CLOUD_PROJECT` matches the GCP project ID (check console — may be `materials-resilience-agent` not `matres-hackathon`).

### Step 1.3 — Create Pydantic schemas (45 min) ✅ Already done
Create `/Users/raunakmantri/Coding/Learning to Code/Ideas/MatRes/schemas/models.py` with these models:
- `Material` — name, cas_number, category (cathode/anode/magnet/electrolyte)
- `SupplyConcentration` — material_name, top_country, top_country_pct, hhi_score, feoc_flag (bool), export_control_events (list of strings with dates)
- `FailureMode` — material_name, mode_description, source_url, recall_count, severity (1-5)
- `SubstitutionCandidate` — original_material, substitute_name, property_delta (dict), supply_risk_score, co2_delta_pct, ranked_position (1/2/3)
- `QualificationStep` — step_name, standard (e.g. "UN 38.3"), duration_weeks, cost_band_usd
- `BOMComponent` — component_name, material_name, quantity_kg, supplier_country
- `RiskReport` — bom_name, components (list of BOMComponent), supply_risks, failure_modes, substitutions, qualification_roadmap, composite_score

Create `schemas/validate.py` (in the same folder) — loads a BOM JSON file and validates it against models, prints any errors.

### Step 1.4 — Create 3 BOM fixture files (30 min) 
Create `bom_fixtures/nmc811.json` — NMC 811 cathode BOM:
Key materials: cobalt (20% by weight, DRC), nickel (10%, Philippines/Indonesia), manganese (5%, South Africa), lithium (5%, Chile/Argentina), graphite anode (10%, China)

Create `bom_fixtures/lfp.json` — LFP cathode BOM:
Key materials: iron phosphate (no concentration risk), lithium (5%, Chile), graphite (10%, China)

Create `bom_fixtures/ncm622_magnet.json` — NCM 622 + NdFeB motor BOM:
Key materials: neodymium (3%, China >90% refined), dysprosium (1%, China >90%), cobalt (15%, DRC), graphite (10%, China)

Each fixture should list: component_name, material_name, quantity_kg, supplier_country, notes.

### Step 1.5 — USGS data ingestion (60 min)
Create `data/ingest_usgs.py`:
- Download USGS Mineral Commodity Summaries 2025 from usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries
- Parse the key table: country production by mineral (cobalt, lithium, nickel, graphite, rare earths, manganese)
- For each material, compute: top country, top country % of world production, HHI score
- Save to `data/usgs_mcs_2025.parquet`

Run: `python data/ingest_usgs.py`
**Validate:** cobalt → DRC should be 70%+, graphite → China should be 65%+

### Step 1.6 — Materials Project API pull start (60 min)
Create `data/ingest_materials_project.py`:
- Use Materials Project API (materialsproject.org/api) 
- Query for battery-relevant materials: cathodes (LiFePO4, LiCoO2, LiNiO2, LiMnO2, LiNi0.8Co0.1Mn0.1O2), anodes (graphite, silicon, Li4Ti5O12), magnets (Nd2Fe14B, ferrite)
- Pull: formula, band_gap, formation_energy, stability (energy above hull), available property fields
- Save to `data/materials_project_battery.parquet`

**Day 1 gate:** `python schemas/validate.py bom_fixtures/nmc811.json` → zero errors. USGS parquet loads with cobalt at >60% DRC.

---

## DAY 2 — Sat May 24 (10 hrs): Data Complete + Claude Prototype

### Step 2.1 — Finish Materials Project pull (60 min)
Complete the bulk pull if still running. Verify parquet has >1000 entries with property data.

### Step 2.2 — NHTSA recall data (90 min)
Create `data/ingest_nhtsa.py`:
- NHTSA API: api.nhtsa.dot.gov/recalls/recallsByVehicle (free, no key needed)
- Also scrape: api.nhtsa.dot.gov/complaints/complaintsByVehicle
- Filter to EV-related battery recalls (2018–2026): keywords "battery", "thermal runaway", "fire", "cell", "pack"
- Key recalls to capture: GM Bolt (2021), Hyundai Kona EV (2021), Chrysler Pacifica PHEV (2022)
- For each recall: vehicle, year, description, component, NHTSA_ID, units_affected
- Save to `data/nhtsa_ev_recalls.parquet`

### Step 2.3 — OEC trade data (30 min)
Create `data/ingest_oec.py`:
- Use OEC API (oec.world/api) — trade flow data for HS codes of battery materials
- Key HS codes: 2604 (nickel ores), 2605 (cobalt ores), 2825.20 (lithium oxide), 2504 (graphite), 2846.90 (rare earth compounds)
- Pull top 5 exporting countries per material with % share
- Save to `data/oec_flows.parquet`

### Step 2.4 — Claude prototype: Scenario A (3 hrs)
**This is the most important step of the entire project. Do not rush it.**

Open Claude (claude.ai or API) and build a prompt chain that does:

**Prompt 1 — Supply Risk Analysis:**
```
Given this BOM component: [paste nmc811.json cobalt entry]
Using this USGS data: [paste cobalt row from usgs parquet]
Analyze: country concentration risk, FEOC compliance status under US IRA 2022, 
any active export controls. Return structured JSON with hhi_score, top_country, 
top_country_pct, feoc_flag, risk_level (HIGH/MEDIUM/LOW), reasoning.
Every number must cite its source.
```

**Prompt 2 — Substitution Generation:**
```
The original material is cobalt (in NMC 811 cathode).
Supply risk: HIGH (70% DRC, FEOC non-compliant).
Using this Materials Project data: [paste LFP, LNMO, sodium-ion data]
Generate 3 ranked substitution candidates. For each: 
- property delta vs NMC 811 (energy density, cycle life, thermal stability)
- supply risk score
- CO2 delta estimate
- brief qualification note
Return structured JSON. Cite every number.
```

**Prompt 3 — Qualification Roadmap:**
```
Substitution: NMC 811 → LFP in a 75 kWh EV pack.
Generate a qualification roadmap with steps, applicable standards (UN 38.3, 
IEC 62660-1, UL 2580), duration per step in weeks, and rough cost band in USD.
Return structured JSON with steps as ordered list.
```

**Validate output:** All 3 prompts return clean JSON. Every number has a source. LFP appears as top-ranked substitution. Qualification roadmap has ≥4 steps.

**If any prompt fails:** Fix the prompt before proceeding. Do not port broken reasoning to ADK.

### Step 2.5 — ADK project setup (90 min)
Create `agents/root_agent.py` — ADK root agent skeleton:
```python
from google.adk import Agent, Tool
# Configure Gemini 2.5 Pro as the model
# Define the root agent that will orchestrate sub-agents
# Initial version: just load the model and verify it responds
```

Run a hello-world test to confirm ADK is connecting to Gemini.

**Day 2 gate:** Scenario A Claude prototype produces 3 substitutions with zero uncited numbers. ADK hello-world runs without errors.

---

## DAY 3 — Sun May 25 (10 hrs): ADK Build — All 4 Sub-agents

### Step 3.1 — SupplyRiskAnalyzer (2 hrs)
Create `agents/supply_risk.py`:
- Input: `BOMComponent` (material name + quantity)
- Logic: query USGS parquet for material → compute HHI, get top country %, check FEOC flag, check OEC flows for recent export-control events
- Output: `SupplyConcentration` model
- Expose as ADK Tool with typed input/output
- **Cite-or-die rule**: every number in output must include `source: "USGS MCS 2025"` or `source: "OEC 2024"` in the JSON

### Step 3.2 — SubstitutionGenerator (2 hrs)
Create `agents/substitution.py`:
- Input: original material name + supply risk score
- Logic: query Materials Project parquet for candidate materials in same category → rank by property delta + supply risk of substitute
- Output: list of 3 `SubstitutionCandidate` models, ranked
- Property delta fields: energy_density_pct, cycle_life_pct, thermal_stability (qualitative), cost_delta_pct
- Every property delta cites `source: "Materials Project mpid:XXXXX"`

### Step 3.3 — FailureModePredictor (2 hrs)
Create `agents/failure_mode.py`:
- Input: material name
- Logic: query NHTSA parquet for recalls mentioning this material → extract failure descriptions, group by mode (thermal runaway, dendrite growth, electrolyte degradation, etc.)
- Output: list of `FailureMode` models, top 3 by recall count
- Each mode cites: `source: "NHTSA recall ID: XXXXX"`
- **If RAG is too slow to build:** use pandas keyword filtering on recall descriptions — acceptable for demo

### Step 3.4 — QualificationPlanner (1.5 hrs)
Create `agents/qualification.py`:
- Input: original material + substitute material name
- Logic: hardcoded qualification roadmap templates per substitution type (cathode swap, anode swap, magnet swap) — look up by material category
- Output: ordered list of `QualificationStep` models
- Roadmap for cathode swap (e.g., NMC → LFP): cell-level testing (UN 38.3) → module testing (IEC 62660-1) → pack-level (UL 2580) → OEM validation → regulatory certification → production ramp
- Timeline: 14-20 months total, broken by step
- Cost bands: $200k-500k per step depending on facility

### Step 3.5 — Hallucination guard (1.5 hrs)
Create `schemas/validator.py` post-output validator:
- After each sub-agent returns output, scan for numeric values (regex: `\d+\.?\d*`)
- For each number, check that a `source:` key exists in the same JSON object
- If any unsourced number found: raise `CitationError` and return an error response instead of passing the output upstream
- This runs as a middleware wrapper around each sub-agent call

### Step 3.6 — Wire root agent (1 hr)
Update `agents/root_agent.py`:
- Orchestrate: parse BOM → for each component → run SupplyRisk → run FailureMode → run Substitution → run Qualification → aggregate into `RiskReport`
- Run Scenario A end-to-end using `bom_fixtures/nmc811.json`

**Day 3 gate:** Scenario A runs through all 4 sub-agents. Zero uncited numbers in output. Output includes supply risk, failure modes, 3 substitutions with property deltas, qualification roadmap with timeline.

---

## DAY 4 — Mon May 26 (~5 hrs): Composite Scorer + MCP + UI Scaffold ✅ COMPLETE (May 21)

### Step 4.1 — Composite scorer ✅
`compute_composite_score()` added to `agents/root_agent.py`:
- w1=0.40 (supply risk), w2=0.25 (perf delta), w3=0.25 (qual cost), w4=0.10 (CO2)
- Weights tunable via SCORE_W1–W4 env vars or Streamlit sidebar sliders
- Fixed: added `composite_score: Optional[float]` to `SubstitutionCandidate` schema
  (Pydantic was silently stripping it on model construction)
- Sample scores: LFP 67.1, LNMO 71.0, sodium-ion 69.2

### Step 4.2 — MCP server for USGS ✅
`mcp_servers/usgs_server.py` — Server "usgs-mcs-2025" with 2 tools:
- `get_supply_concentration(material_name)` → country breakdown + FEOC flag
- `get_hhi_score(material_name)` → HHI + risk level (HIGH/MEDIUM/LOW)

### Step 4.3 — MCP server for Materials Project ✅
`mcp_servers/materials_project_server.py` — Server "materials-project" with 2 tools:
- `get_material_properties(material_name)` → formation energy, stability, band gap
- `find_substitutes(material_name, category)` → top 5 candidates sorted by energy_above_hull

### Step 4.4 — Streamlit UI scaffold ✅
`ui/streamlit_app.py` — full 4-tab UI:
- Sidebar: file uploader + 4 weight sliders
- Tab 1 Supply Risk: table with RISK_COLORS icons + export control events
- Tab 2 Failure Modes: NHTSA recall table with severity icons
- Tab 3 Substitutions: medal cards (🥇🥈🥉) with st.metric for each property delta
- Tab 4 Qualification Roadmap: cumulative timeline table + total cost/duration metrics
- Download Report button (JSON export)

**Day 4 gate: ✅ PASSED**
- All 3 BOM fixtures run clean (nmc811: 8 risks / 15 failure modes / 3 subs / 7 qual steps, 0.2s)
- Streamlit server confirmed live at http://localhost:8501

---

## DAY 5 — Fri May 30 (~5 hrs): Full UI + All 3 Scenarios ✅ COMPLETE (May 22)

**Key architectural clarification added:** Gemini 2.5 Pro is now wired into the runtime pipeline — not just defined. `generate_executive_summary()` in `agents/root_agent.py` calls Gemini after the structured pipeline runs to produce a grounded 3–4 sentence narrative. This is what judges will see demonstrating real LLM reasoning.

### Step 5.1 — Gemini executive summary + UI ✅
- `generate_executive_summary()` added to `agents/root_agent.py`
- Sends structured risk data (high-risk materials, top substitution, qualification weeks) to Gemini 2.5 Pro
- Result displayed as `st.info("Gemini 2.5 Pro Analysis ...")` panel above the 4 tabs in Streamlit
- Sample output (nmc811): _"Critical supply chain risks with 77% graphite from China and 73% cobalt from DRC, both FEOC. LFP is top substitute with −41.8% energy density, 18.6-month qualification path."_

### Step 5.2 — Scenario A full walkthrough ✅
- `bom_fixtures/nmc811.json`: cobalt + graphite + nickel + lithium flagged HIGH
- LFP ranked #1 (composite score 67.1), LNMO #2 (71.0), sodium-ion #3 (69.2)
- 7-step qualification roadmap, ~18.6 months
- **Elapsed: 13.4s ✓ (<90s)**

### Step 5.3 — Scenario B: NdFeB magnets ✅
- `bom_fixtures/ncm622_magnet.json`: neodymium/dysprosium flagged HIGH
- Barium ferrite, strontium ferrite, alnico as substitutions
- **Elapsed: 11.4s ✓ (<90s)**

### Step 5.4 — Scenario C: Graphite anode ✅
- `bom_fixtures/graphite_anode.json` created (new fixture)
- China 77% graphite concentration flagged, FEOC=True
- 3 Dec-2023 export control events surfaced (MOFCOM 2023-No.33)
- Silicon blend #1, LTO #2, hard carbon #3 as anode substitutes
- **Elapsed: 17.0s ✓ (<90s)**

**Day 5 gate: ✅ PASSED** — All 3 scenarios <90s, Gemini narrative live, citations present on all numbers.

---

## DAY 6 — Sat May 31 (10 hrs): Deploy + Architecture + Video + Submit

### Step 6.1 — Dockerfile ✅ DONE (May 22)
`deploy/Dockerfile` created: python:3.12-slim, copies parquets into image, streamlit on :8080
`.dockerignore` created: excludes .env, venv, __pycache__
`requirements.txt` created: pinned minimal direct dependencies

**Docker not installed locally** — install it before testing:
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop/
docker build -t matres -f deploy/Dockerfile .
docker run -p 8080:8080 -e GEMINI_API_KEY=<key> matres
# Verify at http://localhost:8080
```

### Step 6.2 — Cloud Run deploy (60 min)
`deploy/cloud_run_deploy.sh` created — run it after installing gcloud CLI:
```bash
# Install gcloud: https://cloud.google.com/sdk/docs/install
gcloud auth login
gcloud config set project materials-resilience-agent
bash deploy/cloud_run_deploy.sh
```
Full script: regenerates parquets → builds image → pushes to gcr.io → deploys with env vars injected.
Note the public URL. Test all 3 scenarios on the live URL.

### Step 6.3 — Architecture diagram ✅ DONE (May 22)
`docs/architecture.drawio` created — import at diagrams.net to view/edit and export PNG.

To export:
1. Go to https://app.diagrams.net
2. File → Import → upload `docs/architecture.drawio`
3. File → Export as PNG → save to `docs/architecture.png`

Architecture includes: User → Streamlit UI → Root Orchestrator (ADK + Gemini 2.5 Pro) → 4 sub-agents → MCP servers (USGS, OEC, Materials Project) + NHTSA DB + Hallucination Guard → RiskReport

### Step 6.4 — 3-min demo video (2 hrs)
Use Loom (loom.com — free) or OBS + screen recording.

**Script:**
- **0:00–0:30 — Problem hook:** Show a news headline about the GM Bolt recall ($1.9B). Say: "This is what happens when a battery material fails at scale. Now show China's graphite export ban headline. "Supply risk and material failure are the same problem. No tool connects them for engineers."
- **0:30–2:00 — Live Scenario A:** Open the app live. Upload nmc811.json. Walk through all 4 tabs. Point out: "Cobalt: DRC 70%, FEOC non-compliant, HIGH risk. LFP is ranked #1 substitute — 8% energy density trade-off, 18-month qualification path, $300k testing cost. Every number is cited."
- **2:00–3:00 — Business impact:** "This replaces 3 weeks of manual supplier analysis. Target customers: EV battery engineers at Tier-1 suppliers. TAM: $4B supply chain risk software market. We're the first agent at the engineering-decision layer."

### Step 6.5 — Devpost submission (90 min)
Go to devpost.team → your project → Edit

Fill in:
- **Title:** MatRes — Materials Resilience Agent
- **Theme:** Track 1: Build (Net-New Agents)
- **Video:** Upload Loom link or video file
- **Code:** https://github.com/raunakmantri9/MatRes (make public now)
- **Testing access:** Cloud Run URL
- **Architecture diagram:** Upload `docs/architecture.png`
- **Problem to solve:** [use draft from earlier session]
- **Our solution:** [use draft from earlier session]
- **Technologies used:** Gemini 2.5 Pro, Google ADK, MCP, Cloud Run, Vertex AI, Python, Streamlit, Pydantic
- **Data sources:** USGS MCS 2025, Materials Project API, NHTSA Recalls, OEC trade data
- **Findings and learnings:** [fill with real observations from the build]
- **Third-party integrations:** Materials Project API (LBNL, free research license), USGS (public domain), NHTSA (public domain), OEC (open data terms)

Click **Submit**. Screenshot the "Submitted" status.

---

## Scope Cut Order (only if a day goes badly)

Cut in this order — Scenario A and hallucination guard are never cut:

1. Drop MCP servers → use direct pandas queries as ADK tools (saves ~2 hrs)
2. Drop Scenario C (graphite anode)
3. Drop Scenario B (NdFeB magnets)
4. Stub QualificationPlanner with hardcoded templates (saves ~1.5 hrs)
5. Stub FailureModePredictor with keyword search instead of RAG (saves ~1 hr)

A single working scenario with full citations and a live URL beats three broken scenarios.

---

## Verification Checklist (before clicking Submit)

- [ ] `python schemas/validate.py bom_fixtures/nmc811.json` → zero errors
- [ ] USGS query → cobalt DRC concentration >60%
- [ ] NHTSA query → GM Bolt recall appears
- [ ] Scenario A: cobalt flagged, LFP in top substitutions, roadmap has ≥4 steps, <90 sec
- [ ] Scenario B: neodymium flagged, ferrite in substitutions, <90 sec
- [ ] Scenario C: graphite China concentration flagged, synthetic substitute returned, <90 sec
- [ ] All numbers in UI have source labels
- [ ] Cloud Run URL is live and all scenarios work
- [ ] Architecture diagram has all components labeled
- [ ] Demo video is exactly 3 min or under
- [ ] GitHub repo is public
- [ ] Devpost status = "Submitted"
