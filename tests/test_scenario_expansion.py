"""Six-case mapping, integrity and shared workflow, using authored synthetic sources."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from indicator_fixtures import bank,questionnaire,scenario_cases,Client,reading
from iam_sra.scenario_expansion import expansion_cards
from iam_sra.conversation_corpus import retrieve_scenarios,explanation_collection
from iam_sra.conversation_sources import scenario_explanations
from iam_sra.conversation_session import ConversationSession
from iam_sra.indicator_assessment import IndicatorAssessment
from iam_sra.synthetic_runner import synthetic_collection


def source_fixture(tmp_path):
 p=tmp_path/'synthetic-source.txt';p.write_text('Authored synthetic source.')
 digest=sha256(p.read_bytes()).hexdigest()
 register={'sources':[{'document':p.name,'local_path':p.name,'sha256':digest}],
  'scenario_expansion_v01':{'document':'synthetic-scenarios.json','json_sha256':'b'*64,
   'source_resolution':{'local':{'local_document':p.name,'status':'verified_hash','verification_note':'Fixture hash matches.'},
    'missing':{'local_document':None,'status':'original_missing','verification_note':'Fixture original absent.'}}}}
 cases=[]
 for n in range(1,7):
  c=scenario_cases()[n-1]
  cases.append({'id':c['id'],'version':c['version'],'title':c['title'],'locale':'en','area':'Synthetic area',
    'source_status':c['source_status'],'review_status':c['review_status'],'approved_by':None,
    'source_basis_summary':'Authored synthetic source context.','text':c['text'],'wording_origin':'newly_drafted',
    'opening_question':c['opening_question'],'conditional_followup':c['conditional_followup'],'indicator_ids':['indicator-07'],
    'source_refs':[{'source_id':'missing' if n==3 else 'local','locator':'Synthetic section'}],
    'significant_unknowns':c['unknowns']})
 value={'schema_version':'iam-sra-scenario-expansion-0.1.0','scenario_bank_version':'2026-10-21-v0.1',
    'compatible_questionnaire_version':'2026-10-21-v0.2','source_register':[{'id':'local','document':p.name,'sha256':digest},
    {'id':'missing','document':'missing.pdf','sha256':'c'*64}],'scenarios':cases}
 return value,register


def test_six_case_mapping_preserves_draft_and_missing_source_status(tmp_path):
 value,register=source_fixture(tmp_path);cards,sources=expansion_cards(value,questionnaire(),register,tmp_path)
 assert len(cards)==len({c['id'] for c in cards})==6 and len(sources)==1
 assert cards[2]['source_verification']=='unverified_draft_adaptation'
 assert cards[2]['source_refs'][0]['verification_status']=='original_missing'
 assert all(c['approved_by'] is None and c['text']==v['text'] for c,v in zip(cards,value['scenarios']))
 assert cards[0]['topic_ids']==['noise']


@pytest.mark.parametrize('change',['duplicate','route','source','hash','approval'])
def test_incompatible_expansion_is_rejected(tmp_path,change):
 v,r=source_fixture(tmp_path)
 if change=='duplicate':v['scenarios'][1]=deepcopy(v['scenarios'][0])
 if change=='route':v['scenarios'][0]['indicator_ids']=['unknown']
 if change=='source':v['scenarios'][0]['source_refs'][0]['source_id']='unknown'
 if change=='hash':r['sources'][0]['sha256']='a'*64
 if change=='approval':v['scenarios'][0]['approved_by']='Invented approval'
 with pytest.raises(ValueError):expansion_cards(v,questionnaire(),r,tmp_path)


def session(profile='citizen'):
 c=synthetic_collection();c['scenarios']+=scenario_cases()
 s=ConversationSession(c);s.indicators=IndicatorAssessment(bank(),questionnaire())
 s.start_assessment(profile,'Confirmed proposed local service',indicator_ids=['indicator-07','indicator-08'])
 if profile!='citizen':s.indicator_scope(organisation_or_unit='Planning unit',responsibilities='Planning',technical_object='Test model')
 return s


@pytest.mark.parametrize('profile',['citizen','organisational','technical'])
def test_optional_case_preserves_local_scope_and_profile_questions_and_exports(profile):
 s=session(profile);primary=deepcopy(s.indicators.scope);s.indicator_case('expansion-04')
 assert s.indicators.scope==primary and s.indicators.current['scope']['use_case']==primary['use_case']
 assert s.indicators.current['scope']['illustrative_case']['id']=='expansion-04'
 assert not s.indicators.current['tool'] and not s.indicators.current['participant']
 candidates=s.indicators.candidates();reflections=[q for q in candidates if q.get('kind')=='case_reflection']
 assert len(reflections)==(1 if profile=='citizen' else 0)
 assert s.indicators.question()['id']==s.indicators.module()['question_order'][0]
 s.indicator_answer('I can discuss a possible effect.',Client());s.indicator_confirm();s.indicator_finish();s.indicator_suggest(Client())
 s.indicator_review('unsure',s.indicators.revision);s.complete_assessment()
 d=s.browser_export()['indicator_assessment'];row=d['results'][0]
 assert row['scope']['illustrative_case']['text']==scenario_cases()[3]['text']
 assert row['scope']['illustrative_case']['source_refs'][0]['verification_status']=='original_missing'
 assert row['events'][0]['information_context']=='after_information'
 assert row['participant']['status']=='unsure' and row['tool'] is not None
 # Declining is a deliberate context edit, not low readiness or blocked assessment.
 s.indicator_case(None);assert 'illustrative_case' not in s.indicators.current['scope']
 assert s.indicators.current['tool'] is None and s.indicators.current['participant'] is None


def test_case_questions_are_conditional_and_share_the_three_question_budget():
 s=session();s.indicator_case('expansion-04')
 class Gaps(Client):
  def interpret(self,item,scope,question,answer,feedback=''):
   v=reading(answer);candidate=next((q for q in item['questionnaire_candidates'] if q.get('kind')=='case_reflection'),None)
   if candidate:v.update(next_question_id=candidate['id'],answer_basis_quote=answer,follow_up_reason='A relevant issue remains unclear.')
   return v
 for i in range(3):s.indicator_answer('A synthetic unresolved issue.',Gaps());s.indicator_confirm()
 assert s.indicators.current['state']=='ready'
 ids=[e['question']['id'] for e in s.indicators.current['events']]
 assert ids==['indicator-07-crl-q01','expansion-04-opening','expansion-04-probe']


def test_case_edit_invalidates_only_dependent_results_and_does_not_repeat_seen_text():
 s=session();s.indicator_answer('I propose safeguards.',Client());s.indicator_confirm();s.indicator_finish();s.indicator_suggest(Client());s.indicator_review('endorse',s.indicators.revision)
 saved=deepcopy(s.indicators.current);s.indicator_next('indicator-08');s.indicator_case('expansion-01')
 assert s.indicators.results['indicator-07']==saved
 s.indicator_case(None);s.indicator_case('expansion-01')
 assert s.indicators.current['information'][-1]['already_presented'] is True and len(s.indicators.presented_cases)==1


def test_case_explanations_do_not_leak_corridor_or_other_case_facts():
 cards=scenario_cases();c=synthetic_collection();c['explanations']+=scenario_explanations(cards)
 result=explanation_collection(c,'expansion-04')
 ids={r['id'] for r in result['passages']}
 assert 'expansion-04_facts' in ids and all(not i.startswith('expansion-') or i=='expansion-04_facts' for i in ids)
 assert all(r['scenario_applicability']=='expansion-04' for r in result['passages'])
 assert all(r.get('document_title')!='SRA_LLM_FN_concept.pdf' for r in result['passages'])


def test_diversity_prefers_distinct_situations_before_duplicate_villages():
 c=synthetic_collection();c['scenarios']=scenario_cases()[:2]
 for n in range(3):
  route=deepcopy(c['scenarios'][0]);route.update(id=f'ga_coimbra_{n}',city='coimbra');route.pop('situation_family');c['scenarios'].append(route)
 context={'perspective':'personal','stakeholder_category':'citizen','language':'en','city':'coimbra'}
 rows=retrieve_scenarios(c,context,indicator_id='indicator-07')
 assert len({r.get('situation_family','route') for r in rows[:3]})==3


def test_active_session_freezes_case_and_rejects_stale_collection_actions(monkeypatch):
 from iam_sra.api.adapter import ControllerAdapter
 from iam_sra.api.errors import APIError
 s=session();s.indicator_case('expansion-04');before=deepcopy(s.indicators.current['scope']['illustrative_case'])
 fresh=deepcopy(s.collection);fresh['scenarios'][-3]['text']='Changed synthetic configuration.'
 adapter=ControllerAdapter();adapter._collection=fresh;monkeypatch.setattr(adapter,'readiness',lambda:{'corpus':'ready'})
 with pytest.raises(APIError) as exc:adapter.apply(s,'indicator_finish',{},10**12)
 assert exc.value.code=='source_unavailable'
 assert s.indicators.current['scope']['illustrative_case']==before


@pytest.mark.presidio_live
def test_real_private_old_and_expanded_collections_load_without_rewriting_sources(monkeypatch):
 from pathlib import Path
 from iam_sra.settings import ROOT
 from iam_sra.conversation_corpus import load_corpus
 if not (ROOT/'references/private/conversation-corpus-scenarios-v01.json').exists():pytest.skip('Private review corpus absent.')
 monkeypatch.delenv('IAM_CONVERSATION_CORPUS',raising=False)
 old=load_corpus();assert len(old['scenarios'])==9
 monkeypatch.setenv('IAM_CONVERSATION_CORPUS','references/private/conversation-corpus-scenarios-v01.json')
 new=load_corpus();assert len(new['scenarios'])==15 and new['version']=='conversation-corpus-1.2.0'
 assert new['scenarios'][:9]==old['scenarios']
 assert sum(c.get('source_verification')=='unverified_draft_adaptation' for c in new['scenarios'])==1
 assert sum(c.get('source_verification')=='partly_verified_draft_adaptation' for c in new['scenarios'])==1
 # Changing the declared expansion identity fails closed on the next load.
 import iam_sra.scenario_expansion as module
 original=module.load_expansion
 def changed():
  cards,sources,identity=original();identity['version']='changed';return cards,sources,identity
 monkeypatch.setattr(module,'load_expansion',changed)
 with pytest.raises(ValueError,match='configuration changed'):load_corpus()


@pytest.mark.parametrize('profile,availability',[('organisational','outside_role'),('technical','no_technical_object_identified')])
def test_case_change_cannot_turn_outside_role_or_no_object_into_a_level(profile,availability):
 s=session(profile);s.indicator_scope(availability=availability);s.indicator_case('expansion-04')
 row=s.indicators.current
 assert row['disposition']==availability and row['tool']['status']=='abstained' and row['tool']['statement'] is None
 with pytest.raises(ValueError):s.indicator_review('select',s.indicators.revision,s.indicators.scale(s.indicators.current_id)[0]['id'])


def test_changing_the_reusing_indicator_does_not_invalidate_the_original_source():
 s=session();c=Client();s.indicator_answer('I propose safeguards.',c);s.indicator_confirm();s.indicator_finish();s.indicator_suggest(c);s.indicator_review('endorse',s.indicators.revision)
 source=s.indicators.current['events'][0]['id'];original=deepcopy(s.indicators.current)
 s.indicator_next('indicator-08');s.indicator_link([source]);s.indicator_suggest(c);s.indicator_review('endorse',s.indicators.revision)
 s.indicator_case('expansion-01')
 assert s.indicators.results['indicator-07']==original
 assert s.indicators.current['tool'] is None and not s.indicators.current['events'][0]['active']
