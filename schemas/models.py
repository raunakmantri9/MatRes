from typing import Literal, Optional
from pydantic import BaseModel, Field


class Material(BaseModel):
    name: str
    cas_number: Optional[str] = None
    category: Literal["cathode", "anode", "magnet", "electrolyte"]


class SupplyConcentration(BaseModel):
    material_name: str
    top_country: str
    top_country_pct: float = Field(ge=0.0, le=100.0)
    hhi_score: float = Field(ge=0.0, le=10000.0)
    feoc_flag: bool
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    export_control_events: list[str] = Field(default_factory=list)
    source: str


class FailureMode(BaseModel):
    material_name: str
    mode_description: str
    source_url: str
    recall_count: int = Field(ge=0)
    severity: int = Field(ge=1, le=5)
    nhtsa_recall_ids: list[str] = Field(default_factory=list)
    source: str


class SubstitutionCandidate(BaseModel):
    original_material: str
    substitute_name: str
    property_delta: dict[str, str | float]
    supply_risk_score: float = Field(ge=0.0, le=100.0)
    co2_delta_pct: float
    ranked_position: Literal[1, 2, 3]
    source: str
    composite_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class QualificationStep(BaseModel):
    step_name: str
    standard: str
    duration_weeks: int = Field(ge=1)
    cost_band_usd_low: int = Field(ge=0)
    cost_band_usd_high: int = Field(ge=0)


class BOMComponent(BaseModel):
    component_name: str
    material_name: str
    quantity_kg: float = Field(gt=0)
    supplier_country: str
    notes: Optional[str] = None


class RiskReport(BaseModel):
    bom_name: str
    components: list[BOMComponent]
    supply_risks: list[SupplyConcentration]
    failure_modes: list[FailureMode]
    substitutions: list[SubstitutionCandidate]
    qualification_roadmap: list[QualificationStep]
    composite_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
