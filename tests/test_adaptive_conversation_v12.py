import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from iam_sra.conversation_objectives import registry
from iam_sra.conversation_planner import PlannerActionV12,PlannerClient
from iam_sra.conversation_session import ConversationSession
from iam_sra.synthetic_respondent import load_personas,ScriptedRespondent
from iam_sra.synthetic_runner import synthetic_collection,run_evaluation
from iam_sra.baseline_client import MockBaselineClient
from iam_sra.settings import ROOT,config


def ready_session():
    s=ConversationSession(synthetic_collection())
    s.set_context('personal','citizen','madrid')
    s.answer('term',MockBaselineClient())
    return s


def test_v12_wire_contract_omits_controller_owned_metadata():
    fields=set(PlannerActionV12.model_fields)
    assert fields=={'objective_id','proposed_question','strategy'}


def test_v12_planner_selects_eligible_objective_and_adapts_question(monkeypatch):
    planner=PlannerClient();seen=[]
    shortlist=[{'id':'retrieved_concept_personal','objective_id':'general:concept',
        'question':{'dimension':'concept','target_requirement':'concept_definition','triggering_evidence_ids':[]},
        'allowed_wording':['In your own words, what is a drone?'],'topic_ids':[],
        'source':{'document':'synthetic-test'},'retrieval_score':0.5}]
    profile={'claims':[],'planning_context':{'recent_turns':[
        {'question':'Before today, how familiar were you with drones?','answer':'I had heard the term.',
         'confirmed_claims':[]} ]}}
    def request(self,http,stage,system,user,schema,validator):
        seen.append((stage,user,schema))
        if stage=='conversation_planner':
            c=user['candidates'][0]
            assert set(c).isdisjoint({'source_ids','triggering_evidence_ids'})
            raw={'objective_id':c['objective_id'],
                'proposed_question':'How would you describe a drone in everyday terms?',
                'strategy':'identify_information_need'}
        else:
            raw={'preserves_criterion':True,'neutral_without_answer_cues':True,
                'grounded_in_supplied_context':True,'preserves_actor_and_uncertainty':True,
                'reason':'Neutral, short question.'}
        return validator(json.dumps(raw))
    monkeypatch.setattr(PlannerClient,'_request',request)
    result=planner.plan('general',shortlist,profile)
    assert [x[0] for x in seen]==['conversation_planner','conversation_question_review']
    assert result.action.candidate_id=='retrieved_concept_personal'
    assert result.action.target_criterion=='concept'
    assert result.action.displayed_question=='How would you describe a drone in everyday terms?'


def test_v12_unknown_objective_is_rejected_without_invented_source_repair(monkeypatch):
    from iam_sra.assessment import AssessmentError
    planner=PlannerClient()
    shortlist=[{'id':'retrieved_concept_personal','objective_id':'general:concept',
        'question':{'dimension':'concept','target_requirement':'concept_definition','triggering_evidence_ids':[]},
        'allowed_wording':['In your own words, what is a drone?'],'topic_ids':[]}]
    def request(self,http,stage,system,user,schema,validator):
        return validator(json.dumps({'objective_id':'hallucinated:criterion',
            'proposed_question':'How would you describe a drone?', 'strategy':'clarify'}))
    monkeypatch.setattr(PlannerClient,'_request',request)
    with pytest.raises(AssessmentError) as error:planner.plan('general',shortlist,{'claims':[]})
    assert error.value.code=='invalid_candidate'


def test_registry_preserves_all_fifteen_topics_and_pending_status():
    value=registry()
    assert len(value['topics'])==15
    assert value['review_status']=='draft_pending_FN' and value['approved_by'] is None
    assert 'general:concept' in value['objectives']
    assert value['objectives']['general:concept']['eligibility_authority']=='existing baseline_routing policy'
    assert all('source_references' in row for row in value['objectives'].values())


def test_topic_memory_distinguishes_context_from_expressed_evidence():
    s=ready_session()
    s.general.events=[{'active':True,'confirmed':True,'control':'answer','interaction':'substantive',
        'question':{'topic_ids':['noise']},'claims':[]}]
    with patch.object(s,'profile',return_value={'claims':[]}):
        memory=s._topic_memory()
    assert memory[0]['topic_id']=='noise'
    assert memory[0]['question_or_scenario_topic'] is True
    assert memory[0]['respondent_expressed_topic'] is False
    claim={'topic_ids':['noise'],'status':'supported','evidence_id':'B1.p001',
        'span_quote':'The route may be noisy.','interpretation':'The respondent is concerned about noise.'}
    with patch.object(s,'profile',return_value={'claims':[claim]}):
        memory=s._topic_memory()
    assert memory[0]['respondent_expressed_topic'] is True
    assert memory[0]['quotations']==['The route may be noisy.']


def test_qualitative_evidence_profile_has_no_readiness_or_srl():
    s=ready_session();result=s.qualitative_assessment()
    assert result['readiness_level'] is None and result['overall_srl'] is None
    assert result['status']=='descriptive_evidence_only'
    assert all(row['external_verification']=='not_performed' for row in result['criteria'])


def test_persona_bank_is_synthetic_diverse_and_script_is_repeatable():
    bank=load_personas();assert len(bank['personas'])==19
    ids={p['persona_id'] for p in bank['personas']}
    assert {'madrid_drone_novice','milan_authority_costs','noise_researcher_external',
        'coimbra_privacy_noise','iam_contributor_unknown_influence','workshop_attendee'}<=ids
    persona=next(p for p in bank['personas'] if p['persona_id']=='madrid_drone_novice')
    q={'question_text':'What have you heard about drones carrying goods?'}
    assert ScriptedRespondent(persona,11).respond(q)==ScriptedRespondent(persona,11).respond(q)


def test_madrid_regression_fixture_is_reconstructed_and_has_claim_expectations():
    fixture=json.loads((ROOT/'eval/conversation_adaptive_regressions_v1.json').read_text())
    case=fixture['cases'][0]
    assert fixture['synthetic'] is True
    assert 'not the original complete export' in fixture['reconstruction_status']
    assert len(case['turns'])==11
    assert {x['id'] for x in case['expected_observations']} >= {'knowledge_absence','noise_concern','tentative_benefit','distributional_effect'}
    assert 'overall SRL' in case['prohibited_inferences']


def test_offline_synthetic_agent_runs_real_controller_and_writes_report(tmp_path):
    result=run_evaluation(tmp_path,['madrid_drone_novice'],1,[11],offline=True,synthetic_fixture=True)
    assert result['runs']==1 and result['completed_runs']==1
    assert result['semantic_accuracy'] is None
    assert (tmp_path/'summary.json').is_file()
    assert (tmp_path/'summary.md').is_file()
    assert (tmp_path/'evaluation-results.jsonl').is_file()
    data=json.loads(next(tmp_path.glob('session-*.json')).read_text())
    assert data['synthetic'] is True
    assert data['data_classification']=='SYNTHETIC_TEST_ONLY'
    assert data['assessment_mode']=='retrieval_grounded_conversation'
    assert data['numerical_srl'] is None
