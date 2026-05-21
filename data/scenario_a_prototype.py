"""
Scenario A Prototype: NMC 811 → cobalt risk → LFP substitution.
Tests the full reasoning chain using Gemini before porting to ADK.
Run ONLY after confirming GEMINI_API_KEY is set in .env.
"""
import os
import json
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(Path(__file__).parent.parent / ".env")

BASE = Path(__file__).parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not set in .env")

genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")


def load_cobalt_bom_entry() -> dict:
    bom = json.loads((BASE.parent / "bom_fixtures/nmc811.json").read_text())
    for c in bom["components"]:
        if c["material_name"] == "cobalt":
            return c
    raise ValueError("cobalt not found in nmc811.json")


def load_usgs_row(material: str) -> dict:
    df = pd.read_parquet(BASE / "usgs_mcs_2025.parquet")
    row = df[df["material"] == material].iloc[0].to_dict()
    return row


def load_materials_project_candidates() -> list[dict]:
    df = pd.read_parquet(BASE / "materials_project_battery.parquet")
    cathodes = df[df["category"] == "cathode"].to_dict("records")
    return cathodes


def load_nhtsa_cobalt_failures() -> list[dict]:
    df = pd.read_parquet(BASE / "nhtsa_ev_recalls.parquet")
    relevant = df[df["summary"].str.contains("thermal|battery|cell|fire", case=False, na=False)]
    return relevant.head(3).to_dict("records")


def prompt1_supply_risk(cobalt_component: dict, usgs_row: dict) -> dict:
    prompt = f"""You are a supply chain risk analyst for EV battery materials.

BOM COMPONENT:
{json.dumps(cobalt_component, indent=2)}

USGS MCS 2025 DATA FOR COBALT:
- Top producing country: {usgs_row['top_country']} ({usgs_row['top_country_pct']}% of world production)
- HHI concentration score: {usgs_row['hhi_score']} (out of 10,000 — >2500 = HIGH concentration)
- FEOC flag: {usgs_row['feoc_flag']} (Foreign Entity of Concern under US IRA 2022)
- Export control events: {usgs_row['export_control_events'] or 'None on record'}
- Source: {usgs_row['source']}

Analyze the supply risk for cobalt in this EV battery BOM. Return ONLY a JSON object with these fields:
{{
  "material_name": "cobalt",
  "top_country": "<country name>",
  "top_country_pct": <number>,
  "hhi_score": <number>,
  "feoc_flag": <true/false>,
  "risk_level": "<HIGH|MEDIUM|LOW>",
  "export_control_events": ["<event with date>"],
  "reasoning": "<2-3 sentences explaining the risk rating>",
  "source": "USGS MCS 2025"
}}

Every numeric value must be sourced from the data provided above. Do not invent numbers."""

    resp = MODEL.generate_content(prompt)
    text = resp.text.strip()
    if "```" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    return json.loads(text)


def prompt2_substitutions(risk_result: dict, mp_candidates: list[dict]) -> list[dict]:
    candidates_summary = []
    for c in mp_candidates[:8]:
        candidates_summary.append({
            "material_id": c.get("material_id"),
            "formula": c.get("formula"),
            "common_name": c.get("common_name"),
            "formation_energy_per_atom": c.get("formation_energy_per_atom"),
            "energy_above_hull": c.get("energy_above_hull"),
            "is_stable": c.get("is_stable"),
            "source": c.get("source"),
        })

    prompt = f"""You are a materials scientist specializing in EV battery chemistry.

ORIGINAL MATERIAL: cobalt (in NMC 811 cathode — LiNi0.8Co0.1Mn0.1O2)
SUPPLY RISK ASSESSMENT: {json.dumps(risk_result, indent=2)}

MATERIALS PROJECT CANDIDATE DATA:
{json.dumps(candidates_summary, indent=2)}

KNOWN PERFORMANCE BENCHMARKS (cite these in your response):
- NMC 811 energy density: ~275 Wh/kg (cell level)
- NMC 811 cycle life: ~1000 cycles to 80% capacity
- LFP energy density: ~160 Wh/kg (cell level) — Source: NREL Battery Performance Report 2023
- LFP cycle life: ~3000 cycles to 80% capacity — Source: NREL Battery Performance Report 2023
- LFP thermal runaway threshold: >270°C vs NMC 811 ~210°C — Source: Journal of Power Sources 2022
- LFP supply risk score: LOW (iron abundant, phosphate abundant)
- LNMO energy density: ~220 Wh/kg (cell level) — Source: Journal of Materials Chemistry A 2023
- Sodium-ion energy density: ~140 Wh/kg (cell level) — Source: CATL Technical Bulletin 2023

Generate exactly 3 ranked substitution candidates for cobalt/NMC 811. Return ONLY a JSON array:
[
  {{
    "ranked_position": 1,
    "original_material": "cobalt",
    "substitute_name": "<name>",
    "substitute_chemistry": "<formula>",
    "property_delta": {{
      "energy_density_pct": <number — % change vs NMC 811, negative = lower>,
      "cycle_life_pct": <number — % change, positive = better>,
      "thermal_stability": "<Better|Similar|Worse>",
      "cost_delta_pct": <number — % cost change>
    }},
    "supply_risk_score": <0-100, lower = safer>,
    "co2_delta_pct": <number — % CO2 change in production>,
    "qualification_note": "<1 sentence on key engineering tradeoff>",
    "source": "<cite the data source for each number>"
  }},
  ...
]

Cite every numeric value. LFP should be ranked #1 given the supply risk profile."""

    resp = MODEL.generate_content(prompt)
    text = resp.text.strip()
    if "```" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    return json.loads(text)


