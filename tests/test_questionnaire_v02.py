"""Methodological/state boundaries with authored synthetic banks, never private text."""
from copy import deepcopy
import json
import pytest
from indicator_fixtures import bank,questionnaire,Client,reading,matching
from iam_sra.questionnaire import validate_questionnaire
from iam_sra.indicator_assessment import IndicatorAssessment, resolved_scale
from iam_sra.indicator_client import IndicatorClient,validate_match,validate_reading
from iam_sra.conversation_session import ConversationSession
from iam_sra.synthetic_runner import synthetic_collection
from iam_sra.assessment import AssessmentError


def session(profile='citizen', ids=None, **scope):
 s=ConversationSession(synthetic_collection());s.indicators=IndicatorAssessment(bank(),questionnaire())
 s.start_assessment(profile,'Synthetic proposed service',indicator_ids=ids or ['indicator-07','indicator-14','indicator-15'],**scope)
 if profile!='citizen':s.indicator_scope(organisation_or_unit='Planning unit',responsibilities='Planning',technical_object='Test model',object_version='A',intended_environment='Laboratory',component_scope='model')
 return s


def answered(s,client=None):
 client=client or Client();s.indicator_answer('I propose protection for rest because interruption can matter.',client);s.indicator_confirm();s.indicator_finish();return client


@pytest.mark.parametrize('profile',['citizen','organisational','technical'])
def test_all_45_exact_module_mappings_and_direct_entry(profile):
 s=session(profile,ids=[f'indicator-{i:02d}' for i in range(1,16)])
 assert not s.general.events and not s.final_snapshots and s.assessment_route
 for i in range(1,16):
  key=f'indicator-{i:02d}';s.indicator_next(key);m=s.indicators.module();scale=s.indicators.scale(key)
  assert m['profile']==profile and len(scale)==9
  assert [a['statement'] for a in m['anchors']]==[r['statement'] for r in scale]
  assert len({r['level'] for r in scale})==9
  if profile!='citizen':s.indicator_scope(organisation_or_unit='Planning unit',responsibilities='Planning',technical_object='Test model',object_version='A',intended_environment='Laboratory',component_scope='model')
  assert s.indicators.question()['id']==m['question_order'][0]
  assert s.indicators.question()['wording_status']=='newly_drafted'


@pytest.mark.parametrize('change',['criterion','anchor','profile','order','source','duplicate'])
def test_incompatible_questionnaire_is_rejected(change):
 b=bank();q=questionnaire(b);m=q['modules'][0]
 if change=='criterion':m['assessment_criterion']='Invented criterion'
 if change=='anchor':m['anchors'][0]['statement']='Invented anchor'
 if change=='profile':m['profile']='technical'
 if change=='order':m['question_order'].append(m['question_order'][0])
 if change=='source':q['source_register'][0]['sha256']='b'*64
 if change=='duplicate':q['modules'][1]=deepcopy(m)
 with pytest.raises(ValueError):validate_questionnaire(q,b)


def test_navigation_across_batches_and_partial_report_preserve_completed_results():
 s=session(ids=[f'indicator-{i:02d}' for i in range(1,16)]);c=answered(s);s.indicator_suggest(c)
 s.indicator_review('select',s.indicators.revision,'indicator-01-crl-3')
 original=deepcopy(s.indicators.current)
 for n in (6,11,1):s.indicator_next(f'indicator-{n:02d}')
 assert s.indicators.current==original
 s.complete_assessment();data=s.export()['indicator_assessment']
 assert data['report_finished'] and sum(bool(r['participant']) for r in data['results'])==1
 assert len(data['coverage'])==15 and all(r['participant'] is None for r in data['coverage'][1:])


