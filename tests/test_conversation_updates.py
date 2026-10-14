"""Controlled regressions for GA selection, adapted wording and draft CRL evidence."""
from copy import deepcopy
import json
import pytest
from iam_sra.settings import config
from iam_sra.assessment import AssessmentError
from iam_sra.conversation_sources import grant_scenarios,scenario_explanations
from iam_sra.conversation_corpus import retrieve_scenarios,explanation_collection
from iam_sra.conversation_planner import PlannerClient,choose,validate_plan,ReviewedPlan
from iam_sra.citizen_score import empty_assessment,validate_citizen_score,assign_citizen
from test_conversation import collection,new,reach_offer,BANK
from iam_sra.conversation_benchmark import FixtureClient,resolve


def ga_cards():
    """Authored miniature layout fixture; no claim to parse a missing original."""
    pages=['']*59
    pages[55]='Madrid Living Lab:\n• Route 1: Hospital A – Hospital B (900 m, 30 m AGL, 3-minute flight).\n'
    pages[56]='• Route 2: Hospital C – Village D (14.5 km, 70 m AGL, 10 minutes).\nInterventions:'
    pages[57]='Milan Living Lab:\n • San Raffaele – Villa Turro: 3 km, planned test.\n • San Raffaele – Istituto Galeazzi: 14 km, proposed test.\n Authorisation pathways'
    pages[58]='Coimbra Living Lab:\n'+''.join(f' • Route {n}: Local pharmacy → Village {n} (~{n} km)\n' for n in range(1,5))
    return grant_scenarios('\f'.join(pages),config('baseline'),lambda doc,loc:{'document':doc,'locator':loc,'sha256':'test','version':'test','source_status':'contract'})


def expanded():
    c=collection();cards=ga_cards();c['scenarios']+=cards;c['explanations']+=scenario_explanations(cards)
    return c


def test_ga_route_inventory_and_source_status_are_preserved():
    cards=ga_cards()
    assert len(cards)==8 and {c['city'] for c in cards}=={'madrid','milan','coimbra'}
    assert '900 m, 30 m AGL' in cards[0]['text']
    assert '14.5 km, 70 m AGL' in cards[1]['text']
    assert cards[-1]['source']['locator']=='PDF p.59; Part B p.22'
    assert all(c['facts']['current_operational_status']=='not_verified' for c in cards)


def test_city_ranking_and_explanations_do_not_leak_fn_operating_facts():
    s=new(BANK['cases'][1]);c=expanded()
    ranked=retrieve_scenarios(c,s.respondent,s.profile())
    assert ranked[0]['city']=='milan'
    explanations=explanation_collection(c,ranked[0]['id'])
    assert not any(p['document_title']=='SRA_LLM_FN_concept.pdf' for p in explanations['passages'])
    assert any(p['document_title']=='GA.pdf' for p in explanations['passages'])
    assert all(p['scenario_applicability']==ranked[0]['id'] for p in explanations['passages'])


@pytest.mark.parametrize('scenario_id',['urban_medical_corridor']+[c['id'] for c in ga_cards()])
def test_each_source_case_completes_without_losing_context(scenario_id):
    from iam_sra.conversation_session import ConversationSession
    case=BANK['cases'][1];s=ConversationSession(expanded())
    s.set_context('personal','researcher','milan');client=reach_offer(s,case)
    baseline=deepcopy(s.baseline_snapshot);s.select_scenario(scenario_id)
    assert not s.information_exposures
    s.accept_scenario()
    assert s.information_exposures[-1]['source_ids']==[scenario_id]
    with pytest.raises(ValueError):s.select_scenario('urban_medical_corridor')
    while s.scenario.state=='interview':
        _,a,_=resolve(case,s.current_question);s.answer(a['text'],client)
        if s.pending:s.confirm_answer(actor='automation')
    s.confirm_final(actor='automation');data=s.export()
    assert data['state']=='final' and data['selected_scenario']['id']==scenario_id
    assert s.baseline_snapshot==baseline
    assert all(c['scenario_id']==scenario_id for c in data['scenario']['current_profile']['claims'])
    assert data['numerical_crl'] is None


def planned(monkeypatch,approved=True):
    s=new();s.answer('little',None);client=PlannerClient();calls=[]
    def request(self,http,stage,system,user,schema,validator):
        from iam_sra.privacy import require_safe_data
        require_safe_data({'system':system,'user':user,'schema':schema})
        calls.append(stage)
        if stage=='conversation_planner':
            c=user['candidates'][-1]
            wire={'objective_id':c['objective_id'],
                'proposed_question':'Thinking about what you have told us, '+c['allowed_wording_examples'][0][0].lower()+c['allowed_wording_examples'][0][1:],
                'strategy':'clarify'}
        else:wire={'preserves_criterion':approved,'neutral_without_answer_cues':True,
            'grounded_in_supplied_context':True,'preserves_actor_and_uncertainty':True,'reason':'Controlled review.'}
        return validator(json.dumps(wire))
    monkeypatch.setattr(PlannerClient,'_request',request)
    s._plan(client)
    return s,calls


def test_model_can_change_sequence_and_wording_after_review(monkeypatch):
    s,calls=planned(monkeypatch)
    assert calls==['conversation_planner','conversation_question_review']
    assert s.plans[-1]['method']=='model_adapted_retrieved_item',s.plans[-1]['privacy_findings']
    assert s.current_question['question_text'].startswith('Thinking about what you have told us, ')
    assert s.plans[-1]['candidate_id']!=s.plans[-1]['retrieved_candidates'][0]['id']
    assert s.plans[-1]['original_item']!=s.current_question['question_text']
    assert s.plans[-1]['wording_review']['preserves_criterion']


