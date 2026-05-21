"""
FailureModePredictor — ADK tool that surfaces failure modes from NHTSA recall data.
Uses pandas keyword filtering on recall descriptions.
"""
import pandas as pd
from pathlib import Path
from google.adk.tools import FunctionTool
from schemas.models import FailureMode

DATA_DIR = Path(__file__).parent.parent / "data"
_nhtsa_df: pd.DataFrame | None = None

FAILURE_MODE_KEYWORDS = {
    "thermal runaway": ["thermal runaway", "fire", "burning", "smoke", "overheat"],
    "cell defect / separator failure": ["separator", "anode tab", "torn", "folded", "short circuit", "cell"],
    "electrolyte degradation": ["electrolyte", "leak", "electrolyte leak", "corrosion"],
    "BMS / software fault": ["bms", "software", "battery management", "state of charge", "soc", "loss of drive"],
    "dendrite growth": ["dendrite", "lithium plating", "internal short"],
    "capacity degradation": ["capacity", "range", "degradation", "cycle life"],
}

SEVERITY_MAP = {
    "thermal runaway": 5,
    "cell defect / separator failure": 4,
    "electrolyte degradation": 3,
    "BMS / software fault": 3,
    "dendrite growth": 4,
    "capacity degradation": 2,
}


def _nhtsa() -> pd.DataFrame:
    global _nhtsa_df
    if _nhtsa_df is None:
        _nhtsa_df = pd.read_parquet(DATA_DIR / "nhtsa_ev_recalls.parquet")
    return _nhtsa_df


def _classify_mode(text: str) -> str:
    text_lower = text.lower()
    for mode, keywords in FAILURE_MODE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return mode
    return "general battery failure"


def predict_failure_modes(material_name: str) -> list[dict]:
    """
    Return top failure modes associated with a battery material based on NHTSA recalls.

    Args:
        material_name: Name of the material (e.g. 'cobalt', 'graphite', 'lithium')
    """
    df = _nhtsa()

    # All battery recalls are relevant to lithium-ion materials
    battery_keywords = ["battery", "cell", "thermal", "fire", "lithium", "pack", "bms"]
    mask = df["summary"].str.lower().apply(
        lambda t: any(kw in t for kw in battery_keywords)
    )
    relevant = df[mask].copy()

    if relevant.empty:
        relevant = df.copy()

    # Classify each recall into a failure mode
    relevant["failure_mode"] = relevant["summary"].apply(_classify_mode)

    # Aggregate by mode
    grouped = (
        relevant.groupby("failure_mode")
        .agg(
            recall_count=("nhtsa_id", "count"),
            units_affected=("units_affected", "sum"),
            nhtsa_ids=("nhtsa_id", lambda x: list(x.unique())),
            example_summary=("summary", "first"),
        )
        .reset_index()
        .sort_values("recall_count", ascending=False)
    )

    results = []
    for _, row in grouped.head(3).iterrows():
        mode = str(row["failure_mode"])
        ids = row["nhtsa_ids"]
        fm = FailureMode(
            material_name=material_name,
            mode_description=mode,
            source_url="https://www.nhtsa.gov/vehicle-safety/recalls",
            recall_count=int(row["recall_count"]),
            severity=SEVERITY_MAP.get(mode, 3),
            nhtsa_recall_ids=[str(i) for i in ids[:3]],
            source=f"NHTSA recall ID: {', '.join(str(i) for i in ids[:3])}",
        )
        results.append(fm.model_dump())

    return results


# ADK tool wrapper
failure_mode_tool = FunctionTool(predict_failure_modes)
