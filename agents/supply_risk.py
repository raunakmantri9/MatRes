"""
SupplyRiskAnalyzer — ADK tool that scores supply concentration risk per material.
Data sources: USGS MCS 2025 parquet, OEC 2023 parquet.
"""
import json
import pandas as pd
from pathlib import Path
from google.adk.tools import FunctionTool
from schemas.models import SupplyConcentration

DATA_DIR = Path(__file__).parent.parent / "data"
_usgs_df: pd.DataFrame | None = None
_oec_df: pd.DataFrame | None = None


def _usgs() -> pd.DataFrame:
    global _usgs_df
    if _usgs_df is None:
        _usgs_df = pd.read_parquet(DATA_DIR / "usgs_mcs_2025.parquet")
    return _usgs_df


def _oec() -> pd.DataFrame:
    global _oec_df
    if _oec_df is None:
        _oec_df = pd.read_parquet(DATA_DIR / "oec_flows.parquet")
    return _oec_df


FEOC_COUNTRIES = {"China", "Russia", "Iran", "North Korea", "Democratic Republic of Congo"}

HHI_THRESHOLDS = {"HIGH": 2500, "MEDIUM": 1500}


def _risk_level(hhi: float) -> str:
    if hhi >= HHI_THRESHOLDS["HIGH"]:
        return "HIGH"
    if hhi >= HHI_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def analyze_supply_risk(material_name: str) -> dict:
    """
    Analyze supply concentration risk for a given material.
    Returns a SupplyConcentration-compatible dict with source citations.

    Args:
        material_name: Name of the material (e.g. 'cobalt', 'graphite', 'neodymium')
    """
    usgs = _usgs()
    oec = _oec()

    # Match material in USGS — try exact then partial
    row = usgs[usgs["material"] == material_name.lower()]
    if row.empty:
        row = usgs[usgs["material"].str.contains(material_name.lower(), case=False, na=False)]

    if row.empty:
        return {
            "material_name": material_name,
            "top_country": "Unknown",
            "top_country_pct": 0.0,
            "hhi_score": 0.0,
            "feoc_flag": False,
            "risk_level": "LOW",
            "export_control_events": [],
            "source": "USGS MCS 2025 — material not found",
            "error": f"Material '{material_name}' not in USGS dataset",
        }

    r = row.iloc[0]
    hhi = float(r["hhi_score"])
    top_country = str(r["top_country"])
    top_pct = float(r["top_country_pct"])
    feoc = bool(r["feoc_flag"])
    events_raw = str(r.get("export_control_events", "") or "")
    events = [e.strip() for e in events_raw.split(";") if e.strip()]

    # Supplement with OEC trade restriction events
    oec_mat = oec[oec["material"] == material_name.lower()]
    if not oec_mat.empty:
        oec_restrictions = str(oec_mat.iloc[0].get("trade_restrictions", "") or "")
        oec_events = [e.strip() for e in oec_restrictions.split(";") if e.strip()]
        for ev in oec_events:
            if ev and ev not in events:
                events.append(ev)

    result = SupplyConcentration(
        material_name=material_name,
        top_country=top_country,
        top_country_pct=top_pct,
        hhi_score=hhi,
        feoc_flag=feoc,
        risk_level=_risk_level(hhi),
        export_control_events=events,
        source=str(r["source"]),
    )
    return result.model_dump()


def get_hhi_score(material_name: str) -> dict:
    """
    Return just the HHI score and risk level for a material.

    Args:
        material_name: Name of the material
    """
    result = analyze_supply_risk(material_name)
    return {
        "material_name": material_name,
        "hhi_score": result["hhi_score"],
        "risk_level": result["risk_level"],
        "source": result["source"],
    }


# ADK tool wrappers
supply_risk_tool = FunctionTool(analyze_supply_risk)
hhi_tool = FunctionTool(get_hhi_score)
