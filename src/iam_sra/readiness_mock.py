"""Explicit empty fixture for UI testing, never a semantic assessment."""
from .readiness import EvidenceExtraction, ProposalView

class MockReadinessClient:
    def extract_readiness(self, evidence, **kwargs):
        return EvidenceExtraction(acceptance=ProposalView(stance='not_stated', evidence_ids=[], concerns=[], conditions=[], topic_ids=[], policy_preferences=[]), records=[])
