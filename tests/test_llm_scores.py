"""LLM number provenance, including combined-profile reuse and audit."""
import json
import pytest
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem,freeze
from iam_sra.assessment import AssessmentError
from iam_sra.replay_checks import check_export
from test_conversation_client import fake_client
from test_confirmation import meaning,initially_scored
from test_evidence_repair import ContextFake,profile
from test_updates import answer_all


def reply(score,eid='O.p001'):
    return {'finish_reason':'stop','message':{'content':json.dumps({'score':score,'evidence_ids':[eid],'endorsement_evidence_ids':[],'rationale':'LLM-selected score from the confirmed evidence.'})}}


def test_model_number_is_preserved_without_python_anchor_substitution(monkeypatch):
    fake_client(monkeypatch,[reply(6)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I cautiously accept the hum.',context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='supported'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==6
    assert c.last_raw_scores=={'noise':6}
    assert c.last_score_decisions[0]['origin']=='llm_assigned_score'
    assert c.last_score_decisions[0]['model_assigned_score']==6


@pytest.mark.parametrize('score',[0,10,4.5,True])
def test_invalid_model_numbers_are_rejected(monkeypatch,score):
    fake_client(monkeypatch,[reply(score),reply(score)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I accept the hum.',context='original',source='citizen_original')}
    with pytest.raises(AssessmentError):c.score(freeze(meaning(position='supported'),evidence,1,'original','Original proposal'))


def test_initial_and_modified_numeric_scores_with_audited_reuse(monkeypatch):
    # Initial scores follow profile order; modified reviews are privacy then noise.
    fake_client(monkeypatch,[reply(3),reply(2),reply(8),{'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'Clear medical support, not unqualified endorsement.'})}},reply(8,'J1.background.q1.choice'),reply(8,'J1.background.q2.choice')])
    class DirectFake(ContextFake):
        def __init__(self):
            super().__init__(profile())
            self.numeric=ConversationClient()
        def score(self,*args,**kwargs):
            result=self.numeric.score(*args,**kwargs)
            for key in ['last_score_decisions','last_raw_scores','last_anchor_facts','last_settings','last_diagnostics','last_trace','last_metrics']:
                setattr(self,key,getattr(self.numeric,key))
            return result
    s,c=initially_scored(DirectFake())
    initial=s.initial
    assert initial['aggregate']['rounded']==4
    assert all(d['origin']=='llm_assigned_score' for d in initial['score_decisions'])
    s.begin_followups(True);answer_all(s,c)
    s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':'yes'}})
    s.continue_final(True,c)
    assert s.conditional['aggregate']['rounded']==8
    assert s.conditional['score_records']['welfare_equity']['origin']=='equivalent_meaning_reuse'
    checks=check_export(s.export(),initial)
    assert checks['structural_evidence_checks_passed'] and checks['rubric_checks_passed']


def test_disruption_boundary_guidance_reaches_numeric_request_without_substitution(monkeypatch):
    calls=fake_client(monkeypatch,[reply(3)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The constant hum will drive me crazy when relaxing in the evening. I would accept inaudible flights.',context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='opposed'),evidence,1,'original','Original proposal'))
    request=calls[-1][1]
    system=request['messages'][0]['content']
    assert 'Noise is not automatically a personal boundary' in system
    assert 'Score 2 requires a stronger personal intrusion/risk boundary' in system
    payload=json.loads(request['messages'][1]['content'])
    assert 'rest or daily life' in payload['rubric']['3']
    assert result.concerns[0].score==3 and c.last_score_decisions[0]['model_assigned_score']==3


@pytest.mark.parametrize('cid,facet,text',[
 ('welfare_equity','medical_public_benefit','I wholeheartedly endorse the lifesaving medical-delivery purpose of this service, without any reservations about that purpose.'),
 ('welfare_equity','medical_public_benefit','Moving urgent hospital supplies this way has my full and unreserved backing.'),
 ('competence_building','participation_skills','Teaching residents how to report problems has my wholehearted support; I have no reservations about those skills.'),
 ('welfare_equity','medical_public_benefit','The lifesaving medical purpose has my full, unreserved support. I oppose the noise over my home, but that does not qualify my endorsement of the medical purpose.'),
])
def test_overlooked_endorsement_receives_llm_reassessment(monkeypatch,cid,facet,text):
    reviewed={'finish_reason':'stop','message':{'content':json.dumps({'supported':True,'rationale':'Explicit unqualified endorsement of the specified aspect.'})}}
    highest={'finish_reason':'stop','message':{'content':json.dumps({'score':9,'evidence_ids':['O.p001'],'endorsement_evidence_ids':['O.p001'],'rationale':'Unqualified endorsement verified for this aspect.'})}}
    calls=fake_client(monkeypatch,[reply(8),reviewed,highest])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    record=freeze(meaning(position='supported',scores=(cid,),facets={cid:[facet]}),evidence,1,'original','Original proposal')
    result=c.score(record)
    decision=c.last_score_decisions[0]
    assert result.concerns[0].score==9
    assert decision['initial_model_score']==8 and decision['model_assigned_score']==9
    assert decision['endorsement_reassessed'] and decision['highest_criterion_verified']
    assert decision['endorsement_source_ids']==['O.p001']
    assert len(calls)==6
    review_input=json.loads(calls[3][1]['messages'][1]['content'])
    assert review_input['citizen_testimony'][0]['text']==text
    rescore_input=json.loads(calls[5][1]['messages'][1]['content'])
    assert rescore_input['independent_endorsement_review']['supported']
    from iam_sra.scoring import aggregate
    assert aggregate(result)['rounded']==9


@pytest.mark.parametrize('text',[
 'I support the medical purpose.',
 'I endorse the medical purpose only if its benefits are guaranteed first.',
 'Yes.',
])
def test_ordinary_or_qualified_support_is_not_promoted(monkeypatch,text):
    review={'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'Not explicit unqualified endorsement.'})}}
    calls=fake_client(monkeypatch,[reply(8),review])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='supported'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==8 and not c.last_score_decisions[0]['endorsement_reassessed']
    assert not c.last_score_decisions[0]['highest_criterion_verified'] and len(calls)==4


def test_unresolved_endorsement_strength_preserves_model_clear_acceptance_without_upgrade(monkeypatch):
    review={'finish_reason':'stop','message':{'content':json.dumps({'supported':True,'rationale':'Explicit unqualified endorsement.'})}}
    fake_client(monkeypatch,[reply(8),review,reply(8),reply(8)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='This aspect has my full unreserved backing.',context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='supported'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==8
    assert c.last_score_decisions[0]['initial_model_score']==8
    assert c.last_score_decisions[0]['model_assigned_score']==8
    assert c.last_score_decisions[0]['endorsement_disagreement']
    assert not c.last_score_decisions[0]['highest_criterion_verified']


@pytest.mark.parametrize('cid,facet,text,score',[
 ('perceived_safety_privacy','personal_privacy','No consent, safeguards or other modification could make private-space viewing acceptable to me.',1),
 ('noise','acoustic_impact','The hum itself is acceptable to me.',8),
 ('cost_roi_business','cost_financing','The financing arrangement is acceptable to me.',8),
 ('visual_pollution','aesthetic_clutter','I refuse the visual clutter under any mitigation or modification.',1),
])
def test_categorical_and_clear_acceptance_calibration_is_shared_across_concerns(monkeypatch,cid,facet,text,score):
    responses=[reply(score)]
    if score==8:
        responses.append({'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'Ordinary clear acceptance, not explicit endorsement.'})}})
    calls=fake_client(monkeypatch,responses)
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    record=freeze(meaning(position='supported' if score==8 else 'opposed',scores=(cid,),facets={cid:[facet]}),evidence,1,'original','Original proposal')
    result=c.score(record)
    request=calls[0][1]
    system=request['messages'][0]['content']
    assert 'categorical refusal of the specified aspect takes precedence' in system.lower()
    assert 'Score 6 needs actual evidence of caution' in system
    assert 'objections to OTHER aspects cannot supply missing caution' in system
    assert result.concerns[0].score==score
    assert c.last_score_decisions[0]['model_assigned_score']==score


def test_overstated_nine_is_reassessed_by_model_not_substituted(monkeypatch):
    initial={'finish_reason':'stop','message':{'content':json.dumps({'score':9,'evidence_ids':['O.p001'],'endorsement_evidence_ids':['O.p001'],'rationale':'Incorrectly treated ordinary support as endorsement.'})}}
    review={'finish_reason':'stop','message':{'content':json.dumps({'supported':False,'rationale':'Ordinary support lacks explicit unqualified endorsement.'})}}
    fake_client(monkeypatch,[initial,review,reply(8)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='I support the medical-delivery purpose.',context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='supported'),evidence,1,'original','Original proposal'))
    decision=c.last_score_decisions[0]
    assert result.concerns[0].score==8
    assert decision['initial_model_score']==9 and decision['model_assigned_score']==8
    assert decision['endorsement_reassessed'] and not decision['highest_criterion_verified']


def test_categorical_aspect_refusal_is_not_vetoed_by_alternative_proposal_willingness(monkeypatch):
    review={'finish_reason':'stop','message':{'content':json.dumps({'classification':'rejection','evidence_id':'O.p001','quotation':'No safeguard could make public financing acceptable; I would consider private financing.'})}}
    fake_client(monkeypatch,[review,reply(1)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    text='No safeguard could make public financing acceptable; I would consider private financing.'
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    m=meaning(position='opposed',scores=('cost_roi_business',),facets={'cost_roi_business':['cost_financing']})
    m.concerns[0].conditional_willingness='willing'
    result=c.score(freeze(m,evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==1
    assert c.last_score_decisions[0]['origin']=='llm_assigned_score'


def test_numeric_generation_schema_matches_confirmed_position_without_assigning_number(monkeypatch):
    from jsonschema import Draft202012Validator
    calls=fake_client(monkeypatch,[reply(3)])
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The noise seriously disrupts my rest.',context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='opposed'),evidence,1,'original','Original proposal'))
    schema=calls[-1][1]['guided_json']
    validator=Draft202012Validator(schema)
    permitted=json.loads(reply(3)['message']['content'])
    assert not list(validator.iter_errors(permitted))
    forbidden={**permitted,'score':8}
    assert list(validator.iter_errors(forbidden))
    assert schema['properties']['score']['enum']==[None,1,2,3,4,5]
    assert result.concerns[0].score==3


@pytest.mark.parametrize('cid,facet',[
    ('visual_pollution','aesthetic_clutter'),
    ('cost_roi_business','cost_financing'),
])
def test_established_rejection_cannot_be_silently_scored_null(monkeypatch,cid,facet):
    # Transport regression: the model still supplies the number; null triggers
    # the existing bounded retry, rather than silently dropping a known position.
    text='No modification would make this aspect acceptable to me.'
    review={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'rejection','evidence_id':'O.p001','quotation':text})}}
    calls=fake_client(monkeypatch,[review,reply(None),reply(1)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='opposed',scores=(cid,),facets={cid:[facet]}),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==1
    assert c.last_score_decisions[0]['model_assigned_score']==1
    assert calls[-1][1]['guided_json']['properties']['score']['enum']==[1,2,3,4,5]


def test_unclear_independent_review_still_allows_unavailable_score(monkeypatch):
    text='I cannot establish a position on this aspect.'
    review={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'insufficient_evidence','evidence_id':'O.p001','quotation':text})}}
    evaluability={'finish_reason':'stop','message':{'content':json.dumps({
        'supported':False,'evidence_id':'O.p001','quotation':text})}}
    calls=fake_client(monkeypatch,[review,reply(None),evaluability])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='opposed'),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score is None
    assert None in calls[-3][1]['guided_json']['properties']['score']['enum']
    assert not c.last_score_decisions[0]['evaluability_review']['supported']


@pytest.mark.parametrize('cid,facet',[
    ('competence_building','participation_skills'),
    ('airspace_capacity','airspace_traffic'),
])
def test_independently_confirmed_support_cannot_be_silently_discarded(monkeypatch,cid,facet):
    text='I support this aspect.'
    review={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'ordinary_acceptance_or_support','evidence_id':'O.p001','quotation':text})}}
    calls=fake_client(monkeypatch,[review,reply(None),reply(8)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='supported',scores=(cid,),facets={cid:[facet]}),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==8
    assert c.last_score_decisions[0]['model_assigned_score']==8
    assert calls[-1][1]['guided_json']['properties']['score']['enum']==[6,7,8]


@pytest.mark.parametrize('position,score',[
    ('opposed',3),('opposed',4),('supported',7),('mixed',5),
])
def test_independently_confirmed_requirements_are_evaluable_without_forcing_number(monkeypatch,position,score):
    text='The citizen has expressed a requirement for this aspect.'
    review={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'reservation_or_requirement','evidence_id':'O.p001','quotation':text})}}
    calls=fake_client(monkeypatch,[review,reply(None),reply(score)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position=position),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==score
    assert c.last_score_decisions[0]['model_assigned_score']==score
    assert None not in calls[-1][1]['guided_json']['properties']['score']['enum']


def test_mixed_parent_keeps_separate_supported_and_prerequisite_facets(monkeypatch):
    cid='technical_safety_security_privacy'
    text='I accept mechanical reliability, but accept data access only after an access policy is added.'
    def review(kind):
        return {'finish_reason':'stop','message':{'content':json.dumps({
            'classification':kind,'evidence_id':'O.p001','quotation':text})}}
    calls=fake_client(monkeypatch,[review('ordinary_acceptance_or_support'),reply(8),
        review('reservation_or_requirement'),reply(4)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    facets=[]
    for facet,position,conditions in [('system_reliability','supported',[]),('data_security','opposed',['O.p001'])]:
        facets.append({'concern_id':cid,'facet':facet,'position':position,'evidence_ids':['O.p001'],
            'condition_ids':conditions,'conditional_willingness':'willing' if conditions else 'not_stated',
            'applicability_explicit':True,'rationale':'Separate citizen judgment.'})
    m=meaning(position='mixed',scores=(cid,),facets={cid:['system_reliability','data_security']})
    result=c.score(freeze(m,evidence,1,'original','Original proposal',facet_meanings=facets))
    assert result.concerns[0].score==4
    assert [d['model_assigned_score'] for d in c.last_score_decisions]==[8,4]
    payloads=[json.loads(body['messages'][1]['content']) for url,body in calls if url.endswith('/chat/completions') and 'confirmed_facet' in json.loads(body['messages'][1]['content'])]
    assert [p['confirmed_meaning']['position'] for p in payloads]==['supported','opposed']
    assert payloads[0]['confirmed_meaning']['conditions']==[]
    assert payloads[1]['confirmed_meaning']['conditions']==['O.p001']


@pytest.mark.parametrize('cid,facet,text,score',[
    ('cost_roi_business','cost_financing','I categorically reject public financing; no subsidy or benefit would make it acceptable.',1),
    ('visual_pollution','aesthetic_clutter','No change would make spoiling the sky acceptable to me.',1),
    ('energy_emissions','energy_demand','I would accept electricity demand only after a consumption ceiling is added.',4),
])
@pytest.mark.parametrize('missing_reason',['No endorsement evidence cited.','No acceptance evidence cited.'])
def test_null_due_to_strength_confusion_receives_independent_evaluability_recovery(monkeypatch,cid,facet,text,score,missing_reason):
    strength={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'insufficient_evidence','evidence_id':'O.p001','quotation':text})}}
    evaluability={'finish_reason':'stop','message':{'content':json.dumps({
        'supported':True,'evidence_id':'O.p001','quotation':text})}}
    missing=reply(None)
    data=json.loads(missing['message']['content']);data['rationale']=missing_reason
    missing['message']['content']=json.dumps(data)
    calls=fake_client(monkeypatch,[strength,missing,evaluability,reply(score)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    c=ConversationClient()
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    result=c.score(freeze(meaning(position='opposed',scores=(cid,),facets={cid:[facet]}),evidence,1,'original','Original proposal'))
    assert result.concerns[0].score==score
    decision=c.last_score_decisions[0]
    assert decision['initial_model_score'] is None
    assert decision['model_assigned_score']==score
    assert decision['evaluability_reassessed'] and decision['evaluability_review']['supported']
    assert decision['endorsement_source_ids']==[]
    recover=json.loads(calls[-1][1]['messages'][1]['content'])
    assert recover['independent_evaluability_review']['quotation']==text
    # The independent review receives testimony, never the scorer's conclusion.
    checked=json.loads(calls[-3][1]['messages'][1]['content'])
    assert 'score' not in checked and 'rationale' not in checked
    assert None not in calls[-1][1]['guided_json']['properties']['score']['enum']


def test_safety_null_recovery_preserves_later_acceptable_avoidance_condition(monkeypatch):
    fear='The possibility of a drone dropping onto my children is a risk I cannot live with.'
    remedy='Keep the aircraft away from our home; I could accept a route elsewhere.'
    strength={'finish_reason':'stop','message':{'content':json.dumps({
        'classification':'insufficient_evidence','evidence_id':'O.p001','quotation':fear})}}
    evaluability={'finish_reason':'stop','message':{'content':json.dumps({
        'supported':True,'evidence_id':'O.p001','quotation':fear})}}
    omitted=reply(None)
    data=json.loads(omitted['message']['content']);data['rationale']='Opposes the safety risk without accepting it.'
    omitted['message']['content']=json.dumps(data)
    calls=fake_client(monkeypatch,[strength,omitted,evaluability,reply(2)])
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    cid='perceived_safety_privacy';facet='perceived_safety'
    evidence={eid:EvidenceItem(id=eid,text=text,context='original',source='citizen_original')
        for eid,text in [('O.p001',fear),('O.p002',remedy)]}
    m=meaning(position='opposed',scores=(cid,),facets={cid:[facet]})
    m.concerns[0].conditions=['O.p002'];m.concerns[0].conditional_willingness='willing'
    ledger=[{'concern_id':cid,'facet':facet,'position':'opposed','evidence_ids':['O.p001'],
        'condition_ids':['O.p002'],'conditional_willingness':'willing','applicability_explicit':True,
        'rationale':'Injury boundary with an acceptable route elsewhere.'}]
    c=ConversationClient()
    result=c.score(freeze(m,evidence,1,'original','Original proposal',facet_meanings=ledger))
    assert result.concerns[0].score==2
    assert len(c.last_score_decisions)==1
    decision=c.last_score_decisions[0]
    assert decision['facet']=='perceived_safety' and decision['condition_ids']==['O.p002']
    assert decision['initial_model_score'] is None and decision['model_assigned_score']==2
    request=json.loads(calls[-1][1]['messages'][1]['content'])
    assert request['confirmed_facet']['conditional_willingness']=='willing'
    assert request['confirmed_meaning']['conditions']==['O.p002']
    assert {e['text'] for e in request['citizen_evidence']}=={fear,remedy}


@pytest.mark.parametrize('medical_score',[8,9])
def test_medical_endorsement_and_allocation_requirement_remain_separate(monkeypatch,medical_score):
    text='I wholeheartedly endorse the lifesaving medical purpose without reservations, but accept benefit distribution only after an equal allocation rule.'
    def strength(kind):
        return {'finish_reason':'stop','message':{'content':json.dumps({
            'classification':kind,'evidence_id':'O.p001','quotation':text})}}
    medical=reply(medical_score)
    if medical_score==9:
        raw=json.loads(medical['message']['content']);raw['endorsement_evidence_ids']=['O.p001']
        medical['message']['content']=json.dumps(raw)
    replies=[strength('explicit_unqualified_endorsement'),medical]
    if medical_score==8:replies.append(reply(8))
    replies.extend([strength('reservation_or_requirement'),reply(4)])
    fake_client(monkeypatch,replies)
    import iam_sra.conversation_client as module
    previous=module.config
    monkeypatch.setattr(module,'config',lambda name: {**previous(name),'contrastive_endorsement_review':True} if name=='prompts' else previous(name))
    cid='welfare_equity'
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}
    ledger=[{'concern_id':cid,'facet':facet,'position':position,'evidence_ids':['O.p001'],
        'condition_ids':conditions,'conditional_willingness':'willing' if conditions else 'not_stated',
        'applicability_explicit':True,'rationale':'Separate facet-specific position.'}
        for facet,position,conditions in [('medical_public_benefit','supported',[]),('distributive_equity','opposed',['O.p001'])]]
    c=ConversationClient()
    m=meaning(position='mixed',scores=(cid,),facets={cid:[f['facet'] for f in ledger]})
    result=c.score(freeze(m,evidence,1,'original','Original proposal',facet_meanings=ledger))
    assert result.concerns[0].score==4
    medical_decision,equity_decision=c.last_score_decisions
    assert medical_decision['model_assigned_score']==medical_score
    assert medical_decision['condition_ids']==[]
    assert medical_decision['endorsement_disagreement']==(medical_score==8)
    assert equity_decision['model_assigned_score']==4 and equity_decision['condition_ids']==['O.p001']
