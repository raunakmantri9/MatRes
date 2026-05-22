"""
MatRes — Materials Resilience Agent
Streamlit UI: upload BOM → run pipeline → display risk report across 4 tabs.
"""
import sys
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="MatRes — Materials Resilience Agent",
    page_icon="⚗️",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚗️ MatRes")
    st.caption("Materials Resilience Agent")
    st.divider()

    uploaded = st.file_uploader(
        "Upload BOM (JSON)",
        type=["json"],
        help="Upload a battery BOM JSON file. See bom_fixtures/ for examples.",
    )

    st.subheader("Scorer Weights")
    w1 = st.slider("Supply Risk (w1)", 0.0, 1.0, 0.40, 0.05)
    w2 = st.slider("Performance Delta (w2)", 0.0, 1.0, 0.25, 0.05)
    w3 = st.slider("Qualification Cost (w3)", 0.0, 1.0, 0.25, 0.05)
    w4 = st.slider("CO₂ Delta (w4)", 0.0, 1.0, 0.10, 0.05)
    total_w = round(w1 + w2 + w3 + w4, 2)
    if abs(total_w - 1.0) > 0.01:
        st.warning(f"Weights sum to {total_w} — ideally should sum to 1.0")

    st.divider()
    st.caption("Data sources: USGS MCS 2025 · Materials Project · NHTSA Recalls · OEC 2023")

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("Materials Resilience Agent")
st.markdown(
    "Upload an EV battery BOM to analyse supply concentration risk, "
    "failure modes, and substitution pathways — with full source citations."
)

RISK_COLORS = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}


def run_pipeline(bom_path: str, weights: dict) -> dict:
    import os
    os.environ["SCORE_W1"] = str(weights["w1"])
    os.environ["SCORE_W2"] = str(weights["w2"])
    os.environ["SCORE_W3"] = str(weights["w3"])
    os.environ["SCORE_W4"] = str(weights["w4"])
    from agents.root_agent import run_pipeline as _run
    return _run(bom_path)


