"""FN reference-path fidelity and separately authored adaptive boundary tests."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import pytest
from iam_sra.chat_session import ChatSession, explicit_profile
from iam_sra.chat_client import validate_reply
from iam_sra.fn_interview import specification, flow_key
from iam_sra.privacy import PrivacyError
from iam_sra.assessment import AssessmentError
from indicator_fixtures import bank
from fn_fixture import reply, SyntheticInterpreter, ScoreFixture

ROOT=Path(__file__).resolve().parents[1]
GOLDEN=json.loads((ROOT/'eval/fn_golden_paths.json').read_text())['flows']


class GoldenInterpreter:
    def __init__(self, key):self.rows=GOLDEN[key];self.calls=[]
    def turn(self,request):
        goal=request['fn']['evidence_goal']
        row=next(r for r in self.rows if r['id']==goal)
        assert request['answer']==row['answer']
        self.calls.append(goal)
        index=self.rows.index(row)
        following=self.rows[index+1]['id'] if index+1<len(self.rows) else None
        node=next((q for s in specification()['flows'][flow_key(request['profile'],request['depth'])] for q in s['questions'] if q['id']==following),{})
        boundary=[following] if node.get('when')=='boundary' else []
        return reply(request,kind=row['answer_kind'],status='unknown' if row['answer_kind']=='uncertain' else 'explored',topics=row['topics'],boundary=boundary)


def replay(key):
    profile='citizen' if key.startswith('citizen') else key
    s=ChatSession(bank(), 'extended' if key.endswith('extended') else 'short',synthetic=True)
    client=GoldenInterpreter(key);scorer=ScoreFixture()
    s.send({'citizen':'A. Citizen','organisational':'B. Organisation or institution','technical':'C. Technology expert or researcher'}[profile],client)
    questions=[]
    for row in GOLDEN[key]:
        assert s.stage=='conversation',(key,row['id'],s.stage,s.messages[-1])
        assert s.objective==row['id'],(key,row['id'],s.objective,s.messages[-1]['text'])
        assert row['question'] in s.messages[-1]['text']
        assert s.view()['scale'] is None and s.suggestion is None
        questions.append(row['id'])
        s.send(row['answer'],client,score_client=scorer)
        if s.objective=='citizen_duration':s.send('35 minutes' if key=='citizen_extended' else '20 minutes',client)
    return s,client,scorer,questions


@pytest.mark.parametrize('key',list(GOLDEN))
def test_fn_golden_canonical_questions_branches_and_end_review(key):
    s,c,scorer,questions=replay(key)
    assert s.stage=='review' and s.view()['scale']['anchors']==s.source_scales[key]
    assert all(row['status']=='explored' for row in s.fn.export(s.profile,s.depth,s.concerns)['stages'])
    assert questions.index('open_priorities') < questions.index('priorities')
    assert all(q in questions for q in ('area','open_more','priorities'))
    assert s.priorities and all(p['origin']=='respondent_selected' for p in s.priorities)
    assert not any('indicator-' in m['text'] for m in s.messages if m['role']=='assistant')
    if s._has_model_score():
        # The fixture selection is arbitrary; FN's illustrative 6/6/7 are not targets.
        assert s.suggestion['level']==4
        text=s.messages[-1]['text']
        assert all(f'{letter}.' in text for letter in 'ABCDE')
        before=deepcopy(s.suggestion)
        s.send('A',c)
        assert s.stage=='ended' and s.participant_review['validation']=='agrees' and s.suggestion==before
    else:
        assert s.suggestion['level'] is None and s.suggestion['gaps']
        s.send('I am not sure',c);s.send('no changes',c)
        assert s.stage=='ended' and s.suggestion['level'] is None
    out=s.export()
    assert out['overall_srl'] is None and out['training_eligible'] is False
    assert out['fn_interview']['coverage_is_readiness'] is False


@pytest.mark.parametrize('key',list(GOLDEN))
def test_golden_text_and_identity_are_independently_checked_against_full_pdf(key):
    register=json.loads((ROOT/'references/chat-source-register.json').read_text())
    entry=register['sources'][key];path=ROOT/'references/private'/entry['document']
    assert sha256(path.read_bytes()).hexdigest()==entry['sha256']
    text=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True)
    normal=lambda t:' '.join(t.replace('\u200b','').split())
    body=normal(text)
    for row in GOLDEN[key]:
        assert normal(row['question']) in body
        if row['answer_origin']=='FN_example':assert normal(row['answer']) in body
    assert 'Interviewer guidance' in text or 'Guidance for the interviewer' in text


@pytest.mark.parametrize('text,expected',[
    ('A. Citizen','citizen'),('B. Organisation or institution','organisational'),
    ('C. Technology expert or researcher','technical'),('A','citizen'),('B','organisational'),('C','technical'),
    ('I am an engineer',None),('Citizen and technology expert',None)])
def test_explicit_choices_and_ambiguous_profession(text,expected):assert explicit_profile(text)==expected


def start(profile='citizen',depth='short'):
    s=ChatSession(bank(),depth,synthetic=True);c=SyntheticInterpreter()
    s.send(profile,c);s.send('Madrid',c)
    if s.profile=='citizen':s.send('35 minutes' if depth=='extended' else '20 minutes',c)
    return s,c


def test_unknown_citizen_explanation_and_local_uncertainty_not_prior_knowledge():
    s,c=start();s.send('Not that I know of',c)
    assert s.objective=='drone_explanation'
    s.send('yes',c)
    assert s.exposures[-1]['prior_knowledge'] is False
    assert s.objective=='healthcare_awareness'
    s.send('not that I know of',c);s.send('not that I know of',c)
    assert s.context['city_status']=='respondent_provided_unverified'
    assert s.objective=='open_priorities' and s.suggestion is None


def test_qualified_yes_uses_semantics_in_same_call_and_follows_correct_branch():
    s,c=start()
    class Pilot:
        calls=0
        def turn(self,req):
            self.calls+=1
            return reply(req,kind='partial')
    model=Pilot();s.send('Yes, but only for a pilot',model)
    assert model.calls==1 and s.objective=='drone_description'


def test_topic_mention_is_not_priority_or_capability_and_wildlife_remains_allowed():
    s,c=start()
    # Drive to the open discussion with an unfamiliar citizen, without fixtures matching example answers.
    for answer in ('no','no','no','unknown'):s.send(answer,c)
    assert s.objective=='open_priorities'
    s.send('Noise and wildlife concern me.',c)
    assert not s.priorities and all(not r['selected_priority'] for r in s.concerns)
    for answer in ('No other issues.','People near nests could be affected.'):s.send(answer,c)
    assert s.objective=='priorities'
    s.send('Wildlife is my priority.',c)
    assert [p['topic'] for p in s.priorities]==['wildlife']
    assert s.objective=='priority_understanding'


def test_turn_count_and_model_conclude_cannot_skip_essential_goals():
    s,c=start();s.send('yes',c)
    class End:
        def turn(self,req):
            out=reply(req);out['proposed_action']='propose_conclusion';out['interpretation']['action']='conclude';return out
    for _ in range(20):s._user('An arbitrary topic mention is not evidence of a capability.')
    s.send('An aircraft without an onboard pilot.',End())
    assert s.stage=='conversation' and s.objective=='drone_uses'
    assert 'earliest_model_wrap_after' not in s._discussion_progress()


def test_semantic_multi_goal_coverage_skips_redundant_questions_and_rejects_invented_quotes():
    s,c=start();s.send('yes',c)
    class Several:
        def turn(self,req):
            text=req['answer'];eid=req['current_answer_id']
            return reply(req,coverage=[{'goal':g,'evidence_id':eid,'quote':text,'status':'explored','answer_kind':'substantive'} for g in ('drone_description','drone_uses')])
    s.send('An aircraft without an onboard pilot; I have seen it used for photography.',Several())
    assert s.objective=='healthcare_awareness'
    req=s._request('An uncertain answer.')
    out=reply(req,coverage=[{'goal':'opinion','evidence_id':'invented','quote':'fabricated','status':'explored','answer_kind':'substantive'}])
    checked=validate_reply(out,req)
    assert checked['interpretation']['coverage']==[]


@pytest.mark.parametrize('profile',['citizen','organisational','technical'])
@pytest.mark.parametrize('choice',list('ABCDE'))
def test_all_five_profile_validation_choices_preserve_initial_result(profile,choice):
    s,c=start(profile)
    # Review tests isolate the final protocol; golden replay above proves normal entry.
    s.context.update(organisation_or_unit='A synthetic unit',responsibilities='Its own planning role',technical_object='A synthetic component v1')
    s.partial=True;s._report(score_client=ScoreFixture())
    initial=deepcopy(s.suggestion)
    assert s._has_model_score()
    s.send(choice,c)
    if choice=='A':assert s.stage=='ended' and s.participant_review['validation']=='agrees'
    else:
        assert s.stage=='review_addition'
        s.send('Additional fictional evidence has not been independently verified.',c)
        if s.stage!='ended':s.send('no changes',c)
        assert s.participant_review['status']=='pending_human_review'
    assert s.suggestion==initial
    assert s.participant_review['model_result_revision']==initial['revision']


def test_technical_failures_preserve_answer_and_wait_without_implying_respondent_uncertainty():
    s,c=start();s.send('yes',c)
    class Broken:
        def turn(self,request):raise AssessmentError('Synthetic transport failure',code='timeout')
    s.send('My synthetic original answer.',Broken())
    assert s.messages[-1]['act']=='failure' and 'technical problem' in s.messages[-1]['text']
    s.send('retry',Broken())
    assert s.objective=='drone_description' and 'drone_description' not in s.fn.unresolved_gaps
    assert 'drone_description' not in s.fn.coverage
    assert s.view()['answer_processing']['status']=='retry_required'
    assert len([m for m in s.active_evidence() if m['text']=='My synthetic original answer.'])==1
    s.send('stop',c)
    assert s.partial and s.stage=='summary'


def test_model_cannot_claim_coverage_for_a_goal_from_another_profile():
    s,c=start();s.send('yes',c)
    req=s._request('This is a synthetic answer.')
    out=reply(req,coverage=[{'goal':'qualification_evidence','evidence_id':req['current_answer_id'] or 'm1','quote':'This is a synthetic answer.','status':'explored','answer_kind':'substantive'}])
    assert validate_reply(out,req)['interpretation']['coverage']==[]


def test_grounded_adaptive_followup_is_used_once_without_a_second_model_call():
    s,c=start();s.send('yes',c)
    class Clarify:
        calls=0
        def turn(self,request):
            self.calls+=1
            result=reply(request,coverage=[],action='clarify')
            result['message']='When you say autonomous, what do you mean by that?'
            return result
    model=Clarify();s.send('It is autonomous, but I am unsure what that means.',model)
    assert model.calls==1 and s.objective=='drone_description'
    assert s.messages[-1]['text']=='When you say autonomous, what do you mean by that?'
    s.send('An aircraft with no pilot sitting inside.',c)
    assert s.objective=='drone_uses'


def test_several_concerns_cannot_become_priorities_via_unrequested_annotation():
    s,c=start()
    for text in ('no','no','no','unknown'):s.send(text,c)
    class NoSelection:
        def turn(self,request):
            out=reply(request,topics=['noise','wildlife'])
            out['interpretation']['coverage'].append({'goal':'priorities','evidence_id':request['current_answer_id'],
                'quote':request['answer'],'status':'explored','answer_kind':'substantive'})
            return out
    s.send('Noise and wildlife are concerns.',NoSelection())
    assert not s.priorities and 'priorities' not in s.fn.coverage
    assert all(not r['selected_priority'] for r in s.concerns)


def test_organisation_draft_preparation_and_pilot_branches_keep_own_remit():
    s,c=start('organisational')
    for text in ('A synthetic planning unit.','Only public-space coordination, not aircraft certification.'):
        s.send(text,c)
    original=s.context['responsibilities']
    # A later model scope annotation cannot silently add aircraft certification.
    s._user('Another unit handles certification.')
    s._apply_context_facts({'context_facts':[{'field':'responsibilities','quote':'certification'}]},'Another unit handles certification.',s.messages[-1]['id'])
    assert s.context['responsibilities']==original
    s.fn.record('planning','m2','explored','partial')
    assert s.fn.applicable(s.fn.current(s.profile,s.depth,'planning_detail'),s.concerns)
    s.fn.record('testing','m2','explored','no')
    assert not s.fn.applicable(s.fn.current(s.profile,s.depth,'lessons'),s.concerns)
    # Pilot preparation is not forced into a high readiness result.
    assert s.suggestion is None


def test_technical_component_scope_does_not_become_whole_system_and_ambiguity_clarifies():
    s,c=start('technical')
    for text in ('A synthetic research unit.','Laboratory controller tests only.','A controller component v1.','The controller only, not aircraft integration.'):
        s.send(text,c)
    assert 'component' in s.context['technical_object']
    original=s.context['technical_object']
    s._user('A complete aircraft is a different object.')
    s._apply_context_facts({'context_facts':[{'field':'technical_object','quote':'complete aircraft'}]},'A complete aircraft is a different object.',s.messages[-1]['id'])
    assert s.context['technical_object']==original
    s.objective='controlled'
    class Ambiguous:
        def turn(self,req):
            out=reply(req,coverage=[],action='clarify')
            out['message']='What configuration and test environment were used?'
            return out
    s.send('We did a real-world pilot.',Ambiguous())
    assert s.objective=='controlled' and s.messages[-1]['text']=='What configuration and test environment were used?'
    assert s.suggestion is None


def test_correction_invalidates_semantic_coverage_supported_by_superseded_words():
    s,c=start();s.send('yes',c);s.send('An aircraft without an onboard pilot.',c)
    old=next(r for r in s.active_evidence() if r['objective_id']=='drone_description')
    assert s.fn.coverage['drone_description']['evidence_ids']==[old['id']]
    s.pending_correction=old['id']
    s.send('I am not sure what a drone means.',c)
    assert not old['active'] and 'drone_description' not in s.fn.coverage
    assert s.objective=='drone_description'


@pytest.mark.parametrize('key',list(GOLDEN))
def test_all_fn_flows_through_owned_api_jobs_and_both_exports(key):
    from iam_sra.api import create_app
    from iam_sra.api.adapter import ControllerAdapter
    from iam_sra.api.service import AssessmentService
    from test_indicator_api import factory
    from test_api_integration import Browser
    model=GoldenInterpreter(key);scorer=ScoreFixture()
    adapter=ControllerAdapter(engine_factory=factory,clients_factory=lambda e:{'chat':model,'chat_score':scorer},readiness=lambda:{'privacy':'ready','corpus':'ready'})
    manager=AssessmentService(adapter)
    app=create_app({'TESTING':True,'SECRET_KEY':'f'*40},service=manager)
    try:
        b=Browser(app)
        response=b.client.post('/v1/sessions',json={'mode':'chat','depth':'extended' if key=='citizen_extended' else 'short'},headers={'X-CSRF-Token':b.csrf})
        assert response.status_code==201
        b.view=response.json['session']
        b.act('chat_message',{'text':'A' if key.startswith('citizen') else 'B' if key=='organisational' else 'C'})
        for row in GOLDEN[key]:
            assert row['question'] in b.view['chat']['messages'][-1]['text']
            b.act('chat_message',{'text':row['answer']})
            if 'How much time' in b.view['chat']['messages'][-1]['text']:
                b.act('chat_message',{'text':'35 minutes' if key=='citizen_extended' else '20 minutes'})
        assert b.view['chat']['stage']=='review'
        b.act('chat_message',{'text':'A'})
        assert b.view['chat']['stage']=='ended' and b.view['chat']['participant_review']['validation']=='agrees'
        assert Browser(app).client.get('/v1/sessions/'+b.view['id']+'/export').status_code==404
        for fmt in ('json','jsonl'):
            response=b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt)
            assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
            data=json.loads(response.data)
            assert data['conversation']['schema_version']=='iam-sra-chat-2.0.0'
            assert data['conversation']['suggestion']['level']==4
            assert all(g['status']=='explored' for g in data['conversation']['fn_interview']['stages'])
    finally:manager.close()


@pytest.mark.presidio_live
def test_real_detector_accepts_fn_opening_and_grounded_interpretation_metadata():
    from iam_sra.privacy import detector, require_safe_data
    detector()
    from iam_sra.chat_policy import WELCOME
    require_safe_data({'text':WELCOME})
    require_safe_data({'interpretation':{'action':'advance','answer_kind':'substantive',
        'answer_quote':'A synthetic general answer.',
        'coverage':[{'goal':'drone_description','evidence_id':'m18','quote':'A synthetic general answer.','status':'explored','answer_kind':'substantive'}],
        'topics':[],'boundary_goals':[]}})


@pytest.mark.parametrize('story',['draft_only','embedded'])
def test_varied_organisation_story_runs_to_review_without_inventing_tested_arrangements(story):
    source={r['id']:r for r in GOLDEN['organisational']}
    answers={key:row['answer'] for key,row in source.items()}
    overrides={'planning':'Yes. We have a draft plan only.','preparation':'no','testing':'no','operational':'no'} if story=='draft_only' else {
        'planning':'yes','preparation':'yes','testing':'yes','integration':'yes',
        'routine':'The adopted arrangements are in our normal processes.','operational':'yes',
        'operational_evidence':'Staff, documented procedures and ongoing monitoring are established for our own remit.'}
    answers.update(overrides)
    class Story:
        def turn(self,request):
            goal=request['fn']['evidence_goal'];row=source.get(goal,{})
            kind=row.get('answer_kind','substantive')
            if goal in overrides:
                from iam_sra.fn_interview import literal_answer
                kind=literal_answer(request['answer']) or 'substantive'
            return reply(request,kind=kind,topics=row.get('topics',[]),boundary=['monitoring'] if goal=='operational_evidence' else [])
    s=ChatSession(bank(),synthetic=True);c=Story();s.send('B',c)
    asked=[]
    for _ in range(80):
        if s.stage!='conversation':break
        goal=s.objective;asked.append(goal);s.send(answers.get(goal,'I do not know.'),c,score_client=ScoreFixture())
    assert s.stage=='review' and s.context['responsibilities']
    if story=='draft_only':
        assert 'lessons' not in asked and 'integration' not in asked
        assert not any(m['text']=='The adopted arrangements are in our normal processes.' for m in s.active_evidence())
    else:assert 'operational_evidence' in asked and 'monitoring' in asked
    assert not any('aircraft certification' in m['text'] for m in s.messages if m['role']=='assistant')


def test_component_lab_story_never_presupposes_operational_demonstration():
    source={r['id']:r for r in GOLDEN['technical']}
    answers={key:row['answer'] for key,row in source.items()}
    answers.update(organisation_context='A synthetic laboratory.',technical_role='Controller testing only.',
        technical_object='A safety-controller component v1, not the aircraft.',expertise='The controller only.',
        representative='no',demonstrated='no',operational_prototype='no',complete='no',
        outstanding='The controller has only been validated in the laboratory.')
    class Lab:
        def turn(self,req):
            row=source.get(req['fn']['evidence_goal'],{})
            return reply(req,kind=row.get('answer_kind','substantive'),topics=row.get('topics',[]))
    s=ChatSession(bank(),synthetic=True);c=Lab();s.send('C',c);asked=[]
    for _ in range(80):
        if s.stage!='conversation':break
        asked.append(s.objective);s.send(answers.get(s.objective,'I do not know.'),c,score_client=ScoreFixture())
    assert s.stage=='review' and 'component' in s.context['technical_object']
    assert 'operational_interfaces' not in asked and 'safety_demonstrated' not in asked
    assert not any('actual environment' in r['text'] for r in s.active_evidence())


def test_concept_only_technical_story_focuses_on_low_boundary_without_manufacturing_score():
    s,c=start('technical')
    for text in ('A synthetic research unit.','Concept modelling only.','A proposed energy model.','The concept only.'):
        s.send(text,c)
    # Explicit lack of experiments authorises FN's conceptual-work focus; it
    # does not automatically assign a level or infer inability.
    for _ in range(50):
        if s.stage!='conversation':break
        goal=s.objective
        answer='no' if goal=='experimental' else 'Energy is my priority.' if goal=='priorities' else 'A conceptual energy model; no experiments are claimed.'
        s.send(answer,c)
    assert s.stage=='review' and s.suggestion['level'] is None
    assert 'controlled' not in s.fn.asked and 'operational_prototype' not in s.fn.asked
    assert s.fn.facts['experimental']=='no'
    stages={row['id']:row for row in s.export()['fn_interview']['stages']}
    assert stages['controlled']['status']=='not_applicable'
    assert stages['controlled']['goals']==[]


def test_outside_organisation_remit_finishes_partial_without_any_scoring_call():
    s,c=start('organisational')
    class Outside:
        def turn(self,req):
            out=reply(req)
            out['interpretation']['scope_disposition']='outside_remit'
            return out
    scorer=ScoreFixture()
    s.send('A synthetic records unit.',c)
    s.send('Drone service decisions and operation fall outside our remit.',Outside(),score_client=scorer)
    assert s.stage=='review' and s.partial and s.context['scope_status']=='outside_remit'
    assert not scorer.calls and s.suggestion['level'] is None


def test_ambiguous_end_choice_does_not_record_agreement():
    s,c=start();s.partial=True;s._report(score_client=ScoreFixture())
    original=deepcopy(s.suggestion)
    s.send('A or C',c)
    assert s.stage=='review' and s.participant_review is None and s.suggestion==original
    s.send('A. It describes me well but something is missing',c)
    assert s.stage=='review' and s.participant_review is None
    s.send('B',c)
    assert s.stage=='review_addition' and s.participant_review['choice']=='B'


def test_post_result_correction_invalidates_current_judgment_and_preserves_initial_revision():
    s,c=start();s.send('yes',c);s.send('An aircraft without an onboard pilot.',c)
    s.partial=True;s._report(score_client=ScoreFixture())
    initial=deepcopy(s.suggestion)
    s.send('go back',c)
    s.send('I am unsure what the earlier term meant.',c)
    assert s.stage=='review_addition' and s.suggestion is None
    assert s.initial_results[-1]['suggestion']==initial
    assert s.participant_review['status']=='pending_after_new_evidence'
    s.send('no changes',c)
    assert s.stage=='ended' and s.initial_results[-1]['suggestion']==initial


@pytest.mark.presidio_live
@pytest.mark.parametrize('key',list(GOLDEN))
def test_real_detector_fn_profile_city_opening_and_export(key):
    """Real privacy, synthetic semantic client; no Qwen or socket services."""
    from iam_sra.privacy import detector, screened_export
    try:detector()
    except PrivacyError as exc:
        if exc.code=='privacy_unavailable':pytest.skip('Pinned detector resources required')
        raise
    from iam_sra.readiness_bank import load_bank
    s=ChatSession(load_bank(),'extended' if key=='citizen_extended' else 'short',synthetic=True)
    c=SyntheticInterpreter()
    s.send('A. Citizen' if key.startswith('citizen') else 'B. Organisation or institution' if key=='organisational' else 'C. Technology expert or researcher',c)
    s.send('Madrid',c)
    if key.startswith('citizen'):s.send('35 minutes' if key=='citizen_extended' else '20 minutes',c)
    s.send('yes' if key.startswith('citizen') else 'A planning unit.' if key=='organisational' else 'A technical research unit.',c)
    assert s.profile==('citizen' if key.startswith('citizen') else key)
    assert s.context['city']=='Madrid' and s.stage=='conversation'
    out=screened_export({'conversation':s.export()})
    assert out['conversation']['schema_version']=='iam-sra-chat-2.0.0'
    assert out['conversation']['suggestion'] is None


def test_depth_change_after_result_cannot_switch_the_scale_under_initial_judgment():
    s,c=start();s.partial=True;s._report(score_client=ScoreFixture())
    original=deepcopy(s.suggestion);scale=deepcopy(s.view()['scale'])
    s.send('extended conversation',c)
    assert s.depth=='short' and s.stage=='review' and s.suggestion==original
    assert s.view()['scale']==scale


@pytest.mark.parametrize('key',list(GOLDEN))
def test_score_compaction_preserves_all_originals_and_all_nine_exact_scale_texts(key):
    from iam_sra.chat_score import compact_score_request
    s,c,scorer,questions=replay(key)
    original=scorer.calls[-1];before=deepcopy(original)
    wire=compact_score_request(original)
    restored=[dict(zip(wire['original_columns'],row)) for row in wire['originals']]
    assert restored==original['originals'] and original==before
    assert len(wire['anchors'])==9
    assert [(a['id'],a['level'],a['label'],a['description']) for a in wire['anchors']]==[(a['id'],a['level'],a['label'],a['description']) for a in original['anchors']]
    assert wire['supplied_information']==original['supplied_information']


@pytest.mark.parametrize('key',list(GOLDEN))
def test_each_canonical_question_locator_points_to_its_actual_pdf_page(key):
    import re
    register=json.loads((ROOT/'references/chat-source-register.json').read_text())
    path=ROOT/'references/private'/register['sources'][key]['document']
    pages=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True).split('\f')
    normal=lambda s:' '.join(s.replace('\u200b','').split())
    for stage in specification()['flows'][key]:
        for node in stage['questions']:
            if 'authored' in node['source_locator']:continue
            page=int(re.search(r'\d+',node['source_locator']).group())
            assert normal(node['canonical_question']) in normal(pages[page-1]),node['id']


@pytest.mark.parametrize('key',list(GOLDEN))
def test_last_asked_but_unanswered_goal_does_not_authorize_completion(key):
    s=ChatSession(bank(),'extended' if key=='citizen_extended' else 'short',synthetic=True)
    assert s.view()['completion']['methodological_progression']=='incomplete'
    c=GoldenInterpreter(key);scorer=ScoreFixture()
    s.send('A' if key.startswith('citizen') else 'B' if key=='organisational' else 'C',c)
    for row in GOLDEN[key][:-1]:
        s.send(row['answer'],c,score_client=scorer)
        if s.objective=='citizen_duration':s.send('35 minutes' if key=='citizen_extended' else '20 minutes',c)
    assert not s._discussion_progress()['may_propose_conclusion']
    assert s.view()['completion']['methodological_progression']=='incomplete'
    assert s.suggestion is None
    s.send(GOLDEN[key][-1]['answer'],c,score_client=scorer)
    assert s.stage=='review' and s._discussion_progress()['may_propose_conclusion']


def test_unknown_test_results_do_not_authorize_a_probe_presupposing_changes_from_them():
    s,c=start('technical')
    s.fn.asked.append('noise_test')
    s.fn.record('noise_test','m2','unknown','uncertain')
    node=s.fn.current(s.profile,s.depth,'noise_changes')
    assert not s.fn.applicable(node,s.concerns)
