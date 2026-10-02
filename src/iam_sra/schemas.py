from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .settings import CONCERNS
SCHEMA_VERSION = "3.5.0"
ConcernID = Literal["public_awareness_trust", "competence_building", "perceived_safety_privacy", "technical_safety_security_privacy", "noise", "visual_pollution", "wind_downwash", "airspace_capacity", "sump_integration", "infrastructure_land_use", "energy_emissions", "cost_roi_business", "accessibility", "multimodality_congestion", "welfare_equity"]
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
class Evidence(Strict):
    excerpts: list[str] = Field(max_length=3)
    rationale: str = Field(max_length=400)
class ConcernMapping(Evidence):
    concern_id: ConcernID
    position: Literal["supported", "opposed", "mixed", "uncertain", "unassessed"]
    status: Literal["assessed", "unassessed"]
    conditional_willingness: Literal["willing", "not_willing", "uncertain", "not_stated"] = "not_stated"
    conditions: list[str] = Field(default_factory=list, max_length=3)
    facets: list[str] = Field(default_factory=list, max_length=2)
    mapping_note: Literal["direct", "medical_benefit_not_equity", "distinct_shared_evidence", "ambiguous_needs_clarification", "not_mentioned"] = "direct"
    @model_validator(mode="after")
    def coherent(self):
        if any(f not in CONCERNS[self.concern_id]["facets"] for f in self.facets):
            raise ValueError("Facet outside canonical concern scope")
        if len(self.facets) != len(set(self.facets)):
            raise ValueError("Duplicate facet")
        if self.status == "assessed" and (not self.facets or not self.excerpts):
            raise ValueError("Assessed requires a concern facet and evidence")
        if self.status=="assessed" and self.conditions and self.conditional_willingness == "not_stated":
            raise ValueError("Conditions require explicit willingness interpretation")
        return self
class Concern(ConcernMapping):
    score: int | None = Field(ge=1, le=9)
    @model_validator(mode="after")
    def score_coherent(self):
        if self.status=="unassessed" and self.score is not None:
            raise ValueError("Unassessed requires null score")
        if self.status=="assessed" and self.score is None:
            raise ValueError("Assessed requires a score")
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


class MappingConcern(ConcernMapping):
    # Discovery eligibility is not an already measured readiness assessment.
    status: Literal["mapped","needs_clarification"]
    @model_validator(mode="after")
    def mapped_evidence(self):
        if self.status=="mapped" and (not self.facets or not self.excerpts):
            raise ValueError("Mapped concern requires a facet and evidence")
        return self

class MappingAssessment(Strict):
    scenario_id: Literal["urban_medical_corridor"]
    concerns: list[MappingConcern] = Field(max_length=15)
    awareness_understanding: Awareness
    medical_public_benefit_support: Dimension
    current_route_stance: Dimension
    acceptance_conditions: list[str] = Field(max_length=5)
    @model_validator(mode="after")
    def unique(self):
        ids=[c.concern_id for c in self.concerns]
        if len(ids)!=len(set(ids)):raise ValueError("Duplicate concern")
        return self

class ScoreDecision(Strict):
    concern_id: ConcernID
    scope_supported: bool = False
    position: Literal["supported","opposed","mixed","uncertain","unassessed"] = "unassessed"
    facets: list[str] = Field(default_factory=list,max_length=2)
    excerpts: list[str] = Field(default_factory=list,max_length=3)
    status: Literal["assessed","unassessed"]
    decision: Literal["retained","excluded","needs_clarification"]
    conditional_willingness: Literal["willing","not_willing","uncertain","not_stated"] = "not_stated"
    conditions: list[str] = Field(default_factory=list,max_length=3)
    score: int | None = Field(ge=1,le=9)
    rationale: str = Field(max_length=400)
    @model_validator(mode="after")
    def coherent(self):
        if any(f not in CONCERNS[self.concern_id]["facets"] for f in self.facets):raise ValueError("Facet outside concern scope")
        if self.status=="assessed" and (not self.facets or not self.excerpts):raise ValueError("Assessed review requires facet and evidence")
        if self.status=="assessed" and not self.scope_supported:raise ValueError("A score requires explicit semantic scope support")
        if (self.status=="assessed") != (self.score is not None):raise ValueError("Status and nullable score disagree")
        if (self.status=="assessed") != (self.decision=="retained"):raise ValueError("Decision and status disagree")
        return self

class ScoreBatch(Strict):
    concern_scores: list[ScoreDecision] = Field(max_length=15)
    @model_validator(mode="after")
    def unique(self):
        ids=[c.concern_id for c in self.concern_scores]
        if len(ids)!=len(set(ids)):raise ValueError("Duplicate score decision")
        return self
