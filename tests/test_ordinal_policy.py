"""Deterministic policy/transport contracts; no live semantic validation."""
import json
from copy import deepcopy
import pytest
from iam_sra.ordinal import AnchorFacts,decide
from iam_sra.settings import config
from iam_sra.interpretation import EvidenceItem,freeze
from iam_sra.conversation_client import ConversationClient
from iam_sra.assessment import AssessmentError
from iam_sra.replay_checks import check_export,stage_metrics
from test_client import fake_client
from test_confirmation import meaning,initially_scored
from test_evidence_repair import ContextFake,profile
from test_updates import answer_all

def facts(a='clear',o='none',requirement=False,eid='O.p001',endorsement=False):
    return AnchorFacts(acceptance=a,objection=o,further_requirement=requirement,evidence_ids=[eid],
        endorsement_evidence_ids=[eid] if endorsement else [],rationale='Test descriptive meaning.')

@pytest.mark.parametrize('a,o,r,p,highest,score',[
 ('rejects','categorical',False,'opposed',False,1),
 ('conditional','strong_personal_boundary',True,'opposed',False,2),
 ('conditional','strong_disruption',True,'opposed',False,3),
 ('conditional','meaningful_reservation',True,'mixed',False,4),
 ('balanced','meaningful_reservation',False,'mixed',False,5),
 ('cautious','limited_reservation',False,'supported',False,6),
 ('qualified','limited_reservation',True,'supported',False,7),
 ('clear','none',False,'supported',False,8),
 ('endorsement','none',False,'supported',True,9),
 ('endorsement','none',False,'supported',False,8),
 ('endorsement','none',True,'supported',True,7),
 ('unknown','unknown',False,'uncertain',False,None),
 ('clear','none',False,'opposed',False,None),
 ('conditional','strong_disruption',True,'supported',False,None),
 ('cautious','categorical',False,'mixed',False,None),
 ('clear','strong_personal_boundary',False,'mixed',False,None),
 ('conditional','categorical',False,'opposed',False,None),
])
def test_shared_predicates(a,o,r,p,highest,score):
    d=decide(facts(a,o,r,endorsement=a=='endorsement'),p,highest)
    assert d['score']==score
    assert d['scoring_policy_version']==config('ordinal')['version']

def reply(obj):return {'finish_reason':'stop','message':{'content':json.dumps(obj)}}

@pytest.mark.parametrize('source,text,checked,score',[
 ('citizen_choice','Yes',None,8),
 ('citizen_applicability_confirmation','My earlier support still applies.',None,8),
 ('citizen_original','Yes',False,8),
 ('citizen_original','I endorse the medical purpose without reservations.',True,9),
])
def test_highest_requires_authored_independent_evidence(monkeypatch,source,text,checked,score):
    answers=[reply(facts('endorsement',endorsement=True).model_dump())]
    if checked is not None:answers.append(reply({'supported':checked,'rationale':'Specific endorsement criterion.'}))
    calls=fake_client(monkeypatch,answers)
    evidence={'O.p001':EvidenceItem(id='O.p001',text=text,context='original',source=source)}
    c=ConversationClient();m=meaning(position='supported',scores=('welfare_equity',),facets={'welfare_equity':['medical_public_benefit']})
    result=c.score(freeze(m,evidence,1,'original','Original proposal'))
    assert next(x.score for x in result.concerns if x.concern_id=='welfare_equity')==score
    assert len(calls)==(4 if checked is not None else 2)
    assert c.last_raw_scores=={'welfare_equity':None}
    assert c.last_score_decisions[0]['highest_criterion_verified']==(score==9)

def test_session_cache_exact_context_edit_and_policy_invalidation(monkeypatch):
    calls=fake_client(monkeypatch,[reply(facts().model_dump()) for _ in range(5)])
    c=ConversationClient();c.bind_session('one',0)
    evidence={'O.p001':EvidenceItem(id='O.p001',text='The hum is acceptable.',context='original',source='citizen_original')}
    record=freeze(meaning(position='supported'),evidence,1,'original','Original proposal')
    assert c.score(record).concerns[0].score==8
    c.score(record)
    assert len(calls)==2 and c.last_metrics['cache_hits']==1
    c.bind_session('one',1);c.score(record);assert len(calls)==4
    c.bind_session('two',1);c.score(record);assert len(calls)==6
    changed=freeze(meaning(position='supported'),evidence,1,'original','Other original wording')
    c.score(changed);assert len(calls)==8
    old=config('ordinal')['version']
    original_config=config
    monkeypatch.setattr('iam_sra.conversation_client.config',lambda name: {**original_config(name),'version':old+'-changed'} if name=='ordinal' else original_config(name))
    c.score(record);assert len(calls)==10

