"""Administrative product adaptations plus grounded topic semantics, not model quality claims."""
from copy import deepcopy
import pytest
from iam_sra.chat_session import ChatSession
from iam_sra.chat_policy import INTRODUCTION, PERSPECTIVE, ACKNOWLEDGEMENTS, EASA_BASICS, educational_choice
from iam_sra.privacy import require_safe_data
from indicator_fixtures import bank
from fn_fixture import SyntheticInterpreter, reply


def citizen(choice='A'):
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    s.send('A',c);s.send('Madrid',c)
    assert s.objective=='citizen_duration'
    s.send(choice,c)
    return s,c


@pytest.mark.parametrize('answer,profile', [('A','citizen'),('A. Citizen','citizen'),('my personal views','citizen'),
    ('B','organisational'),('B. Organisation or institution','organisational'),('our organisation responsibilities','organisational'),
    ('C','technical'),('C. Technology expert or researcher','technical'),('a technology subsystem','technical')])
def test_full_introduction_roles_acknowledgement_then_city(answer,profile):
    s=ChatSession(bank(),synthetic=True);c=SyntheticInterpreter()
    assert s.messages[0]['text']==INTRODUCTION and s.messages[1]['text']==PERSPECTIVE
    assert all(word in INTRODUCTION.lower() for word in ['thank you','emerging technologies','no right or wrong','experiences','skip','withdraw','screening can miss','temporarily'])
    assert all(word in PERSPECTIVE.lower() for word in ['patient','regulator','manufacturer','more than one'])
    assert s.view()['scale'] is None
    s.send(answer,c)
    assert s.profile==profile and s.messages[-2]['text']==ACKNOWLEDGEMENTS[profile]
    assert s.objective=='area'
    s.send('Madrid',c)
    assert s.objective==('citizen_duration' if profile=='citizen' else 'organisation_context')
    assert not s.calls and s.suggestion is None


@pytest.mark.parametrize('choice,depth,provenance',[('A','short','participant_choice'),('B','extended','participant_choice'),
    ('20 minutes','short','participant_choice'),('around thirty-five minutes','extended','participant_choice'),
    ('a brief conversation','short','participant_choice'),('more detail','extended','participant_choice'),
    ('not sure','short','default_after_uncertainty'),('skip this question','short','default_after_skip')])
def test_depth_choice_is_explicit_non_scoring_and_source_versioned(choice,depth,provenance):
    s,c=citizen(choice)
    assert s.objective=='drone_recognition' and s.depth==s.view()['citizen_depth']==depth
    selected=s.depth_selection
    assert selected['provenance']==provenance and not selected['readiness_inferred']
    assert ('35min' if depth=='extended' else '20min') in selected['source']['document']
    assert selected==s.decision_traces[-1]['depth_change']
    assert selected['evidence_id'] not in {e['id'] for e in s.active_evidence()}


@pytest.mark.parametrize('choice',['A','B'])
def test_yes_preserves_prior_knowledge_sequence_without_supplied_examples(choice):
    s,c=citizen(choice);s.send('yes',c)
    assert s.objective=='drone_description' and not s.exposures
    s.send('An aircraft without an onboard pilot.',c)
    assert s.objective=='drone_uses' and not s.exposures
    s.send('Photography and inspection.',c)
    assert s.objective==('drone_other_uses' if choice=='B' else 'healthcare_awareness')


@pytest.mark.parametrize('choice,word',[('A','have'),('B','be')])
def test_no_permissioned_exact_explanation_is_information_exposure(choice,word):
    s,c=citizen(choice);s.send('no',c)
    node=s.fn.current(s.profile,s.depth,'drone_explanation')
    assert s.messages[-1]['resource']==EASA_BASICS
    assert s.exposures[-1]['engagement']=='offered_not_verified'
    s.send('A',c)
    assert s.objective=='healthcare_awareness'
    exposure=next(e for e in s.exposures if e['kind']=='FN_explanation')
    assert exposure['text']==node['explanation'] and f'Drones can {word} different sizes' in exposure['text']
    assert not exposure['prior_knowledge']
    assert not any(e['text']==exposure['text'] for e in s.active_evidence())


