"""
MatRes root orchestrator agent.
Parses a BOM JSON, runs all 4 sub-agents per component, and aggregates RiskReport.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google import genai as google_genai

load_dotenv(Path(__file__).parent.parent / ".env")

APP_NAME = "matres"
MODEL = "gemini-2.5-pro-preview-05-06"


def create_root_agent() -> Agent:
    return Agent(
        name="matres_root",
        model=MODEL,
        description="Materials Resilience Agent — orchestrates supply risk, failure mode, substitution, and qualification analysis for EV battery BOMs.",
        instruction="""You are the MatRes orchestrator. When given a BOM JSON file path:
1. Parse the BOM and identify all components with their material names.
2. For each component, analyse supply risk using USGS and OEC data.
3. For each high-risk material, identify top failure modes from NHTSA recall data.
4. Generate 3 ranked substitution candidates with property deltas.
5. Build a qualification roadmap for the top-ranked substitution.
6. Return a complete RiskReport JSON. Every numeric value must include a source citation.""",
    )


def hello_world_test():
    """Verify ADK connects to Gemini and responds."""
    client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly: MatRes ADK connection OK",
    )
    print(f"ADK hello-world: {response.text.strip()}")
    assert "OK" in response.text, "Gemini connection test failed"
    print("ADK connection PASSED")


def run_agent_on_bom(bom_path: str):
    """Run the root agent on a BOM file (full ADK session)."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=create_root_agent(),
        app_name=APP_NAME,
        session_service=session_service,
    )
    session = session_service.create_session(app_name=APP_NAME, user_id="user_1")

    from google.adk.types import Content, Part
    message = Content(role="user", parts=[
        Part(text=f"Analyse this BOM file and return a complete RiskReport: {bom_path}")
    ])

    print(f"Running MatRes agent on {bom_path}...")
    for event in runner.run(
        user_id="user_1",
        session_id=session.id,
        new_message=message,
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--hello":
        hello_world_test()
    elif len(sys.argv) > 1:
        run_agent_on_bom(sys.argv[1])
    else:
        hello_world_test()