def test_full_answer_can_support_a_passage_missing_from_wrong_or_empty_annotations(monkeypatch):
 s=session();answered(s);e=s.indicators.evidence();scale=s.indicators.scale('indicator-07')
 for observations in ([],reading('I propose','intention')['observations']):
  value=deepcopy(e);value[0]['observations']=observations
  raw=matching(scale,e);assert validate_match(raw,scale,value)['selected_statement_id'].endswith('-5')
  def request(self,http,stage,system,user,schema,validator):
   rows=schema['properties']['assessments']['properties']
   assert all(r['properties']['status']['enum']==['supported','insufficient','conflicting'] for r in rows.values())
   assert len(schema['properties']['selected_statement_id']['anyOf'][0]['enum'])==9
   assert 'enum' not in schema['$defs']['Citation']['properties']['quote']
   assert user['evidence'][0]['answer']==e[0]['answer']
   wire=deepcopy(raw);wire['assessments']={r.pop('statement_id'):r for r in wire['assessments']}
   return validator(wire)
  monkeypatch.setattr(IndicatorClient,'_request',request)
  assert IndicatorClient().match(s.indicators.indicator('indicator-07'),s.indicators.current['scope'],scale,value)['selected_statement_id'].endswith('-5')


def test_no_observations_is_identifiable_and_not_a_no_evidence_shortcut():
 class Missing(Client):
  def interpret(self,*args):
   r=reading(args[3]);r['observations']=[];return r
  def match(self,item,scope,statements,evidence):
   self.calls+=1;assert evidence[0]['answer'] and evidence[0]['observations']==[]
   e=deepcopy(evidence);e[0]['observations']=reading(e[0]['answer'])['observations'];return matching(statements,e)
 s=session();c=Missing();answered(s,c);assert s.indicators.current['events'][0]['interpretation_status']=='no_observations_extracted'
 s.indicator_suggest(c);assert c.calls==1 and s.indicators.current['tool']


def test_citations_profile_scope_and_selected_assessment_consistency_remain_mandatory():
 s=session();answered(s);e=s.indicators.evidence();scale=s.indicators.scale('indicator-07');raw=matching(scale,e)
 for field in ('quote','id','scope','selected','active'):
  v=deepcopy(raw);ev=deepcopy(e)
  if field=='quote':v['assessments'][4]['evidence'][0]['quote']='Fabricated'
  if field=='id':v['assessments'][4]['evidence'][0]['evidence_id']='missing'
  if field=='scope':ev[0]['scope']['response_profile']='technical'
  if field=='selected':v['selected_statement_id']='indicator-07-crl-9'
  if field=='active':ev[0]['active']=False
  with pytest.raises(AssessmentError):validate_match(v,scale,ev,s.indicators.current['scope'])
 v=deepcopy(raw);v['assessments'][0].update(status='supported',evidence=deepcopy(v['assessments'][4]['evidence']))
 with pytest.raises(AssessmentError):validate_match(v,scale,e)


def test_questionnaire_followup_is_grounded_bounded_and_cannot_repeat():
 class Follow(Client):
  def interpret(self,item,scope,question,answer,feedback=''):
   value=reading(answer)
   q=next((q for q in item['questionnaire_candidates'] if '-q' in q['id']),None)
   if q:value.update(next_question_id=q['id'],follow_up_reason='A relevant issue is unresolved.',answer_basis_quote=answer)
   return value
 s=session();c=Follow()
 for n in range(3):
  assert s.indicators.question()['id'].endswith(f'q{n+1:02d}')
  s.indicator_answer('A short synthetic answer.',c);s.indicator_confirm()
 assert s.indicators.current['state']=='ready' and len(s.indicators.current['events'])==3
 value=reading('A short synthetic answer.');value.update(next_question_id='unknown',answer_basis_quote='A short synthetic answer.')
 with pytest.raises(AssessmentError):validate_reading(value,'A short synthetic answer.',s.indicators.candidates())


def test_new_facts_offer_an_answer_addition_then_require_confirmation():
 class New(Client):
  def interpret(self,item,scope,q,answer,feedback=''):
   r=reading(answer)
   if feedback:r.update(needs_answer_edit=True,correction_notice='Please add the new activity as answer information.')
   return r
 s=session();c=New();s.indicator_answer('I know the issue.',c);original=s.indicators.current['pending']['text']
 s.indicator_correct('I also attended a workshop.',c)
 assert s.indicators.current['pending']['text']==original and s.indicators.current['pending']['correction_offer']
 assert s.indicators.evidence()==[]
 s.indicator_add_information('I also attended a workshop.',c)
 assert s.indicators.current['events'][0]['text']==original and not s.indicators.current['events'][0]['active']
 assert s.indicators.evidence()==[]
 s.indicator_confirm();assert 'attended a workshop' in s.indicators.evidence()[0]['answer']


