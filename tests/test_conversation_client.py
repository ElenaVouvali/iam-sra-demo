import json
import pytest
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem, freeze
from iam_sra.assessment import AssessmentError
from test_client import fake_client, mapping_choice
from test_confirmation import meaning


def test_live_client_interpret_only_does_mapping(monkeypatch):
    choice=mapping_choice({'noise':3})
    d=json.loads(choice['message']['content']);d['concerns'][0]['excerpts']=['O.p001']
    for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']:d[name]['excerpts']=['O.p001']
    choice['message']['content']=json.dumps(d)
    scope={'finish_reason':'stop','message':{'content':json.dumps({'supported':True,'rationale':'Acoustic topic supported.'})}}
    calls=fake_client(monkeypatch,[choice,scope])
    client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The noise bothers me.',context='original',source='citizen_original')}
    result=client.interpret(evidence)
    assert len(calls)==4 and len(client.last_diagnostics)==2
    assert all(d['stage'] in {'mapping','scope_review'} for d in client.last_diagnostics)
    assert 'score' not in result.model_dump_json()
    assert 'concern_scores' not in calls[-1][1]['guided_json']['properties']


def test_numeric_api_has_no_remapping_fields_and_uses_confirmed_evidence(monkeypatch):
    choice={'finish_reason':'stop','message':{'content':json.dumps({'score':3,'rationale':'Strong noise objection.'})}}
    calls=fake_client(monkeypatch,[choice])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The noise bothers me.',context='original',source='citizen_original')}
    record=freeze(meaning(),evidence,1,'original','Original proposal')
    result=ConversationClient().score(record)
    assert result.concerns[0].score==3
    payload=calls[-1][1]
    assert set(payload['guided_json']['properties'])=={'score','rationale'}
    request=json.loads(payload['messages'][1]['content'])
    assert request['confirmed_meaning']==record['meaning']['concerns'][0]
    assert request['citizen_evidence'][0]['text']=='The noise bothers me.'
    assert request['original_testimony_history'][0]['text']=='The noise bothers me.'


def test_scorer_attempt_to_remap_rejected(monkeypatch):
    bad={'finish_reason':'stop','message':{'content':json.dumps({'score':9,'rationale':'Supported','position':'supported'})}}
    calls=fake_client(monkeypatch,[bad,bad])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The noise bothers me.',context='original',source='citizen_original')}
    with pytest.raises(AssessmentError):ConversationClient().score(freeze(meaning(),evidence,1,'original','Original proposal'))
    assert len(calls)==4


def test_ambiguous_confirmed_meaning_never_scored(monkeypatch):
    calls=fake_client(monkeypatch,[])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I am unsure.',context='original',source='citizen_original')}
    result=ConversationClient().score(freeze(meaning(position='uncertain'),evidence,1,'original','Original proposal'))
    assert calls==[] and all(c.score is None for c in result.concerns)


def test_original_history_is_concern_specific_and_preserves_superseded_evidence(monkeypatch):
    choice={'finish_reason':'stop','message':{'content':json.dumps({'score':8,'rationale':'Confirmed acoustic acceptance.'})}}
    calls=fake_client(monkeypatch,[choice])
    evidence={key:EvidenceItem(id=key,text=text,context='original',source=source) for key,text,source in [
        ('O.p001','The original hum bothered me.','citizen_original'),
        ('O.p002','I support hospital deliveries.','citizen_original'),
        ('C1.testimony','I now accept the original hum.','citizen_correction')]}
    record=freeze(meaning(eid='C1.testimony',position='supported'),evidence,2,'original','Original proposal',supporting_history={'noise':['O.p001']})
    ConversationClient().score(record)
    request=json.loads(calls[-1][1]['messages'][1]['content'])
    assert [item['id'] for item in request['original_testimony_history']]==['O.p001']
    assert request['citizen_evidence'][0]['id']=='C1.testimony'


def test_score_free_discovery_metadata_schema_and_exact_unmapped_wording(monkeypatch):
    raw={'no_reservations':False,'no_reservations_evidence':[],'blockers':[], 'unmapped_issues':['my pet collection']}
    choice={'finish_reason':'stop','message':{'content':json.dumps(raw)}}
    calls=fake_client(monkeypatch,[choice])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='What happens to my pet collection?',context='original',source='citizen_original')}
    client=ConversationClient();facts=client.discovery_facts(evidence)
    assert facts.unmapped_issues==['my pet collection']
    assert set(calls[-1][1]['guided_json']['properties'])=={'reasons_explicit','reasons_evidence','no_reservations','no_reservations_evidence','blockers','unmapped_issues'}
    assert client.last_raw_scores=={} and client.last_diagnostics[0]['stage']=='discovery'


def test_discovery_metadata_rejects_invented_issues_and_unknown_references(monkeypatch):
    raw={'no_reservations':True,'no_reservations_evidence':['unknown'],'blockers':[], 'unmapped_issues':['invented neighborhood']}
    choice={'finish_reason':'stop','message':{'content':json.dumps(raw)}}
    fake_client(monkeypatch,[choice,choice])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I accept.',context='original',source='citizen_original')}
    with pytest.raises(AssessmentError):ConversationClient().discovery_facts(evidence)


def test_generic_approval_cannot_establish_factual_awareness_after_review(monkeypatch):
    choice=mapping_choice({})
    d=json.loads(choice['message']['content'])
    for name in ['awareness_understanding','medical_public_benefit_support','current_route_stance']:d[name]['excerpts']=['O.p001']
    d['awareness_understanding']['interpretation']='demonstrated'
    choice['message']['content']=json.dumps(d)
    rejected={'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'No concrete fact was stated.'})}}
    # Benefit nomination creates a welfare candidate in this historical fixture.
    accepted={'finish_reason':'stop','message':{'content':json.dumps({'supported':True,'rationale':'Explicit candidate.'})}}
    calls=fake_client(monkeypatch,[choice,rejected,accepted])
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I accept.',context='original',source='citizen_original')}
    result=ConversationClient().interpret(evidence)
    assert result.awareness_understanding.interpretation=='unassessed' and not result.awareness_understanding.excerpts
    assert all('score' not in call[1]['guided_json']['properties'] for call in calls if call[0].endswith('completions'))
