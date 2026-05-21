"""
MCP server wrapping USGS MCS 2025 supply concentration data.
Tools: get_supply_concentration, get_hhi_score
Run standalone: python -m mcp_servers.usgs_server
"""
import sys
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
        _df = pd.read_parquet(DATA_DIR / "usgs_mcs_2025.parquet")
    return _df


def get_supply_concentration(material_name: str) -> dict:
    df = _load()
    row = df[df["material"] == material_name.lower()]
    if row.empty:
        row = df[df["material"].str.contains(material_name.lower(), case=False, na=False)]
    if row.empty:
        return {"error": f"Material '{material_name}' not found", "source": "USGS MCS 2025"}
    r = row.iloc[0]
    shares = {}
    try:
        shares = eval(str(r.get("country_shares_json", "{}")))
    except Exception:
        pass
    events_raw = str(r.get("export_control_events", "") or "")
    events = [e.strip() for e in events_raw.split(";") if e.strip()]
    return {
        "material": str(r["material"]),
        "top_country": str(r["top_country"]),
        "top_country_pct": float(r["top_country_pct"]),
        "hhi_score": float(r["hhi_score"]),
        "feoc_flag": bool(r["feoc_flag"]),
        "country_shares": shares,
        "export_control_events": events,
        "source": str(r["source"]),
    }


def get_hhi_score(material_name: str) -> dict:
    result = get_supply_concentration(material_name)
    if "error" in result:
        return result
    hhi = result["hhi_score"]
    risk = "HIGH" if hhi >= 2500 else ("MEDIUM" if hhi >= 1500 else "LOW")
    return {
        "material": material_name,
        "hhi_score": hhi,
        "risk_level": risk,
        "feoc_flag": result["feoc_flag"],
        "source": result["source"],
    }


app = Server("usgs-mcs-2025")

TOOLS = [
    Tool(
        name="get_supply_concentration",
        description="Get country production shares, HHI score and FEOC flag for a battery material from USGS MCS 2025.",
        inputSchema={
            "type": "object",
            "properties": {
                "material_name": {"type": "string", "description": "Material name e.g. 'cobalt', 'graphite'"}
            },
            "required": ["material_name"],
        },
    ),
    Tool(
        name="get_hhi_score",
        description="Get HHI concentration score and risk level (HIGH/MEDIUM/LOW) for a material.",
        inputSchema={
            "type": "object",
            "properties": {
                "material_name": {"type": "string", "description": "Material name"}
            },
            "required": ["material_name"],
        },
    ),
]


@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_supply_concentration":
        result = get_supply_concentration(arguments["material_name"])
    elif name == "get_hhi_score":
        result = get_hhi_score(arguments["material_name"])
    else:
        result = {"error": f"Unknown tool: {name}"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