def test_context_object_changes_invalidate_judgments_and_forbid_cross_object_links():
 s=session('technical');c=answered(s);s.indicator_suggest(c);s.indicator_review('endorse',s.indicators.revision)
 before=s.indicators.revision
 s.indicator_scope(technical_object='Different system',object_version='B',intended_environment='Other setting',component_scope='system')
 assert s.indicators.current['tool'] is None and s.indicators.current['participant'] is None and s.indicators.evidence()==[]
 with pytest.raises(ValueError):s.indicator_review('endorse',before)
 assert s.indicators.history
 s.select_indicators(['indicator-07'],'general_understanding','Synthetic proposed service',profile='organisational')
 assert s.indicators.profile=='organisational' and s.indicators.current['state']=='scope'


def test_equivalent_links_are_explicit_and_preserve_source_question_and_scope():
 s=session();answered(s);event=s.indicators.current['events'][0]
 s.indicator_next('indicator-14');assert s.indicators.question()
 s.indicator_link([event['id']]);assert s.indicators.current['state']=='ready'
 linked=s.indicators.evidence()[0];assert linked['answer']==event['text'] and linked['question']==event['question']
 assert linked['origin']=='confirmed_indicator_reuse'


@pytest.mark.parametrize('category',['agree','unsure','not_applicable','declined'])
def test_optional_likert_categories_are_separate_from_readiness(category):
 s=session(likert_enabled=True);c=Client();assert s.indicators.question()['format']=='likert'
 s.indicator_answer(category,c);r=s.indicators.current
 assert r['likert']['category']==category and r['tool'] is None and s.indicators.evidence()==[] and c.calls==0
 assert s.indicators.question()['format']=='open_text'
 s.indicator_finish();s.indicator_suggest(c);assert r['tool']['selected_statement_id'] is None


@pytest.mark.parametrize('profile,availability',[('technical','no_technical_object_identified'),('organisational','outside_role')])
def test_absent_object_or_outside_role_does_not_become_low_level(profile,availability):
 s=session(profile);s.indicator_scope(availability=availability)
 assert s.indicators.current['status']==availability and s.indicators.current['tool']['selected_statement_id'] is None
 with pytest.raises(ValueError):s.indicator_review('select',s.indicators.revision,s.indicators.scale('indicator-07')[0]['id'])
 s.indicator_review('unsure',s.indicators.revision);s.complete_assessment()
 assert s.indicators.current['participant']['statement'] is None


def test_read_more_and_scale_exposure_do_not_rewrite_prior_evidence_or_prove_development():
 s=session();answered(s);before=deepcopy(s.indicators.evidence());s.indicator_information('definition');s.indicator_information('scale')
 assert s.indicators.evidence()==before and len(s.indicators.current['information'])==2
 assert s.indicators.current['events'][0]['information_context']=='before_tool_information'
 assert s.indicators.current['events'][0]['independent_prior_knowledge'] is None


def test_scenario_tie_breaker_has_no_corridor_bonus():
 from iam_sra.conversation_corpus import retrieve_scenarios
 def card(key):return {'id':key,'locale':'en','city':'elsewhere','applicability':{'perspectives':['personal'],'roles':['citizen']},'topic_ids':[]}
 result=retrieve_scenarios({'scenarios':[card('urban_medical_corridor'),card('a_other')]},{'perspective':'personal','stakeholder_category':'citizen','language':'en','city':'other'})
 assert result[0]['id']=='a_other'


