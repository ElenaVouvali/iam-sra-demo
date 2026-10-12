"""Shared strict model base and reviewed thematic identifiers."""
from typing import Literal


from pydantic import BaseModel, ConfigDict, Field, model_validator


ConcernID = Literal["public_awareness_trust", "competence_building", "perceived_safety_privacy", "technical_safety_security_privacy", "noise", "visual_pollution", "wind_downwash", "airspace_capacity", "sump_integration", "infrastructure_land_use", "energy_emissions", "cost_roi_business", "accessibility", "multimodality_congestion", "welfare_equity"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