def prompt3_qualification_roadmap(substitution: dict) -> list[dict]:
    prompt = f"""You are a battery qualification engineer with experience in UN 38.3, IEC 62660, and UL 2580.

SUBSTITUTION BEING QUALIFIED:
- From: NMC 811 (LiNi0.8Co0.1Mn0.1O2)
- To: {substitution['substitute_name']} ({substitution['substitute_chemistry']})
- Application: 75 kWh EV battery pack
- Key delta: {json.dumps(substitution['property_delta'])}

Generate an ordered qualification roadmap. Return ONLY a JSON array of steps:
[
  {{
    "step_name": "<name>",
    "standard": "<applicable standard — e.g. UN 38.3, IEC 62660-1, UL 2580, ISO 26262>",
    "duration_weeks": <integer>,
    "cost_band_usd_low": <integer>,
    "cost_band_usd_high": <integer>,
    "description": "<what is tested and why>"
  }},
  ...
]

Include at least 6 steps from cell-level through production ramp.
Timeline should total 14-20 months.
Cost bands should reflect realistic US/EU third-party testing facility rates."""

    resp = MODEL.generate_content(prompt)
    text = resp.text.strip()
    if "```" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    return json.loads(text)


def main():
    print("=" * 60)
    print("SCENARIO A: NMC 811 → Cobalt Risk → LFP Substitution")
    print("=" * 60)

    print("\n[1/3] Loading data...")
    cobalt = load_cobalt_bom_entry()
    usgs = load_usgs_row("cobalt")
    mp_candidates = load_materials_project_candidates()
    print(f"  BOM: {cobalt['component_name']} ({cobalt['quantity_kg']} kg, {cobalt['supplier_country']})")
    print(f"  USGS: cobalt {usgs['top_country_pct']}% {usgs['top_country']}, HHI {usgs['hhi_score']}")
    print(f"  Materials Project: {len(mp_candidates)} cathode candidates")

    print("\n[2/3] Prompt 1 — Supply Risk Analysis...")
    risk = prompt1_supply_risk(cobalt, usgs)
    print(f"  Risk level: {risk['risk_level']}")
    print(f"  {risk['reasoning']}")

    print("\n[3/3] Prompt 2 — Substitution Generation...")
    subs = prompt2_substitutions(risk, mp_candidates)
    for s in subs:
        delta = s["property_delta"]
        print(f"  #{s['ranked_position']}: {s['substitute_name']} | "
              f"Energy {delta['energy_density_pct']:+.0f}% | "
              f"Cycles {delta['cycle_life_pct']:+.0f}% | "
              f"Supply risk {s['supply_risk_score']}/100")

    print("\n[4/3] Prompt 3 — Qualification Roadmap for top substitution...")
    roadmap = prompt3_qualification_roadmap(subs[0])
    total_weeks = sum(s["duration_weeks"] for s in roadmap)
    print(f"  {len(roadmap)} steps | {total_weeks} weeks total ({total_weeks/4.3:.0f} months)")
    for step in roadmap:
        print(f"  • {step['step_name']:<40} {step['duration_weeks']:>3} wks  "
              f"${step['cost_band_usd_low']//1000}k–${step['cost_band_usd_high']//1000}k  "
              f"[{step['standard']}]")

    output = {
        "scenario": "A",
        "bom": "NMC 811 — 75 kWh EV Battery Pack",
        "supply_risk": risk,
        "substitutions": subs,
        "qualification_roadmap": roadmap,
    }
    out_path = BASE.parent / "data/scenario_a_output.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nFull output saved to {out_path}")

    assert risk["risk_level"] == "HIGH", f"Expected HIGH risk for cobalt, got {risk['risk_level']}"
    assert subs[0]["ranked_position"] == 1
    assert len(roadmap) >= 4, f"Expected >=4 qualification steps, got {len(roadmap)}"
    lfp_found = any("lfp" in s["substitute_name"].lower() or
                    "iron" in s["substitute_name"].lower() or
                    "lifepo" in s.get("substitute_chemistry", "").lower()
                    for s in subs)
    assert lfp_found, "LFP should appear in top substitutions"
    print("\nAll assertions PASSED — Scenario A prototype validated")


if __name__ == "__main__":
    main()
