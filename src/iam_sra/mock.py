"""Explicit GPU-free conversation fixture; never a live-error fallback."""

class MockConversationClient:
    """Visibly labeled fixture. Never selected on a live error."""
    def interpret(self,evidence,context='original',proposal=None,target=None):
        from .schemas import MappingAssessment, MappingConcern
        refs=[k for k,v in evidence.items() if v.context==context and v.source!='question']
        d={'interpretation':'uncertain','excerpts':refs[:1],'rationale':'MOCK: fixed uncertain interpretation; no semantic evaluation.'}
        concerns=[]
        if target:
            from .settings import CONCERNS
            if target in CONCERNS:concerns=[MappingConcern(concern_id=target,status='needs_clarification',position='uncertain',facets=[CONCERNS[target]['facets'][0]],excerpts=refs[:1],rationale=d['rationale'])]
        return MappingAssessment(scenario_id='urban_medical_corridor',concerns=concerns,awareness_understanding={'interpretation':'unassessed','excerpts':[],'rationale':'MOCK: unknown understanding.'},
            medical_public_benefit_support={'interpretation':'unassessed','excerpts':[],'rationale':'MOCK: unknown medical position.'},current_route_stance=d,acceptance_conditions=[])
    def score(self,confirmed,only=None,unavailable=None):
        from .interpretation import verify
        from .schemas import Assessment, Concern
        from .settings import CONCERNS
        meaning,evidence=verify(confirmed)
        dims={name:{**getattr(meaning,name).model_dump(),'excerpts':[evidence[r].text for r in getattr(meaning,name).excerpts]} for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']}
        return Assessment(scenario_id=meaning.scenario_id,concerns=[Concern(concern_id=cid,status='unassessed',position='unassessed',score=None,excerpts=[],rationale='MOCK: no assessment.') for cid in CONCERNS],acceptance_conditions=[],**dims)