def test_source_answer_edit_invalidates_linked_judgments_without_rewriting_history():
 s=session(ids=['indicator-07','indicator-08']);c=answered(s);source=s.indicators.current['events'][0]['id']
 s.indicator_next('indicator-08');s.indicator_link([source]);s.indicator_suggest(c);s.indicator_review('endorse',s.indicators.revision)
 s.indicator_next('indicator-07');s.indicator_edit(source,'answer')
 linked=s.indicators.results['indicator-08']
 assert linked['tool'] is None and linked['participant'] is None and not linked['events'][0]['active']
 assert any(h['indicator_id']=='indicator-08' and h['participant'] for h in s.indicators.history)


def test_context_overflow_preserves_full_confirmed_answers_and_never_generates(monkeypatch):
 s=session();answered(s);before=deepcopy(s.indicators.evidence());client=IndicatorClient()
 def post(self,http,path,payload,*args):
  assert path=='/tokenize'
  text=json.dumps(payload)
  assert before[0]['answer'] in text
  return {'count':4096}
 monkeypatch.setattr(IndicatorClient,'_post_json',post)
 with pytest.raises(AssessmentError) as exc:s.indicator_suggest(client)
 assert exc.value.code=='budget' and s.indicators.current['tool'] is None
 assert s.indicators.evidence()==before and client.last_metrics['generation_calls']==0


def test_comparison_resume_exports_every_reused_record_including_the_tail(monkeypatch,tmp_path):
 import importlib.util
 from pathlib import Path
 import sys
 root=Path(__file__).resolve().parents[1]
 spec=importlib.util.spec_from_file_location('comparison',root/'scripts/evaluate-indicator-questionnaire.py')
 runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 cases=json.loads((root/'eval/indicator_questionnaire_cases_v02.json').read_text())['cases']
 previous=tmp_path/'previous.jsonl';out=tmp_path/'report'
 previous.write_text(''.join(json.dumps({'case_id':c['id'],'policy':runner.POLICY,'status':'completed','result':{'selected_statement_id':None},'calls':1,'seconds':1})+'\n' for c in cases))
 monkeypatch.setattr(runner,'load_bank',bank)
 monkeypatch.setattr(sys,'argv',['comparison','--base-url','http://unused.invalid','--output',str(out),'--resume-from',str(previous)])
 assert runner.main()==0
 rows=[json.loads(r) for r in (out/'evaluation-results.jsonl').read_text().splitlines()]
 assert [r['case_id'] for r in rows]==[c['id'] for c in cases]
 assert rows==json.loads((out/'summary.json').read_text())['runs']


@pytest.mark.parametrize('data',[{'discussion_status':'illustrative'},{'indicator_ids':[]},{'indicator_ids':['unknown']}])
def test_invalid_direct_scope_does_not_finish_the_baseline_or_lose_onboarding(data):
 s=ConversationSession(synthetic_collection());s.indicators=IndicatorAssessment(bank(),questionnaire())
 with pytest.raises(ValueError):s.start_assessment('citizen','Synthetic service',**data)
 assert s.state in {'general_welcome','general_context'} and not s.indicators.selected


def test_failed_answer_addition_retains_original_pending_meaning_and_facts():
 class Broken(Client):
  def interpret(self,*args):raise AssessmentError('Synthetic transport failure.',code='transport')
 s=session();s.indicator_answer('I have considered safeguards.',Client());original=deepcopy(s.indicators.current['pending'])
 with pytest.raises(AssessmentError):s.indicator_add_information('I also attended a workshop.',Broken())
 assert s.indicators.current['pending']==original and s.indicators.current['state']=='interpretation'
 assert not s.indicators.current['events']


@pytest.mark.parametrize('profile',['organisational','technical'])
def test_reconfirming_identical_scope_does_not_restart_completed_assessment(profile):
 s=session(profile);c=answered(s);s.indicator_suggest(c);s.indicator_review('endorse',s.indicators.revision)
 original=deepcopy(s.indicators.current);scope=original['scope']
 keys=['availability','organisation_or_unit','responsibilities','technical_object','object_version','intended_environment','component_scope']
 s.indicator_scope(**{k:scope[k] for k in keys})
 assert s.indicators.current==original and s.indicators.current['state']=='complete'
