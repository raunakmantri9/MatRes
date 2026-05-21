"""
Materials Project API ingestion for battery-relevant materials.
Pulls formation energy, energy above hull, band gap, and available
electrochemical properties for cathode, anode, and magnet materials.
Source: https://next.materialsproject.org/api
"""
import os
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OUTPUT = Path(__file__).parent / "materials_project_battery.parquet"
API_KEY = os.getenv("MATERIALS_PROJECT_API_KEY")

QUERIES = [
    # (formula, category, common_name)
    ("LiFePO4",              "cathode", "LFP"),
    ("LiCoO2",               "cathode", "LCO"),
    ("LiNiO2",               "cathode", "LNO"),
    ("LiMnO2",               "cathode", "LMO"),
    ("LiNi0.8Co0.1Mn0.1O2", "cathode", "NMC 811"),
    ("LiNi0.6Co0.2Mn0.2O2", "cathode", "NCM 622"),
    ("LiNi0.5Co0.2Mn0.3O2", "cathode", "NCM 523"),
    ("LiMn2O4",              "cathode", "LMO spinel"),
    ("LiNi0.5Mn1.5O4",      "cathode", "LNMO"),
    ("C",                    "anode",   "graphite"),
    ("Si",                   "anode",   "silicon"),
    ("Li4Ti5O12",            "anode",   "LTO"),
    ("Nd2Fe14B",             "magnet",  "NdFeB"),
    ("BaFe12O19",            "magnet",  "barium ferrite"),
    ("SrFe12O19",            "magnet",  "strontium ferrite"),
    ("Fe3O4",                "magnet",  "magnetite"),
]


def fetch_material(session, formula: str, category: str, common_name: str) -> list[dict]:
    from mp_api.client import MPRester
    results = []
    try:
        with MPRester(API_KEY) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=["material_id", "formula_pretty", "formation_energy_per_atom",
                        "energy_above_hull", "band_gap", "is_stable", "nsites",
                        "volume", "density"],
            )
            for doc in docs[:3]:
                results.append({
                    "material_id": doc.material_id,
                    "formula": doc.formula_pretty,
                    "common_name": common_name,
                    "category": category,
                    "formation_energy_per_atom": doc.formation_energy_per_atom,
                    "energy_above_hull": doc.energy_above_hull,
                    "band_gap": doc.band_gap,
                    "is_stable": doc.is_stable,
                    "nsites": doc.nsites,
                    "density_g_cm3": doc.density,
                    "source": f"Materials Project {doc.material_id}",
                })
    except Exception as e:
        print(f"  WARNING: {formula} ({common_name}) — {e}")
    return results


def main():
    if not API_KEY:
        print("ERROR: MATERIALS_PROJECT_API_KEY not set in .env")
        return

    try:
        from mp_api.client import MPRester
    except ImportError:
        import subprocess, sys
        print("Installing mp-api...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mp-api"])
        from mp_api.client import MPRester

    print(f"Querying Materials Project for {len(QUERIES)} formulas...\n")
    all_rows = []

    for formula, category, common_name in QUERIES:
        print(f"  {common_name:<20} ({formula})")
        rows = fetch_material(None, formula, category, common_name)
        all_rows.extend(rows)
        time.sleep(0.3)

    df = pd.DataFrame(all_rows)
    OUTPUT.parent.mkdir(exist_ok=True)
    df.to_parquet(OUTPUT, index=False)

    print(f"\nSaved {len(df)} entries to {OUTPUT}")
    print(f"\n{'Material':<20} {'Formula':<28} {'Category':<10} {'Hull (eV/atom)':>15}  {'Stable'}")
    print("-" * 85)
    for _, row in df.iterrows():
        stable = "YES" if row["is_stable"] else "no"
        hull = f"{row['energy_above_hull']:.4f}" if pd.notna(row["energy_above_hull"]) else "N/A"
        print(f"{row['common_name']:<20} {row['formula']:<28} {row['category']:<10} {hull:>15}  {stable}")

    print(f"\nTotal entries: {len(df)}")


if __name__ == "__main__":
    main()
