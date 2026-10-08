import json
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem,freeze
from test_client import fake_client
from test_confirmation import meaning


def reply(score):
    return {'finish_reason':'stop','message':{'content':json.dumps({'score':score,
        'evidence_ids':['O.p001'],'endorsement_evidence_ids':[], 'rationale':'Synthetic model position conflict.'})}}


def test_confirmed_opposition_cannot_become_positive_after_retry(monkeypatch):
    fake_client(monkeypatch,[reply(8),reply(8)])
    client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I reject the hum.',context='original',source='citizen_original')}
    result=client.score(freeze(meaning(position='opposed'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score is None
    assert client.last_score_decisions[0]['score'] is None
    assert 'conflicts' in client.last_score_decisions[0]['reason']
    assert sum(d.get('failure')=='position_conflict' for d in client.last_diagnostics)==2


def test_model_can_correct_contradiction_using_its_own_number(monkeypatch):
    fake_client(monkeypatch,[reply(8),reply(3)])
    client=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The hum seriously disrupts my rest.',context='original',source='citizen_original')}
    result=client.score(freeze(meaning(position='opposed'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==3
    assert client.last_score_decisions[0]['origin']=='llm_assigned_score'