@pytest.mark.parametrize('answer',['B','B — The educational resource, then finish for now.','open the resource','I would like to read the guide','I want to finish for now and read later','stop'])
def test_educational_exit_has_no_scale_result_or_scorer(answer):
    s,c=citizen();s.send('no',c)
    class NoScore:
        def match_profile(self,payload):raise AssertionError('Educational exit must not score')
    s.send(answer,c,score_client=NoScore())
    assert s.stage=='ended' and s.stop_reason=='ended_early_after_recognition' and s.partial
    assert s.suggestion is None and not s.indicator_results and s.view()['scale'] is None
    assert s.view()['completion']['evidence_sufficiency']=='unassessed'
    assert s.export()['stop_reason']=='ended_early_after_recognition'
    assert s.exposures[-1]['engagement']=='selected_not_verified'
    assert not any(e['kind']=='FN_explanation' for e in s.exposures)


@pytest.mark.parametrize('text',["What is the resource?",'not sure','I do not want to finish','I do not want to open the link'])
def test_resource_questions_or_uncertainty_do_not_consent_to_educational_exit(text):
    assert educational_choice(text)!='finish'


def test_declining_explanation_can_continue_without_information_contamination():
    s,c=citizen();s.send('no',c);s.send('continue without explanation',c)
    assert s.objective=='healthcare_awareness'
    assert not any(e['kind']=='FN_explanation' for e in s.exposures)


class Topics:
    def __init__(self,topics=(),intent=None,alias=None):self.topics=topics;self.intent=intent;self.alias=alias
    def turn(self,request):
        out=reply(request,topics=self.topics)
        if self.intent:
            out['interpretation'].update(topic_intent=self.intent,topic_intent_quote=request['answer'])
        if self.alias:out['interpretation']['topics'][0]['matches_topic']=self.alias
        return out


def open_topics(choice='A'):
    s,c=citizen(choice)
    for text in ('no','no','no','unknown'):s.send(text,c)
    assert s.objective=='open_priorities'
    return s,c


def test_single_topic_invites_others_and_explicit_one_priority_is_allowed():
    s,c=open_topics();s.send('Noise concerns me.',Topics(['noise']))
    assert s.objective=='open_more' and "You've mentioned noise" in s.messages[-1]['text']
    assert not s.priorities
    s.send('Noise is the only issue I want to focus on.',Topics(['noise'],intent='main_only'))
    assert [p['topic'] for p in s.priorities]==['noise']
    assert 'priorities' in s.fn.coverage and s.fn.facts['topic_scope_closed']
    assert s.objective!='open_more' and s.objective!='suggested_topics'


def test_multiple_topics_explicitly_closed_do_not_repeat_invitation():
    s,c=open_topics();s.send('Noise and wildlife are all I want to discuss.',Topics(['noise','wildlife'],intent='no_more'))
    assert 'open_more' not in s.fn.asked
    assert len(s._raised_topics())==2 and not s.priorities
    s.send('Residents and nesting birds might be affected.',c)
    assert s.objective=='priorities'
    s.send('Wildlife is my priority.',Topics(['wildlife']))
    assert [p['topic'] for p in s.priorities]==['wildlife']


@pytest.mark.parametrize('choice',['A','B'])
def test_suggestions_follow_open_discussion_and_use_selected_source(choice):
    s,c=open_topics(choice)
    assert not s.exposures or all(e['kind']!='suggested_topics' for e in s.exposures)
    s.send('Noise concerns me.',Topics(['noise']))
    s.send('Could you suggest some other issues?',Topics(intent='suggestions'))
    assert s.objective=='suggested_topics'
    from iam_sra.fn_interview import specification,flow_key
    assert all(t in s.messages[-1]['text'] for t in specification()['topic_suggestions'][flow_key(s.profile,s.depth)])
    assert s.exposures[-1]['kind']=='suggested_topics' and not s.priorities


def test_semantic_alias_merges_a_concern_without_indicator_counting():
    s,c=open_topics();s.send('Noise bothers me.',Topics(['noise']))
    s.send('Aircraft sound is my main concern.',Topics(['aircraft sound'],alias='noise'))
    assert len(s._raised_topics())==1 and s._raised_topics()[0]['topic']=='noise'
    assert len(s._raised_topics()[0]['evidence_ids'])==2


