"""Logic doubles and contrastive contracts; not live semantic validation."""
import json
from copy import deepcopy
import pytest
from iam_sra.conversation_client import ConversationClient
from iam_sra.interpretation import EvidenceItem
from iam_sra.discovery import Boundary,DiscoveryFacts
from iam_sra.scoring import aggregate
from iam_sra.schemas import Assessment,Concern
from iam_sra.session import Session
from iam_sra.reporting import citizen_summary,clarification_needs
from iam_sra.updates import facet_availability
from test_client import fake_client
from test_confirmation import meaning
from test_discovery import DiscoveryFake
from test_evidence_repair import ready,profile


def item(text):return {'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source='citizen_original')}


def replies(values):return [{'finish_reason':'stop','message':{'content':json.dumps(x)}} for x in values]


@pytest.mark.parametrize('text,kind,eligible',[
 ('But 60 meters is incredibly low.','altitude_only',False),
 ('Fifteen flights a day make that constant hum unbearable.','noise_or_visibility_only',False),
 ('How will helicopters and drones be kept apart in that crowded sky?','traffic_capacity_separation_coordination',True),
 ('There is not enough room for all these competing flights unless their movements are coordinated.','traffic_capacity_separation_coordination',True),
])
def test_airspace_contrastive_decision_controls_all_mapping_contexts(monkeypatch,text,kind,eligible):
    raw=meaning('O.p001',scores=('airspace_capacity',),facets={'airspace_capacity':['airspace_traffic']})
    raw.awareness_understanding.interpretation='unassessed'
    fake_client(monkeypatch,replies([raw.model_dump(),{'supported':True,'rationale':'Related aviation concept.'},{'kind':kind,'rationale':'Independent contrastive decision.'}]))
    c=ConversationClient();result=c.interpret(item(text))
    assert bool(result.concerns)==eligible
    assert c.last_candidate_projections[-1]['supported']==eligible
    assert c.last_candidate_projections[-1]['evidence_ids']==['O.p001']
    assert c.last_raw_scores=={}


@pytest.mark.parametrize('cid,facet,text,kind,eligible',[
 ('infrastructure_land_use','facility_siting','Route them over the industrial park.','flight_routing_only',False),
 ('infrastructure_land_use','land_allocation','Do not allocate our community garden to a landing pad.','facility_or_land_planning',True),
])
def test_infrastructure_scope_still_distinguishes_real_facilities(monkeypatch,cid,facet,text,kind,eligible):
    raw=meaning('O.p001',scores=(cid,),facets={cid:[facet]});raw.awareness_understanding.interpretation='unassessed'
    fake_client(monkeypatch,replies([raw.model_dump(),{'supported':True,'rationale':'Topic nominated.'},{'kind':kind,'rationale':'Separate facilities attribution.'}]))
    assert bool(ConversationClient().interpret(item(text)).concerns)==eligible


@pytest.mark.parametrize('decisive,status',[(True,'yes'),(False,'yes'),(True,'unsure')])
def test_boundary_topic_and_decisiveness_are_separate_reviews(monkeypatch,decisive,status):
    facts=DiscoveryFacts(blockers=[Boundary(concern_id='noise',status=status,excerpts=['O.p001'])])
    calls=fake_client(monkeypatch,replies([facts.model_dump(),{'supported':True,'rationale':'Explicit hum objection.'},{'supported':decisive,'rationale':'Independent position separately checked.'}]))
    c=ConversationClient();result=c.discovery_facts(item('Noise bothers me; I have not decided whether noise alone rules it out.'))
    b=result.blockers[0]
    assert b.validated_facets==['acoustic_impact'] and b.decisiveness_checked==decisive
    assert b.status==(status if decisive else 'unsure')
    assert len([url for url,_ in calls if url.endswith('/v1/chat/completions')])==3 and 'independent' in calls[-1][1]['messages'][0]['content']


def test_rejected_routing_boundary_stays_audit_only(monkeypatch):
    raw=DiscoveryFacts(blockers=[Boundary(concern_id='infrastructure_land_use',status='yes',excerpts=['O.p001'])])
    values=[raw.model_dump()]
    for facet in ['facility_siting','land_allocation']:
        values.extend([{'supported':True,'rationale':'False generic approval.'},{'kind':'flight_routing_only','rationale':'No facilities or land allocation.'}])
    fake_client(monkeypatch,replies(values));c=ConversationClient();facts=c.discovery_facts(item('Reroute over the industrial park or I oppose the route.'))
    assert facts.blockers==[]
    audit=c.last_candidate_projections[-1]
    assert audit['kind']=='boundary_review' and not audit['decisiveness_supported'] and audit['raw_nomination']['excerpts']==['O.p001']


def test_unvalidated_metadata_cannot_bypass_ledger_or_confirmation():
    facts=DiscoveryFacts(blockers=[Boundary(concern_id='infrastructure_land_use',status='yes',excerpts=['O.p001'])])
    c=DiscoveryFake(profile(),facts);s=Session();s.begin();s.submit('I support medical deliveries but oppose hum and private cameras.',c)
    assert not s.blockers and not s.discovery_topics
    s.finish_discovery();s.confirm(True)
    assert not s.blockers and not any('infrastructure' in line for line in citizen_summary(s)['lines'])
    assert s.boundary_nominations[0]['actionable'] is False


def test_supported_topic_without_independent_answer_gets_one_concrete_question():
    facts=DiscoveryFacts(blockers=[Boundary(concern_id='noise',status='unsure',excerpts=['O.p001'],validated_facets=['acoustic_impact'])])
    p=profile()
    for candidate in p.concerns:candidate.conditional_willingness='willing'
    c=DiscoveryFake(p,facts);s=Session();s.begin();s.submit('I object to hum, but may accept quieter flights.',c)
    q=s.discovery_question
    assert q['kind']=='blocker' and 'If the other issues were resolved' in q['text']
    before=s.draft.model_dump();s.respond_discovery(['unsure'],'',c)
    assert s.draft.model_dump()==before and s.blockers[q['concern_id']]['status']=='unsure'
    assert not s.discovery_question or s.discovery_question['selection_key']!=q['selection_key']


@pytest.mark.parametrize('response,available',[('yes',True),('unsure',False),('skip',False)])
def test_explicit_applicability_responses_control_modified_review(response,available):
    s,c=ready();initial=deepcopy(s.initial);key='welfare_equity:medical_public_benefit'
    s.record_joint('accept',[],'',c,{key:{'response':response}})
    f=next(f for f in s.facet_meanings if f.facet=='medical_public_benefit')
    assert facet_availability(s,f)==available
    assert all(facet_availability(s,f) for f in s.facet_meanings if f.facet in {'personal_privacy','acoustic_impact'})
    a=s.joint['applicability_confirmations'][0]
    assert a['response']==response and a['context']=='modified' and a['original_evidence_ids']
    assert 'Does that still apply' in a['displayed_statement']
    s.continue_final(True,c)
    assert s.initial==initial
    assert s.conditional['aggregate']['trace']['denominator']==(3 if available else 2)
    assert bool(clarification_needs(s))==(not available)
    s.rewind('combined_proposal')
    assert s.conditional is None and s.final is None and s.conditional_confirmed is None
    assert s.revision_history[-1]['joint']['applicability_confirmations'][0]['response']==response


def test_changed_applicability_requires_explanation_without_mutating_answers():
    s,c=ready();evidence=deepcopy(s.evidence)
    with pytest.raises(ValueError,match='changed'):
        s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':'changed'}})
    assert s.joint is None and s.evidence==evidence and s.conditional is None


def test_three_input_trace_not_just_the_rounded_headline():
    m=profile();concerns=[]
    for candidate,value in zip(m.concerns,[3,2,8]):
        data=candidate.model_dump();data.update(status='assessed',score=value)
        concerns.append(Concern.model_validate(data))
    data=m.model_dump();data['concerns']=concerns
    result=aggregate(Assessment.model_validate(data))
    assert result['trace']['mean_inputs']==[{'concern_id':'noise','score':3},{'concern_id':'perceived_safety_privacy','score':2},{'concern_id':'welfare_equity','score':8}]
    assert result['trace']['denominator']==3 and result['mean']==13/3
    assert result['cap']==4 and result['adjusted']==4 and result['rounded']==4


def test_ui_applicability_is_explicit_unselected_and_blocks_missing_answer(monkeypatch):
    from test_ui import fresh,click
    from test_evidence_repair import ContextFake
    from iam_sra.session import State
    app=fresh(monkeypatch,ContextFake(profile()));click(app)
    app.text_area(key='citizen_answer').set_value('I support medicine but oppose hum and cameras.');click(app)
    click(app,'Finish these questions');app.checkbox(key='confirm_1').check().run();click(app)
    while app.session_state.session.state==State.FOLLOWUPS:
        q=app.session_state.session.current_question
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
    key='applies_welfare_equity:medical_public_benefit'
    assert app.radio(key=key).value is None
    app.radio(key='joint_choice').set_value('accept');click(app)
    assert app.session_state.session.joint is None and app.radio(key='joint_choice').value=='accept'
    app.radio(key=key).set_value('yes');click(app)
    assert app.session_state.session.joint['unchanged_aspects_confirmed']==['welfare_equity:medical_public_benefit']


def test_confirming_mixed_unchanged_aspect_keeps_conditions_and_re_reviews():
    s,c=ready();key='welfare_equity:medical_public_benefit';f=s.original_facets[key]
    f.position='mixed';f.condition_ids=['O.p001'];f.rationale='Medical public benefit is supported with a stated condition.'
    s.record_joint('accept',[],'',c,{key:{'response':'yes'}})
    modified=next(x for x in s.facet_meanings if x.facet=='medical_public_benefit')
    assert modified.position=='mixed' and modified.condition_ids
    assert s.joint['applicability_confirmations'][0]['original_condition_ids']==['O.p001']
    assert 'Your conditions were:' in s.joint['applicability_confirmations'][0]['displayed_statement']
    s.continue_final(True,c)
    assert any(call[0]=='score' and call[1]=='modified' and call[2]['meaning']['concerns'][0]['position']=='mixed' for call in c.calls)


def test_boundary_for_missing_ledger_topic_is_clarification_not_actionable():
    facts=DiscoveryFacts(blockers=[Boundary(concern_id='infrastructure_land_use',status='yes',excerpts=['O.p001'],validated_facets=['facility_siting'],decisiveness_checked=True)])
    c=DiscoveryFake(profile(),facts);s=Session();s.begin();s.submit('I also reject the landing pad location.',c)
    assert not s.blockers and s.discovery_question['kind']=='topic'
    assert s.discovery_question['concern_id']=='infrastructure_land_use'
    assert s.boundary_nominations[0]['actionable'] is False


def test_concern_edit_invalidates_prior_independent_boundary():
    facts=DiscoveryFacts(blockers=[Boundary(concern_id='noise',status='yes',excerpts=['O.p001'],validated_facets=['acoustic_impact'],decisiveness_checked=True)])
    c=DiscoveryFake(profile(),facts);s=Session();s.begin();s.submit('Even if everything else were resolved, noise alone stops me.',c)
    assert s.blockers['noise']['status']=='yes'
    s.finish_discovery();s.confirm(True)
    c.next=meaning('C1.testimony',scores=('noise',),position='mixed')
    s.correct('noise','Some of the sound is acceptable; I have reservations about late evening.','Specific original correction',c)
    assert 'noise' not in s.blockers and s.confirmed is None
    assert any('invalidated_boundary' in entry for entry in s.boundary_nominations)


def test_metadata_schema_does_not_allow_model_to_self_certify(monkeypatch):
    calls=fake_client(monkeypatch,replies([DiscoveryFacts().model_dump()]))
    ConversationClient().discovery_facts(item('I am unsure.'))
    schema=calls[-1][1]['guided_json']
    assert 'decisiveness_checked' not in schema['$defs']['Boundary']['properties']
    assert 'validated_facets' not in schema['$defs']['Boundary']['properties']
    assert schema['properties']['unmapped_issues']['items']['enum']==['I am unsure.']


def test_report_fallback_names_original_and_specific_modified_gap():
    from iam_sra.reporting import final_summary
    s,c=ready();s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':'skip'}});s.continue_final(True,c)
    result=final_summary(s)
    assert result['selected_profile']=='final_original' and result['proposal_context']=='original'
    assert result['headline_score']==4 and result['modified_aggregate_available'] is False
    assert result['clarification_needs'][0]['facet']=='medical_public_benefit'
    assert citizen_summary(s)['remaining_objections']==[]


@pytest.mark.parametrize('kind,eligible',[('altitude_discomfort_only',False),('explicit_physical_risk',True)])
def test_altitude_not_automatically_remapped_to_physical_risk(monkeypatch,kind,eligible):
    raw=meaning('O.p001',scores=('perceived_safety_privacy',),facets={'perceived_safety_privacy':['perceived_safety']})
    raw.awareness_understanding.interpretation='unassessed'
    fake_client(monkeypatch,replies([raw.model_dump(),{'supported':True,'rationale':'Generic proximity inference.'},{'kind':kind,'rationale':'Physical risk meaning independently checked.'}]))
    assert bool(ConversationClient().interpret(item('The height makes me uneasy.')).concerns)==eligible


def test_unknown_modified_medical_facet_does_not_keep_an_invented_global_support():
    s,c=ready();s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':'unsure'}})
    assert s.conditional_draft.medical_public_benefit_support.interpretation=='uncertain'
    assert s.draft.medical_public_benefit_support.interpretation=='supported'


def test_mapping_generation_schema_mirrors_missing_position_invariant(monkeypatch):
    raw=meaning('O.p001',scores=());raw.awareness_understanding.interpretation='unassessed'
    calls=fake_client(monkeypatch,replies([raw.model_dump()]))
    ConversationClient().interpret(item('I am unsure.'))
    branches=calls[-1][1]['guided_json']['$defs']['MappingConcern']['oneOf']
    assert branches[0]['properties']['position']['enum']==['supported','opposed','mixed','uncertain']
    assert branches[1]['properties']['position']['const']=='unassessed'
    assert 'not_stated' not in branches[1]['properties']['conditional_willingness']['enum']


@pytest.mark.parametrize('cid,facet,kind,eligible',[
 ('perceived_safety_privacy','personal_privacy','altitude_only',False),
 ('perceived_safety_privacy','personal_privacy','private_viewing_or_personal_privacy',True),
 ('technical_safety_security_privacy','system_reliability','traffic_coordination_only',False),
 ('technical_safety_security_privacy','system_reliability','explicit_system_failure_or_engineered_safeguard',True),
])
def test_no_secondary_privacy_or_reliability_inference(monkeypatch,cid,facet,kind,eligible):
    raw=meaning('O.p001',scores=(cid,),facets={cid:[facet]});raw.awareness_understanding.interpretation='unassessed'
    fake_client(monkeypatch,replies([raw.model_dump(),{'supported':True,'rationale':'Overbroad generic scope acceptance.'},{'kind':kind,'rationale':'Actual facet meaning checked independently.'}]))
    assert bool(ConversationClient().interpret(item('Height or coordination alone does not specify another concern.')).concerns)==eligible
