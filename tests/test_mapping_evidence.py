"""Engineering tests of coverage and evidence preservation, not model accuracy."""
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem
from iam_sra.settings import CONCERNS
from test_confirmation import meaning








def test_multiple_passages_can_support_a_single_mapping_candidate(monkeypatch):
    import json
    from test_client import fake_client
    raw=meaning('O.p001',scores=('noise',),position='opposed')
    raw.concerns[0].excerpts=['O.p001','O.p002']
    raw.concerns[0].conditions=['O.p002'];raw.concerns[0].conditional_willingness='willing'
    responses=[{'finish_reason':'stop','message':{'content':json.dumps(raw.model_dump())}},
               {'finish_reason':'stop','message':{'content':json.dumps({'supported':True,'rationale':'Expressed disruption with conditional openness.'})}}]
    calls=fake_client(monkeypatch,responses)
    client=ConversationClient()
    evidence={key:EvidenceItem(id=key,text=text,context='original',source='citizen_original') for key,text in [('O.p001','The noise seriously disrupts my rest.'),('O.p002','I would accept if inaudible.') ]}
    result=client.interpret(evidence)
    assert result.concerns[0].excerpts==['O.p001','O.p002']
    schema=next(payload['guided_json'] for url,payload in calls if url.endswith('/v1/chat/completions'))
    assert 'items' in schema['$defs']['MappingConcern']['oneOf'][0]['properties']['excerpts']


def test_many_conditions_remain_per_concern_without_overflowing_global_summary():
    from iam_sra.interpretation import reconcile_original
    profile=meaning(scores=tuple(list(CONCERNS)[:7]),position='opposed')
    for index,c in enumerate(profile.concerns):
        c.conditions=[f'O.p{index+1:03d}'];c.conditional_willingness='willing'
    result,ledger=reconcile_original(None,profile,{})
    assert result.acceptance_conditions==[]
    assert len({r for c in result.concerns for r in c.conditions})==7
    assert len({r for f in ledger.values() for r in f.condition_ids})==7