def test_failed_meaning_review_uses_authored_fallback(monkeypatch):
    s,calls=planned(monkeypatch,False)
    assert s.plans[-1]['method']=='deterministic_fallback'
    assert not s.current_question['question_text'].startswith('Thinking about what you have told us, ')


def payload(kind='explained_impact',**overrides):
    claim={'claim_id':'C1','evidence_id':'B1_1.p001','event_id':'B1_1','kind':kind,'dimension':'understanding',
        'span_quote':'I understand that repeated flights could interrupt rest.','subject':'respondent',
        'status':'supported','ambiguities':[],'domain':'IAM','temporality':'not_applicable',
        'information_context':'before_information','outcome_relation':'unknown',**overrides}
    return {'rubric':config('readiness_levels'),'profile':{'claims':[claim]},
        'answers':[{'id':'B1_1','context':'general_baseline','information_context':'before_information'}]}


def assessment(level=3):
    value=empty_assessment('The selected draft anchor is supported by the stated evidence.')
    value.update(crl=level,evidence_ids=['B1_1'])
    value['criteria'][level-1].update(status='supported',evidence_ids=['C1'],reason='Controlled anchor assessment.')
    return value


@pytest.mark.parametrize('level,claims',[
    (3,{'kind':'recognition'}),
    (2,{'kind':'learning_exposure','temporality':'actual','domain':'transferable'}),
    (4,{'kind':'learning_exposure','temporality':'actual'}),
    (5,{'kind':'intention','temporality':'intention'}),
    (7,{'kind':'influence','temporality':'actual','outcome_relation':'unknown'}),
    (7,{'kind':'influence','temporality':'actual','outcome_relation':'reported_link','domain':'transferable'}),
    (8,{'kind':'contribution','temporality':'actual','subject':'organisation'}),
    (9,{'kind':'contribution','temporality':'actual','ambiguities':['activity']}),
])
def test_inadmissible_evidence_cannot_become_a_positive_anchor(level,claims):
    with pytest.raises(ValueError):validate_citizen_score(assessment(level),payload(**claims))


def test_anchor_assessment_requires_full_inventory_and_matching_answer_citations():
    assert validate_citizen_score(assessment(),payload()).crl==3
    value=assessment();value['criteria'][-1]['level']=8
    with pytest.raises(ValueError):validate_citizen_score(value,payload())
    value=assessment();value['evidence_ids']=[]
    with pytest.raises(ValueError):validate_citizen_score(value,payload())
    assert validate_citizen_score(empty_assessment('Insufficient evidence.'),payload()).crl is None


def test_distinct_claims_from_one_passage_keep_separate_anchor_references():
    data=payload(kind='contribution',temporality='actual')
    data['profile']['claims'].append({**data['profile']['claims'][0],'claim_id':'C2',
        'kind':'influence','outcome_relation':'reported_link'})
    value=assessment(7);value['criteria'][6]['evidence_ids']=['C2']
    assert validate_citizen_score(value,data).crl==7
    value['criteria'][6]['evidence_ids']=['C1']
    with pytest.raises(ValueError):validate_citizen_score(value,data)


def test_semantic_score_review_can_reject_structurally_valid_number(monkeypatch):
    from iam_sra.readiness_score import WorkbookScoreClient
    calls=[]
    def request(self,http,stage,system,user,schema,validator):
        calls.append(stage)
        wire=assessment() if stage=='citizen_anchor_assessment' else {
            'matches_workbook':False,'supported_by_own_evidence':True,
            'preserves_scope_and_uncertainty':True,'reason':'The full anchor is not established.'}
        return validator(json.dumps(wire))
    monkeypatch.setattr(WorkbookScoreClient,'_request',request)
    with pytest.raises(AssessmentError):assign_citizen(WorkbookScoreClient(),payload())
    assert calls==['citizen_anchor_assessment','citizen_anchor_review']


@pytest.mark.presidio_live
def test_real_detector_adapted_question_and_positive_anchor_envelopes(monkeypatch):
    """Installed detector, controlled positive model verdicts; not semantic validation."""
    pytest.importorskip('presidio_analyzer');pytest.importorskip('en_core_web_sm')
    s,calls=planned(monkeypatch)
    assert s.plans[-1]['method']=='model_adapted_retrieved_item',s.plans[-1]['privacy_findings']
    from iam_sra.readiness_score import WorkbookScoreClient
    from iam_sra.privacy import require_safe_data,PrivacyError
    def request(self,http,stage,system,user,schema,validator):
        try:require_safe_data({'system':system,'user':user,'schema':schema})
        except PrivacyError as exc:raise AssertionError(list(exc.findings)) from None
        wire=assessment() if stage=='citizen_anchor_assessment' else {'matches_workbook':True,
            'supported_by_own_evidence':True,'preserves_scope_and_uncertainty':True,'reason':'Controlled positive review.'}
        return validator(json.dumps(wire))
    monkeypatch.setattr(WorkbookScoreClient,'_request',request)
    client=WorkbookScoreClient();result=assign_citizen(client,payload())
    assert result.crl==3 and client.last_anchor_review['matches_workbook']
    with pytest.raises(PrivacyError):require_safe_data({'source_locator':'My PIN is 1846.'})
    with pytest.raises(PrivacyError):require_safe_data({'claim_id':'Alice Example'})
    require_safe_data({'claim_id':'C3','criteria':[{'evidence_ids':['C3']}]})
    require_safe_data({'settings':{'request_metrics':[{'request_id':'deadbeef-abcd-4abc-8def-abcdefabcdef'}]}})
    with pytest.raises(PrivacyError):require_safe_data({'request_id':'Alice Example'})
