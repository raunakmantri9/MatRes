"""
MatRes root orchestrator.
Parses a BOM JSON, runs all 4 sub-agents per high-risk component,
applies hallucination guard, and aggregates a RiskReport.
"""
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agents.supply_risk import analyze_supply_risk, supply_risk_tool, hhi_tool
from agents.failure_mode import predict_failure_modes, failure_mode_tool
from agents.substitution import generate_substitutions, substitution_tool
from agents.qualification import plan_qualification, qualification_tool, qualification_summary_tool
from schemas.models import BOMComponent, RiskReport
from schemas.validator import validate_citations, CitationError

load_dotenv(Path(__file__).parent.parent / ".env")

APP_NAME = "matres"
MODEL = "gemini-2.5-pro"
HIGH_RISK_THRESHOLD = 1500  # HHI >= this triggers full sub-agent pipeline

MATERIAL_CATEGORIES = {
    "cobalt": "cathode",
    "nickel": "cathode",
    "manganese": "cathode",
    "lithium": "cathode",
    "graphite": "anode",
    "silicon": "anode",
    "lithium hexafluorophosphate": "anode",
    "neodymium": "magnet",
    "dysprosium": "magnet",
    "boron": "magnet",
    "iron": "magnet",
    "copper": "cathode",
    "aluminum": "cathode",
    "iron phosphate": "cathode",
}


def _get_category(material_name: str) -> str:
    return MATERIAL_CATEGORIES.get(material_name.lower(), "cathode")


def create_root_agent() -> Agent:
    return Agent(
        name="matres_root",
        model=MODEL,
        description=(
            "Materials Resilience Agent — orchestrates supply risk, failure mode, "
            "substitution, and qualification analysis for EV battery BOMs."
        ),
        instruction="""You are the MatRes orchestrator. When given a BOM JSON:
1. Parse components and identify material names.
2. For each component call analyze_supply_risk to get HHI and risk level.
3. For HIGH/MEDIUM risk materials call predict_failure_modes.
4. For HIGH risk materials call generate_substitutions to get 3 ranked alternatives.
5. For the top substitution call plan_qualification to get the roadmap.
6. Return a structured RiskReport. Every number must have a source citation.""",
        tools=[supply_risk_tool, hhi_tool, failure_mode_tool,
               substitution_tool, qualification_tool, qualification_summary_tool],
    )


def run_pipeline(bom_path: str) -> dict:
    """
    Run the full MatRes pipeline on a BOM file.
    Returns a RiskReport-compatible dict.
    """
    t0 = time.time()
    bom = json.loads(Path(bom_path).read_text())
    bom_name = bom.get("bom_name", Path(bom_path).stem)
    components = [BOMComponent(**c) for c in bom["components"]]

    supply_risks = []
    failure_modes = []
    substitutions = []
    qualification_roadmap = []

    for comp in components:
        mat = comp.material_name

        # Step 1 — supply risk for every component
        risk = analyze_supply_risk(mat)
        try:
            validate_citations(risk, context=f"SupplyRisk:{mat}")
        except CitationError as e:
            print(f"  WARNING: {e}")
        supply_risks.append(risk)

        hhi = risk.get("hhi_score", 0)
        risk_level = risk.get("risk_level", "LOW")

        # Step 2 — failure modes for HIGH/MEDIUM risk
        if risk_level in ("HIGH", "MEDIUM"):
            fms = predict_failure_modes(mat)
            for fm in fms:
                try:
                    validate_citations(fm, context=f"FailureMode:{mat}")
                except CitationError as e:
                    print(f"  WARNING: {e}")
            failure_modes.extend(fms)

        # Step 3 — substitutions only for HIGH risk
        if risk_level == "HIGH" and not substitutions:
            cat = _get_category(mat)
            subs = generate_substitutions(mat, cat, float(hhi))
            for s in subs:
                try:
                    validate_citations(s, context=f"Substitution:{mat}")
                except CitationError as e:
                    print(f"  WARNING: {e}")
            substitutions.extend(subs)

            # Step 4 — qualification roadmap for top substitution
            if subs:
                top = subs[0]
                roadmap = plan_qualification(mat, top["substitute_name"], cat)
                qualification_roadmap.extend(roadmap)

    elapsed = time.time() - t0
    report = RiskReport(
        bom_name=bom_name,
        components=components,
        supply_risks=supply_risks,
        failure_modes=failure_modes,
        substitutions=substitutions,
        qualification_roadmap=qualification_roadmap,
    )
    result = report.model_dump()
    result["elapsed_seconds"] = round(elapsed, 1)
    return result


def hello_world_test():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly: MatRes ADK connection OK",
    )
    print(f"ADK hello-world: {response.text.strip()}")
    assert "OK" in response.text, "Gemini connection test failed"
    print("ADK connection PASSED")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--hello":
        hello_world_test()
    elif len(sys.argv) > 1:
        bom = sys.argv[1]
        report = run_pipeline(bom)
        out = Path(bom).parent / "risk_report_output.json"
        out.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nRiskReport saved to {out}")
        print(f"Components: {len(report['components'])}")
        print(f"Supply risks: {len(report['supply_risks'])}")
        print(f"Failure modes: {len(report['failure_modes'])}")
        print(f"Substitutions: {len(report['substitutions'])}")
        print(f"Qualification steps: {len(report['qualification_roadmap'])}")
        print(f"Elapsed: {report['elapsed_seconds']}s")
    else:
        hello_world_test()
