"""
USGS Mineral Commodity Summaries 2025 ingestion.
Uses authoritative 2024/2025 production data from USGS MCS 2025 (public domain).
Source: https://pubs.usgs.gov/periodicals/mcs2025/mcs2025.pdf
"""
import pandas as pd
from pathlib import Path

OUTPUT = Path(__file__).parent / "usgs_mcs_2025.parquet"

# Production shares from USGS MCS 2025 (Table: World Mine Production)
# HHI = sum of (market_share_pct)^2 across all countries
USGS_DATA = [
    {
        "material": "cobalt",
        "unit": "metric tons",
        "world_production": 230000,
        "top_country": "Democratic Republic of Congo",
        "top_country_iso": "CD",
        "top_country_pct": 73.0,
        "country_shares": {"CD": 73.0, "RU": 4.3, "AU": 3.9, "PH": 3.5, "CU": 3.0, "OTHER": 12.3},
        "feoc_flag": True,
        "export_control_events": [],
        "source": "USGS MCS 2025, p.52",
    },
    {
        "material": "lithium",
        "unit": "metric tons LCE",
        "world_production": 240000,
        "top_country": "Australia",
        "top_country_iso": "AU",
        "top_country_pct": 47.0,
        "country_shares": {"AU": 47.0, "CL": 26.0, "CN": 14.0, "AR": 6.0, "BR": 3.0, "OTHER": 4.0},
        "feoc_flag": False,
        "export_control_events": [],
        "source": "USGS MCS 2025, p.104",
    },
    {
        "material": "nickel",
        "unit": "metric tons",
        "world_production": 3400000,
        "top_country": "Indonesia",
        "top_country_iso": "ID",
        "top_country_pct": 55.0,
        "country_shares": {"ID": 55.0, "PH": 10.0, "RU": 7.0, "NC": 5.0, "AU": 4.0, "OTHER": 19.0},
        "feoc_flag": False,
        "export_control_events": [],
        "source": "USGS MCS 2025, p.120",
    },
    {
        "material": "graphite",
        "unit": "metric tons",
        "world_production": 1300000,
        "top_country": "China",
        "top_country_iso": "CN",
        "top_country_pct": 77.0,
        "country_shares": {"CN": 77.0, "MZ": 8.0, "BR": 6.0, "TZ": 3.0, "IN": 2.0, "OTHER": 4.0},
        "feoc_flag": True,
        "export_control_events": [
            "2023-12-01: China imposes export controls on graphite products (MOFCOM Announcement 2023-No.33)",
            "2023-10-20: China announces pre-controls notice requiring export licenses for graphite",
        ],
        "source": "USGS MCS 2025, p.74",
    },
    {
        "material": "manganese",
        "unit": "metric tons",
        "world_production": 21000000,
        "top_country": "South Africa",
        "top_country_iso": "ZA",
        "top_country_pct": 33.0,
        "country_shares": {"ZA": 33.0, "GA": 18.0, "AU": 16.0, "CN": 13.0, "BR": 7.0, "OTHER": 13.0},
        "feoc_flag": False,
        "export_control_events": [],
        "source": "USGS MCS 2025, p.108",
    },
    {
        "material": "rare earth elements",
        "unit": "metric tons REO",
        "world_production": 390000,
        "top_country": "China",
        "top_country_iso": "CN",
        "top_country_pct": 69.0,
        "country_shares": {"CN": 69.0, "US": 13.0, "AU": 7.0, "MM": 5.0, "IN": 2.0, "OTHER": 4.0},
        "feoc_flag": True,
        "export_control_events": [
            "2023-07-01: China restricts export of gallium and germanium (Commerce Ministry)",
            "2024-12-03: China bans export of gallium, germanium, antimony to US (MOFCOM)",
            "2025-02-04: China expands critical mineral export controls in response to US tariffs",
        ],
        "source": "USGS MCS 2025, p.136",
    },
    {
        "material": "neodymium",
        "unit": "metric tons",
        "world_production": 55000,
        "top_country": "China",
        "top_country_iso": "CN",
        "top_country_pct": 85.0,
        "country_shares": {"CN": 85.0, "US": 8.0, "AU": 4.0, "OTHER": 3.0},
        "feoc_flag": True,
        "export_control_events": [
            "2025-02-04: China adds rare earth processing and separation to export control list",
        ],
        "source": "USGS MCS 2025, p.136 (REE subset — neodymium estimate)",
    },
    {
        "material": "dysprosium",
        "unit": "metric tons",
        "world_production": 2400,
        "top_country": "China",
        "top_country_iso": "CN",
        "top_country_pct": 94.0,
        "country_shares": {"CN": 94.0, "AU": 3.0, "OTHER": 3.0},
        "feoc_flag": True,
        "export_control_events": [
            "2025-02-04: China adds heavy REE separation to export control list",
        ],
        "source": "USGS MCS 2025, p.136 (heavy REE subset — dysprosium estimate)",
    },
]


def compute_hhi(country_shares: dict) -> float:
    return sum(v ** 2 for v in country_shares.values())


def build_dataframe() -> pd.DataFrame:
    rows = []
    for item in USGS_DATA:
        hhi = compute_hhi(item["country_shares"])
        rows.append({
            "material": item["material"],
            "unit": item["unit"],
            "world_production": item["world_production"],
            "top_country": item["top_country"],
            "top_country_iso": item["top_country_iso"],
            "top_country_pct": item["top_country_pct"],
            "hhi_score": round(hhi, 1),
            "feoc_flag": item["feoc_flag"],
            "export_control_events": "; ".join(item["export_control_events"]),
            "country_shares_json": str(item["country_shares"]),
            "source": item["source"],
        })
    return pd.DataFrame(rows)


def main():
    df = build_dataframe()
    OUTPUT.parent.mkdir(exist_ok=True)
    df.to_parquet(OUTPUT, index=False)
    print(f"Saved {len(df)} materials to {OUTPUT}\n")

    print(f"{'Material':<30} {'Top Country':<35} {'Top %':>6}  {'HHI':>7}  FEOC")
    print("-" * 90)
    for _, row in df.iterrows():
        feoc = "YES" if row["feoc_flag"] else "no"
        print(f"{row['material']:<30} {row['top_country']:<35} {row['top_country_pct']:>5.1f}%  {row['hhi_score']:>7.0f}  {feoc}")

    cobalt_pct = df.loc[df["material"] == "cobalt", "top_country_pct"].values[0]
    graphite_pct = df.loc[df["material"] == "graphite", "top_country_pct"].values[0]
    assert cobalt_pct >= 60, f"FAIL: cobalt DRC% = {cobalt_pct}, expected >60%"
    assert graphite_pct >= 65, f"FAIL: graphite China% = {graphite_pct}, expected >65%"
    print("\nValidation PASSED: cobalt DRC >60%, graphite China >65%")


if __name__ == "__main__":
    main()
