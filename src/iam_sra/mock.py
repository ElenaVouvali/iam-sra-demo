"""Explicit GPU-free plumbing fixture, not semantic inference."""
import json
from .assessment import parse_assessment

def assess(text):
    dimension={"interpretation":"uncertain","excerpts":[text],"rationale":"MOCK: fixed uncertain interpretation for UI/CI only."}
    return parse_assessment(json.dumps({"scenario_id":"urban_medical_corridor","concerns":[],"awareness_understanding":dimension,"medical_public_benefit_support":dimension,"current_route_stance":dimension,"acceptance_conditions":[]}),text)