def test_cache_does_not_save_schema_failure(monkeypatch):
    calls=fake_client(monkeypatch,[reply({'score':9}),reply({'score':9}),reply(facts().model_dump())])
    c=ConversationClient();c.bind_session('one',0)
    record=freeze(meaning(position='supported'),{'O.p001':EvidenceItem(id='O.p001',text='Noise is fine.',context='original',source='citizen_original')},1,'original','Original')
    with pytest.raises(AssessmentError):c.score(record)
    c.score(record)
    assert len(calls)==6 and c.last_metrics['cache_hits']==0

class AnchoredFake(ContextFake):
    """Controlled semantic descriptors, not a simulation of Qwen accuracy."""
    def score(self,record,only=None,unavailable=None):
        result=super().score(record,only,unavailable)
        self.last_score_decisions=[]
        for c in result.concerns:
            if c.score is None:continue
            for facet in c.facets:
                a,o,r=('clear','none',False) if c.position=='supported' else ('conditional','strong_personal_boundary' if facet=='personal_privacy' else 'strong_disruption',True)
                source=next(x for x in record['meaning']['concerns'] if x['concern_id']==c.concern_id)
                d=decide(facts(a,o,r,source['excerpts'][0]),c.position)
                d.update(concern_id=c.concern_id,facet=facet,confirmed_position=c.position,context=record['context'],condition_ids=source['conditions'])
                self.last_score_decisions.append(d);c.score=d['score']
        return result

def completed():
    s,c=initially_scored(AnchoredFake(profile()));s.begin_followups();answer_all(s,c)
    initial=s.initial
    s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':'yes'}})
    s.continue_final(True,c)
    return s,c,initial

def test_unchanged_meaning_reuse_and_changed_facets_are_reviewed():
    s,c,initial=completed()
    decision=next(d for d in s.conditional['score_decisions'] if d['facet']=='medical_public_benefit')
    assert decision['score']==8 and decision['origin']=='equivalent_meaning_reuse'
    assert decision['source_decision']['score']==8
    assert not any(call[0]=='score' and call[1]=='modified' and call[3]=={'welfare_equity'} for call in c.calls)
    for d in s.conditional['score_decisions']:
        if d['facet']!='medical_public_benefit':assert d['origin']=='python_anchor_predicate'
    assert s.initial==initial
    assert s.initial['aggregate']['trace']['denominator']==3 and s.initial['aggregate']['mean']==13/3
    assert s.initial['aggregate']['adjusted']==4
    assert s.conditional['aggregate']['mean']==8
    checks=check_export(s.export(),initial)
    assert checks['structural_evidence_checks_passed'] and checks['rubric_checks_passed']

def test_equivalence_rejects_changed_policy_construct_conditions_and_edits():
    s,c,initial=completed()
    f=next(f for f in s.facet_meanings if f.facet=='medical_public_benefit')
    assert s._equivalent_decision(f)
    source=deepcopy(s._pending_final_original)
    for field,value in [('construct','other_construct'),('scoring_policy_version','old'),('anchor_rule_id','categorical_refusal')]:
        s._pending_final_original=deepcopy(source)
        d=next(d for d in s._pending_final_original['score_decisions'] if d['facet']=='medical_public_benefit');d[field]=value
        assert s._equivalent_decision(f) is None
    s._pending_final_original=source
    s.rewind('combined_proposal')
    assert s.final is None and s.conditional is None and s._pending_final_original is None
    assert s.initial==initial and s.revision_history

def test_replay_completion_is_not_correctness_and_exports_have_origins():
    s,c,initial=completed();export=s.export()
    assert export['schema_version']=='5.3.0'
    for domain in export['domain_assessments']:
        for row in domain['profiles'].values():
            assert row['score_record'] is not None and row['score_record']['reason']
            assert row['score_record']['scoring_policy_version']==config('ordinal')['version']
    export['aggregation']['conditional_modified']['rounded']=9
    export['audit']['snapshots']['conditional_modified']['aggregate']['rounded']=9
    checks=check_export(export,initial)
    assert not checks['structural_evidence_checks_passed']
    assert any(not c['passed'] and 'aggregate_arithmetic' in c['check'] for c in checks['structural_evidence_checks'])