def test_depth_change_preserves_old_scale_exposure_and_does_not_reask_basics():
    s,c=open_topics();s.send('show the scale',c)
    shown=deepcopy(s.messages[-1]['scale']);old_ids={m['id'] for m in s.messages}
    s.send('more detail',c)
    assert s.depth=='extended' and len(s.depth_history)==2
    assert shown['source']['document'].endswith('20min.pdf')
    assert s.messages[next(i for i,m in enumerate(s.messages) if m.get('scale'))]['scale']==shown
    assert s.objective not in {'area','citizen_duration','drone_recognition','drone_description','drone_uses','drone_other_uses'}
    assert old_ids<={m['id'] for m in s.messages}


@pytest.mark.presidio_live
def test_real_privacy_accepts_new_onboarding_educational_exit_and_export():
    s,c=citizen('B');s.send('no',c);s.send('B',c)
    require_safe_data(s.export())


def test_natural_mid_interview_depth_request_and_uncertain_duration():
    s,c=citizen("I'm not sure how much time")
    assert s.depth=='short' and s.depth_selection['provenance']=='default_after_uncertainty'
    s.send('Can we switch to 35 minutes?',c)
    assert s.depth=='extended' and s.depth_selection['provenance']=='participant_change'


def test_untrusted_topic_metadata_cannot_select_priorities_or_invent_aliases():
    from iam_sra.chat_client import validate_reply
    s,c=open_topics();s.send('Noise matters.',Topics(['noise']))
    s._user('Aircraft sound also matters.')
    request=s._request('Aircraft sound also matters.')
    out=reply(request,topics=['aircraft sound'])
    out['interpretation'].update(topic_intent='main_only',topic_intent_quote='An invented choice.')
    out['interpretation']['topics'][0]['matches_topic']='invented existing topic'
    validated=validate_reply(out,request)['interpretation']
    assert validated['topic_intent'] is None
    assert validated['topics'][0]['matches_topic'] is None
    assert not s.priorities


def test_corrected_sole_priority_reopens_topic_scope_without_repeating_duration():
    s,c=open_topics();s.send('Noise matters.',Topics(['noise']))
    s.send('Noise is the only issue I want to focus on.',Topics(['noise'],intent='main_only'))
    target=s.priorities[0]['evidence_id'];s.pending_correction=target
    s.send('Actually I also want to discuss wildlife.',c)
    assert 'topic_scope_closed' not in s.fn.facts
    assert not s.priorities and s.depth_selection and 'citizen_duration' in s.fn.coverage
    assert s.objective=='open_more'


def test_owned_api_educational_exit_and_both_exports_are_unassessed():
    import json
    from iam_sra.api import create_app
    from iam_sra.api.adapter import ControllerAdapter
    from iam_sra.api.service import AssessmentService
    from test_indicator_api import factory
    from test_api_integration import Browser
    class NoScore:
        def match_profile(self,payload):raise AssertionError('An educational exit cannot invoke scoring')
    adapter=ControllerAdapter(engine_factory=factory,
        clients_factory=lambda e:{'chat':SyntheticInterpreter(),'chat_score':NoScore()},
        readiness=lambda:{'privacy':'ready','corpus':'ready'})
    manager=AssessmentService(adapter)
    app=create_app({'TESTING':True,'SECRET_KEY':'e'*40},service=manager)
    try:
        b=Browser(app)
        r=b.client.post('/v1/sessions',json={'mode':'chat'},headers={'X-CSRF-Token':b.csrf})
        assert r.status_code==201
        b.view=r.json['session']
        for answer in ('A','Madrid','B','no','B'):b.act('chat_message',{'text':answer})
        chat=b.view['chat']
        assert chat['stage']=='ended' and chat['scale'] is None and chat['suggestion'] is None
        assert chat['completion']['termination_reason']=='ended_early_after_recognition'
        for fmt in ('json','jsonl'):
            r=b.client.get('/v1/sessions/'+b.view['id']+'/export?format='+fmt)
            assert r.status_code==200
            data=json.loads(r.data)['conversation']
            assert data['completion']['partial'] and data['completion']['evidence_sufficiency']=='unassessed'
            assert data['suggestion'] is None and data['depth_selection']['depth']=='extended'
    finally:manager.close()
