# MatRes — Materials Resilience Agent

**Supply-risk-aware BOM advisor for EV battery engineering teams.**

Upload a battery Bill of Materials → get geopolitical risk scores, real recall data, ranked substitution candidates, and a full qualification roadmap — in under 90 seconds.

Built for the [Google for Startups AI Agents Challenge](https://googleforstartups.devpost.com/) · Track 1: Build · Powered by Gemini 2.5 Pro + Google ADK

**Live demo:** https://matres-705351137331.us-central1.run.app

---

## The Problem

EV battery engineers face a recurring crisis: they design a pack around a specific material (cobalt, graphite, neodymium), then geopolitical events force a scramble for substitutes. Today that analysis takes **3–6 weeks** across procurement, materials science, and legal teams.

- China controls 77% of graphite supply and imposed export controls in Dec 2023
- 73% of cobalt comes from the DRC, flagged under US IRA 2022 FEOC rules
- GM's Bolt recall cost $1.9B — lithium battery thermal runaway, 141,667 vehicles

MatRes compresses this to **under 90 seconds**.

---

## What It Does

Upload a BOM JSON → 4 AI agents run in sequence:

| Agent | What it does | Data source |
|-------|-------------|-------------|
| **SupplyRiskAnalyzer** | Computes HHI concentration score, FEOC flag, active export controls | USGS MCS 2025, OEC 2023 |
| **FailureModePredictor** | Surfaces real recalls by failure mode and severity | NHTSA EV recalls 2018–2026 |
| **SubstitutionGenerator** | Ranks 3 alternative materials with property deltas | Materials Project (LBNL) |
| **QualificationPlanner** | Builds the full testing roadmap with timeline and cost band | UN 38.3, IEC 62660, UL 2580 |

Every number in the output has a source citation. A hallucination guard rejects any numeric claim without a `source:` field before it reaches the UI.

---

## Architecture

```
User: BOM JSON
       ↓
[Streamlit UI — 4 tabs + weight sliders]
       ↓
[Root Orchestrator — Google ADK + Gemini 2.5 Pro]
  ↙        ↙           ↘           ↘
[Supply  [Failure   [Substitution  [Qualification
 Risk]    Mode]      Generator]    Planner]
  ↓          ↓            ↓              ↓
[USGS MCS  [NHTSA    [Materials     [Standards
 2025 +     Recalls]  Project API]   Templates]
 OEC 2023]
       ↓
[Hallucination Guard — CitationError if unsourced number]
       ↓
[RiskReport + Composite Score (0–100)]
       ↓
[Cloud Run — GCP us-central1]
```

---

## Demo Scenarios

| Scenario | BOM | Risk flagged | Top substitution |
|----------|-----|-------------|------------------|
| **A** | NMC 811 cathode | Cobalt — DRC 73%, FEOC | LFP — 18-month qualification, $925k–$1.85M |
| **B** | NCM 622 + NdFeB motor | Neodymium — China 85%, FEOC | Barium ferrite |
| **C** | LFP pack | Graphite — China 77%, Dec 2023 export ban | Silicon blend |

---

## Tech Stack

- **Intelligence:** Gemini 2.5 Pro (via Vertex AI)
- **Orchestration:** Google Agent Development Kit (ADK) with FunctionTool wrappers
- **Data protocol:** MCP servers for USGS and Materials Project data
- **Schemas:** Pydantic v2 with hallucination guard middleware
- **UI:** Streamlit
- **Infrastructure:** Cloud Run (GCP us-central1), Secret Manager, Cloud Build

---

## Data Sources

| Source | What | License |
|--------|------|---------|
| USGS Mineral Commodity Summaries 2025 | Country production shares, HHI scores | Public domain |
| Materials Project API (LBNL) | Formation energy, stability, band gap | Free research license |
| NHTSA EV Recalls 2018–2026 | Recall descriptions, units affected | Public domain |
| OEC Trade Data 2023 | Export flows, trade restrictions | Open data |

---

## Run Locally

```bash
git clone https://github.com/raunakmantri9/MatRes
cd MatRes
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Add your keys to .env (see .env.example)
cp .env.example .env
# Edit .env with GEMINI_API_KEY and MATERIALS_PROJECT_API_KEY

# Generate data
python data/ingest_usgs.py
python data/ingest_materials_project.py
python data/ingest_nhtsa.py
python data/ingest_oec.py

# Run
streamlit run ui/streamlit_app.py
```

Then upload any file from `bom_fixtures/` to start.

---

## Run a BOM from CLI

```bash
python -m agents.root_agent bom_fixtures/nmc811.json
```

---

## Project Structure

```
agents/          # 4 ADK sub-agents + root orchestrator
bom_fixtures/    # 3 demo BOMs (NMC 811, LFP, NCM 622 + magnet)
data/            # Ingest scripts for USGS, Materials Project, NHTSA, OEC
deploy/          # Dockerfile, Cloud Run deploy script
docs/            # Architecture diagram
mcp_servers/     # MCP servers for USGS and Materials Project
schemas/         # Pydantic models + hallucination guard
ui/              # Streamlit app
```

---

## Composite Scorer

Substitutions are ranked by a weighted formula (tunable via sidebar sliders):

| Factor | Default weight | What it measures |
|--------|---------------|-----------------|
| Supply risk improvement | 40% | Lower HHI of substitute = better |
| Performance delta | 25% | Energy density trade-off vs. original |
| Qualification cost | 25% | Lower testing cost = better |
| CO₂ delta | 10% | Emissions benefit of switching |
