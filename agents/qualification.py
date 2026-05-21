"""
QualificationPlanner — ADK tool that returns a testing roadmap for material substitutions.
Uses hardcoded templates per substitution type (cathode / anode / magnet swap).
"""
from google.adk.tools import FunctionTool
from schemas.models import QualificationStep

# Roadmap templates: (step_name, standard, duration_weeks, cost_low_usd, cost_high_usd, description)
ROADMAPS = {
    "cathode": [
        (
            "Cell-level characterisation",
            "IEC 62660-1",
            10,
            75_000, 150_000,
            "Electrochemical performance: capacity, rate capability, cycle life baseline at cell level.",
        ),
        (
            "Safety & abuse testing (cell)",
            "UN 38.3",
            6,
            25_000, 50_000,
            "UN 38.3 transport certification: altitude, thermal, vibration, shock, external short, overcharge, forced discharge.",
        ),
        (
            "Module-level validation",
            "IEC 62660-2",
            12,
            150_000, 300_000,
            "Module thermal management, cell balancing, BMS compatibility with new chemistry.",
        ),
        (
            "Pack-level safety validation",
            "UL 2580",
            16,
            300_000, 600_000,
            "Full pack abuse testing: thermal propagation, crush, immersion, fire resistance per UL 2580.",
        ),
        (
            "Vehicle integration & field trial",
            "ISO 26262 / OEM spec",
            20,
            200_000, 400_000,
            "OEM integration testing: range, charge time, thermal performance across climate zones. 50k-mile durability trial.",
        ),
        (
            "Regulatory certification",
            "ECE R100 / FMVSS 305",
            8,
            100_000, 200_000,
            "Homologation for target markets: ECE R100 (EU), FMVSS 305 (US). May run in parallel with field trial.",
        ),
        (
            "Production process validation",
            "IATF 16949",
            8,
            75_000, 150_000,
            "Validate electrode coating, formation cycling, and end-of-line testing at production volumes.",
        ),
    ],
    "anode": [
        (
            "Cell-level electrochemical characterisation",
            "IEC 62660-1",
            8,
            60_000, 120_000,
            "Capacity, first-cycle efficiency, rate capability, and cycle life for new anode chemistry.",
        ),
        (
            "Safety & abuse testing (cell)",
            "UN 38.3",
            6,
            25_000, 50_000,
            "UN 38.3 transport certification with new anode material.",
        ),
        (
            "Silicon expansion management validation",
            "Internal / OEM spec",
            10,
            100_000, 200_000,
            "Si-blend specific: validate mechanical integrity under volumetric expansion (up to 300% for pure Si).",
        ),
        (
            "Module thermal & BMS validation",
            "IEC 62660-2",
            12,
            150_000, 300_000,
            "BMS SOC algorithm recalibration for new anode voltage profile.",
        ),
        (
            "Pack-level safety validation",
            "UL 2580",
            14,
            250_000, 500_000,
            "Full pack abuse and safety testing.",
        ),
        (
            "Vehicle integration & regulatory certification",
            "ECE R100 / FMVSS 305",
            24,
            300_000, 600_000,
            "Combined OEM field trial and homologation.",
        ),
    ],
    "magnet": [
        (
            "Magnetic property characterisation",
            "IEC 60404-5",
            4,
            20_000, 50_000,
            "Measure Br, Hc, BHmax of substitute magnet vs NdFeB baseline.",
        ),
        (
            "Motor performance simulation",
            "IEC 60034-1",
            6,
            50_000, 100_000,
            "FEA simulation of motor efficiency, torque, and demagnetisation risk at operating temperatures.",
        ),
        (
            "Thermal stability & demagnetisation testing",
            "IEC 60404-8-1",
            8,
            75_000, 150_000,
            "Validate magnet performance from -40°C to +180°C. Critical for ferrite substitutes at high temp.",
        ),
        (
            "Motor prototype build & dyno testing",
            "ISO 19453-6",
            16,
            200_000, 400_000,
            "Build prototype motor with substitute magnet. Full dynamometer test: power, efficiency, NVH.",
        ),
        (
            "Vehicle integration & drive cycle validation",
            "OEM / WLTP spec",
            20,
            200_000, 500_000,
            "Full vehicle drive cycle: range impact, regenerative braking efficiency, thermal management.",
        ),
        (
            "Supplier qualification & production ramp",
            "IATF 16949",
            10,
            100_000, 200_000,
            "Qualify new magnet supplier, validate sintering process, incoming QC procedures.",
        ),
    ],
}


def plan_qualification(original_material: str, substitute_material: str, category: str) -> list[dict]:
    """
    Return an ordered qualification roadmap for substituting one material with another.

    Args:
        original_material: Name of the material being replaced (e.g. 'cobalt', 'neodymium')
        substitute_material: Name of the replacement material (e.g. 'LFP', 'barium ferrite')
        category: Material category — 'cathode', 'anode', or 'magnet'
    """
    template = ROADMAPS.get(category.lower(), ROADMAPS["cathode"])
    steps = []
    for name, standard, weeks, cost_low, cost_high, description in template:
        step = QualificationStep(
            step_name=name,
            standard=standard,
            duration_weeks=weeks,
            cost_band_usd_low=cost_low,
            cost_band_usd_high=cost_high,
        )
        d = step.model_dump()
        d["description"] = description
        d["source"] = f"Industry standard: {standard}"
        steps.append(d)
    return steps


def get_qualification_summary(original_material: str, substitute_material: str, category: str) -> dict:
    """
    Return a summary of the qualification roadmap: total weeks, total cost range, number of steps.

    Args:
        original_material: Material being replaced
        substitute_material: Replacement material
        category: Material category — 'cathode', 'anode', or 'magnet'
    """
    steps = plan_qualification(original_material, substitute_material, category)
    total_weeks = sum(s["duration_weeks"] for s in steps)
    total_low = sum(s["cost_band_usd_low"] for s in steps)
    total_high = sum(s["cost_band_usd_high"] for s in steps)
    return {
        "original_material": original_material,
        "substitute_material": substitute_material,
        "total_steps": len(steps),
        "total_weeks": total_weeks,
        "total_months": round(total_weeks / 4.3, 1),
        "total_cost_usd_low": total_low,
        "total_cost_usd_high": total_high,
        "source": "Industry standards: UN 38.3, IEC 62660, UL 2580, IATF 16949",
    }


# ADK tool wrappers
qualification_tool = FunctionTool(plan_qualification)
qualification_summary_tool = FunctionTool(get_qualification_summary)