def render_supply_risk(report: dict):
    st.subheader("Supply Concentration Risk")
    rows = []
    for risk in report["supply_risks"]:
        icon = RISK_COLORS.get(risk["risk_level"], "⚪")
        rows.append({
            "Material": risk["material_name"],
            "Top Country": risk["top_country"],
            "Concentration %": f"{risk['top_country_pct']:.1f}%",
            "HHI Score": f"{risk['hhi_score']:.0f}",
            "Risk": f"{icon} {risk['risk_level']}",
            "FEOC": "⚠️ YES" if risk["feoc_flag"] else "✓ No",
            "Source": risk["source"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    high = [r for r in report["supply_risks"] if r["risk_level"] == "HIGH"]
    if high:
        st.error(f"**{len(high)} HIGH-risk material(s):** {', '.join(r['material_name'] for r in high)}")

    if any(r["export_control_events"] for r in report["supply_risks"]):
        st.subheader("Active Export Control Events")
        for risk in report["supply_risks"]:
            for event in risk["export_control_events"]:
                st.warning(f"**{risk['material_name'].title()}** — {event}")


def render_failure_modes(report: dict):
    st.subheader("Failure Mode Analysis (NHTSA Recalls)")
    if not report["failure_modes"]:
        st.info("No failure modes identified for materials in this BOM.")
        return

    rows = []
    severity_icons = {5: "🔴🔴", 4: "🔴", 3: "🟡", 2: "🟢", 1: "🟢"}
    for fm in report["failure_modes"]:
        rows.append({
            "Material": fm["material_name"],
            "Failure Mode": fm["mode_description"].title(),
            "Recall Count": fm["recall_count"],
            "Severity": f"{severity_icons.get(fm['severity'], '')} {fm['severity']}/5",
            "NHTSA IDs": ", ".join(fm.get("nhtsa_recall_ids", [])[:3]),
            "Source": fm["source"],
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_substitutions(report: dict):
    st.subheader("Substitution Candidates")
    if not report["substitutions"]:
        st.info("No substitutions generated — no HIGH risk materials found.")
        return

    for sub in sorted(report["substitutions"], key=lambda x: x["ranked_position"]):
        rank = sub["ranked_position"]
        score = sub.get("composite_score", 0)
        delta = sub.get("property_delta", {})
        energy = delta.get("energy_density_pct", 0)
        cycles = delta.get("cycle_life_pct", 0)
        thermal = delta.get("thermal_stability", "Unknown")
        cost_d = delta.get("cost_delta_pct", 0)

        medal = ["🥇", "🥈", "🥉"][rank - 1]
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {medal} #{rank}: {sub['substitute_name']}")
                st.caption(f"Replaces: {sub['original_material']} | Source: {sub['source'][:80]}")
            with col2:
                st.metric("Composite Score", f"{score:.0f}/100")

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Energy Density", f"{energy:+.0f}%", delta_color="inverse" if energy < 0 else "normal")
            c2.metric("Cycle Life", f"{cycles:+.0f}%", delta_color="normal" if cycles > 0 else "inverse")
            c3.metric("Thermal Stability", thermal)
            c4.metric("Cost Delta", f"{cost_d:+.0f}%", delta_color="normal" if cost_d < 0 else "inverse")
            c5.metric("Supply Risk", f"{sub['supply_risk_score']:.0f}/100", delta_color="inverse")

            with st.expander("Property delta source"):
                st.caption(delta.get("source", sub["source"]))


def render_qualification(report: dict):
    st.subheader("Qualification Roadmap")
    if not report["qualification_roadmap"]:
        st.info("No qualification roadmap generated.")
        return

    steps = report["qualification_roadmap"]
    total_weeks = sum(s["duration_weeks"] for s in steps)
    total_low = sum(s["cost_band_usd_low"] for s in steps)
    total_high = sum(s["cost_band_usd_high"] for s in steps)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Steps", len(steps))
    col2.metric("Total Duration", f"{total_weeks} wks ({total_weeks/4.3:.0f} mo)")
    col3.metric("Total Cost", f"${total_low//1000}k–${total_high//1000}k")

    st.divider()
    rows = []
    cumulative = 0
    for i, step in enumerate(steps, 1):
        cumulative += step["duration_weeks"]
        rows.append({
            "Step": i,
            "Name": step["step_name"],
            "Standard": step["standard"],
            "Duration (wks)": step["duration_weeks"],
            "Cumulative (mo)": f"{cumulative/4.3:.1f}",
            "Cost Range": f"${step['cost_band_usd_low']//1000}k–${step['cost_band_usd_high']//1000}k",
            "Source": step.get("source", ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ── Main flow ──────────────────────────────────────────────────────────────────
if uploaded is None:
    st.info("👈 Upload a BOM JSON file in the sidebar to begin analysis.")
    with st.expander("Show example BOM fixtures"):
        fixture_dir = Path(__file__).parent.parent / "bom_fixtures"
        for f in sorted(fixture_dir.glob("*.json")):
            bom = json.loads(f.read_text())
            st.markdown(f"**{f.name}** — {bom.get('bom_name', f.stem)}")
            st.caption(f"{len(bom.get('components', []))} components")
else:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="wb") as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    weights = {"w1": w1, "w2": w2, "w3": w3, "w4": w4}

    with st.spinner("Running MatRes pipeline..."):
        try:
            report = run_pipeline(tmp_path, weights)
            st.session_state["report"] = report
            st.session_state["bom_name"] = report.get("bom_name", uploaded.name)
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

    report = st.session_state.get("report")
    if report:
        elapsed = report.get("elapsed_seconds", 0)
        st.success(f"Analysis complete in {elapsed}s — **{report['bom_name']}**")

        summary = report.get("executive_summary", "")
        if summary:
            st.info(f"**Gemini 2.5 Pro Analysis**\n\n{summary}")

        tab1, tab2, tab3, tab4 = st.tabs([
            "🌍 Supply Risk",
            "⚠️ Failure Modes",
            "🔄 Substitutions",
            "📋 Qualification Roadmap",
        ])
        with tab1:
            render_supply_risk(report)
        with tab2:
            render_failure_modes(report)
        with tab3:
            render_substitutions(report)
        with tab4:
            render_qualification(report)

        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            high_count = sum(1 for r in report["supply_risks"] if r["risk_level"] == "HIGH")
            if high_count > 0:
                top_sub = report["substitutions"][0] if report["substitutions"] else None
                if top_sub:
                    st.info(
                        f"**Recommendation:** {high_count} HIGH-risk material(s) identified. "
                        f"Top substitution: **{top_sub['substitute_name']}** "
                        f"(composite score {top_sub.get('composite_score', 0):.0f}/100). "
                        f"Qualification timeline: ~{sum(s['duration_weeks'] for s in report['qualification_roadmap'])/4.3:.0f} months."
                    )
        with col2:
            st.download_button(
                "⬇️ Download Report (JSON)",
                data=json.dumps(report, indent=2, default=str),
                file_name=f"matres_report_{report['bom_name'].replace(' ', '_')[:30]}.json",
                mime="application/json",
            )
