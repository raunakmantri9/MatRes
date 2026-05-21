"""
MCP server wrapping Materials Project battery materials data.
Tools: get_material_properties, find_substitutes
Run standalone: python -m mcp_servers.materials_project_server
"""
import json
from pathlib import Path
import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

DATA_DIR = Path(__file__).parent.parent / "data"
_df: pd.DataFrame | None = None


def _load() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_parquet(DATA_DIR / "materials_project_battery.parquet")
    return _df


def get_material_properties(material_name: str) -> dict:
    df = _load()
    row = df[
        (df["common_name"].str.lower() == material_name.lower()) |
        (df["formula"].str.lower() == material_name.lower())
    ]
    if row.empty:
        row = df[df["common_name"].str.contains(material_name, case=False, na=False)]
    if row.empty:
        return {"error": f"Material '{material_name}' not found in Materials Project dataset"}

    r = row.sort_values("energy_above_hull").iloc[0]
    return {
        "material_id": str(r["material_id"]),
        "formula": str(r["formula"]),
        "common_name": str(r["common_name"]),
        "category": str(r["category"]),
        "formation_energy_per_atom_ev": float(r["formation_energy_per_atom"]) if pd.notna(r["formation_energy_per_atom"]) else None,
        "energy_above_hull_ev": float(r["energy_above_hull"]) if pd.notna(r["energy_above_hull"]) else None,
        "band_gap_ev": float(r["band_gap"]) if pd.notna(r["band_gap"]) else None,
        "is_stable": bool(r["is_stable"]),
        "density_g_cm3": float(r["density_g_cm3"]) if pd.notna(r["density_g_cm3"]) else None,
        "source": str(r["source"]),
    }


def find_substitutes(material_name: str, category: str) -> list[dict]:
    df = _load()
    candidates = df[df["category"].str.lower() == category.lower()].copy()
    # Exclude the original material
    candidates = candidates[~candidates["common_name"].str.lower().str.contains(
        material_name.lower(), na=False
    )]
    # Sort by energy above hull (lower = more stable = better candidate)
    candidates = candidates.sort_values("energy_above_hull").drop_duplicates("common_name")
    results = []
    for _, r in candidates.head(5).iterrows():
        results.append({
            "material_id": str(r["material_id"]),
            "formula": str(r["formula"]),
            "common_name": str(r["common_name"]),
            "category": str(r["category"]),
            "energy_above_hull_ev": float(r["energy_above_hull"]) if pd.notna(r["energy_above_hull"]) else None,
            "is_stable": bool(r["is_stable"]),
            "source": str(r["source"]),
        })
    return results


app = Server("materials-project")

TOOLS = [
    Tool(
        name="get_material_properties",
        description="Get Materials Project properties (formation energy, stability, band gap) for a battery material.",
        inputSchema={
            "type": "object",
            "properties": {
                "material_name": {"type": "string", "description": "Common name or formula e.g. 'LFP', 'LiFePO4'"}
            },
            "required": ["material_name"],
        },
    ),
    Tool(
        name="find_substitutes",
        description="Find top 5 substitute materials in the same category from Materials Project.",
        inputSchema={
            "type": "object",
            "properties": {
                "material_name": {"type": "string", "description": "Material to substitute"},
                "category": {"type": "string", "description": "Category: cathode, anode, or magnet"},
            },
            "required": ["material_name", "category"],
        },
    ),
]


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_material_properties":
        result = get_material_properties(arguments["material_name"])
    elif name == "find_substitutes":
        result = find_substitutes(arguments["material_name"], arguments["category"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