def test_metrics_deduplicate_copied_requests_and_count_failures():
    s,c,initial=completed()
    metric={'request_id':'unique','stage':'scope_review','model_calls':2,'retries':1,'cache_hit':False,'latency_seconds':3}
    s.inference.extend([{'settings':{'request_metrics':[metric]}},{'settings':{'request_metrics':[metric]}}])
    assert stage_metrics(s)['scope_review']=={'model_calls':2,'retries':1,'cache_hits':0,'latency_seconds':3}

def test_changed_support_can_decrease_without_any_monotonic_rule():
    original=decide(facts(), 'supported')
    updated=decide(facts('rejects','categorical'), 'opposed')
    assert original['score']==8 and updated['score']==1
    assert decide(facts('conditional','meaningful_reservation',False),'mixed')['score'] is None

def test_skip_unsure_do_not_reuse_unchanged_scores():
    for response in ['skip','unsure']:
        s,c=initially_scored(AnchoredFake(profile()));s.begin_followups();answer_all(s,c)
        s.record_joint('accept',[],'',c,{'welfare_equity:medical_public_benefit':{'response':response}})
        s.continue_final(True,c)
        medical=s.conditional['score_records']['welfare_equity']
        assert medical['score'] is None and medical['origin']=='unavailable'
        assert s.conditional['aggregate']['rounded'] is None and s.conditional['aggregate']['trace']['denominator']==2

def test_replay_no_live_exits_nonzero_and_never_contacts_endpoint(tmp_path):
    import subprocess,sys
    path=tmp_path/'disabled.json'
    result=subprocess.run([sys.executable,'scripts/replay-fn-evidence.py','--no-live','--output',str(path)],capture_output=True,text=True)
    assert result.returncode==1
    row=json.loads(path.read_text())
    assert not row['live_model_used'] and not row['dialogue_completed'] and row['stage_metrics']=={}
    assert row['failure_stage']=='not_attempted'

def test_ui_reuses_only_session_client_and_hides_intermediate_scores(monkeypatch):
    from test_ui import fresh,click,assert_simple
    client=ContextFake(profile());app=fresh(monkeypatch,client)
    assert app.session_state._conversation_client is client
    click(app);app.text_area(key='citizen_answer').set_value('Support medical purpose, oppose noise and cameras.')
    click(app);assert_simple(app)
    app.run();assert app.session_state._conversation_client is client
    assert app.session_state.session.initial is None

def test_replay_checks_reject_unsupported_topic_and_wrong_context():
    s,c,initial=completed();export=s.export()
    export['audit']['original_facet_meanings'].append({'concern_id':'airspace_capacity','facet':'airspace_traffic','position':'opposed'})
    checks=check_export(export,initial,{'facets':[['welfare_equity','medical_public_benefit']], 'exclude':['airspace_capacity']})
    assert not checks['structural_evidence_checks_passed']
    export=s.export()
    d=export['audit']['snapshots']['conditional_modified']['score_decisions'][0]
    d['evidence_ids']=['O.p001']
    assert not check_export(export,initial)['structural_evidence_checks_passed']

def test_replay_reports_transport_failure_as_failure_not_live_pass(monkeypatch):
    import importlib.util,httpx
    spec=importlib.util.spec_from_file_location('fn_replay','scripts/replay-fn-evidence.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class Down:
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,*a,**k):raise httpx.ConnectError('offline test only')
    monkeypatch.setattr('iam_sra.llm_client.httpx.Client',Down)
    row=module.replay(ConversationClient())
    assert row['failure_stage']=='initial interpretation' and not row['success']
    assert not row['live_model_used'] and not row['dialogue_completed']
    assert row['stage_metrics']['mapping']['model_calls']==0

def test_uncertain_facet_is_not_scored_even_with_willingness(monkeypatch):
    calls=fake_client(monkeypatch,[])
    m=meaning(position='uncertain');m.concerns[0].conditional_willingness='willing'
    record=freeze(m,{'O.p001':EvidenceItem(id='O.p001',text='I am unsure but might accept changes.',context='original',source='citizen_original')},1,'original','Original')
    result=ConversationClient().score(record)
    assert calls==[] and result.concerns[0].score is None
    assert decide(facts('endorsement'), 'supported',True)['score']==8

def test_replay_reports_do_not_overwrite_previous_artifacts(tmp_path):
    from iam_sra.replay_checks import write_report
    path=tmp_path/'replay.json'
    write_report(path,{'success':True})
    old=path.read_text();new=write_report(path,{'success':False})
    assert path.read_text()==old and new!=path
    assert not json.loads(new.read_text())['success']
