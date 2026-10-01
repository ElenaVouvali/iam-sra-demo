from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .settings import CONCERNS
ConcernID = Literal["public_awareness_trust", "competence_building", "perceived_safety_privacy", "technical_safety_security_privacy", "noise", "visual_pollution", "wind_downwash", "airspace_capacity", "sump_integration", "infrastructure_land_use", "energy_emissions", "cost_roi_business", "accessibility", "multimodality_congestion", "welfare_equity"]
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
class Evidence(Strict):
    excerpts: list[str] = Field(max_length=3)
    rationale: str = Field(max_length=400)
class Concern(Evidence):
    concern_id: ConcernID
    position: Literal["supported", "opposed", "mixed", "uncertain", "unassessed"]
    status: Literal["assessed", "unassessed"]
    score: int | None = Field(ge=1, le=9)
    @model_validator(mode="after")
    def coherent(self):
        if self.status == "unassessed" and self.score is not None:
            raise ValueError("Unassessed requires null score")
        if self.status == "assessed" and (self.score is None or not self.excerpts):
            raise ValueError("Assessed requires score and evidence")
        if self.status == "unassessed" and self.position not in {"unassessed", "uncertain"}:
            raise ValueError("Unassessed concern requires unassessed position")
        if self.status == "assessed":
            valid = (self.position == "opposed" and self.score <= 4) or (self.position == "mixed" and self.score == 5) or (self.position == "supported" and self.score >= 6)
            if not valid: raise ValueError("Score contradicts concern-specific position anchors")
        return self
class Dimension(Evidence):
    interpretation: Literal["supported", "opposed", "mixed", "uncertain", "unassessed"]
    @model_validator(mode="after")
    def coherent(self):
        if (self.interpretation == "unassessed") != (len(self.excerpts) == 0):
            raise ValueError("Dimension interpretation requires evidence")
        return self
class Awareness(Dimension):
    interpretation: Literal["demonstrated", "uncertain", "unassessed"]
class Assessment(Strict):
    scenario_id: Literal["urban_medical_corridor"]
    concerns: list[Concern] = Field(max_length=15)
    awareness_understanding: Awareness
    medical_public_benefit_support: Dimension
    current_route_stance: Dimension
    acceptance_conditions: list[str] = Field(max_length=5)
    @model_validator(mode="after")
    def unique(self):
        ids = [c.concern_id for c in self.concerns]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate concern")
        return self
