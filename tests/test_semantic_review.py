"""Production-path evidence and strength contracts; not live-model accuracy tests."""
import json
import pytest
from iam_sra.semantic_review import endorsement
from iam_sra.interpretation import EvidenceItem
from iam_sra.assessment import AssessmentError
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import freeze
from test_client import fake_client
from test_ordinal_policy import meaning,reply


def test_strength_requires_verbatim_evidence():
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The hum is acceptable.',context='original',source='citizen_original')}
    class Client:
        def _request(self,http,stage,system,user,schema,validator):
            return validator(json.dumps({'classification':'ordinary_acceptance_or_support','evidence_id':'O.p001','quotation':'I fully endorse it.'}))
    with pytest.raises(AssessmentError,match='exact citizen quotation'):endorsement(Client(),None,'noise','acoustic_impact',evidence,['O.p001'])


@pytest.mark.parametrize('text,classification,score,quote',[
    ('The hum is acceptable.','ordinary_acceptance_or_support',8,'The hum is acceptable.'),
    ('The hum has my full, unreserved backing.','explicit_unqualified_endorsement',9,'full, unreserved backing'),
    ('I accept the hum, with regular reviews required.','reservation_or_requirement',7,'regular reviews required')])
def test_strength_is_reviewed_before_number_and_ordinary_support_stays_eight(monkeypatch,text,classification,score,quote):
    values=[reply({'classification':classification,'evidence_id':'O.p001','quotation':quote}),
        reply({'score':score,'evidence_ids':['O.p001'],'endorsement_evidence_ids':['O.p001'] if score==9 else [],'rationale':'Facet-specific model score.'})]
    calls=fake_client(monkeypatch,values)
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda n:{**previous(n),'contrastive_endorsement_review':True} if n=='prompts' else previous(n))
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    record=freeze(meaning(position='supported'),evidence,1,'original','Original proposal')
    c=ConversationClient();result=c.score(record)
    assert result.concerns[0].score==score
    assert len(calls)==4
    assert 'No score' in calls[1][1]['messages'][0]['content']
    if score!=9:assert 9 not in calls[3][1]['guided_json']['properties']['score']['enum']
    assert c.last_score_decisions[0]['highest_criterion_verified']==(score==9)




def test_unused_discovery_metadata_does_not_call_model(monkeypatch):
    calls=fake_client(monkeypatch,[])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda n:{**previous(n),'omit_automatic_discovery_metadata':True} if n=='prompts' else previous(n))
    c=ConversationClient();evidence={'O.p001':EvidenceItem(id='O.p001',text='I oppose the hum.',context='original',source='citizen_original')}
    facts=c.discovery_facts(evidence)
    assert not calls and not facts.blockers
