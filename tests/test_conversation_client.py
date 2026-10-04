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
