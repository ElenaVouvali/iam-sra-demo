"""FN adaptive regression tests: routing helpers and source-critical questions.

These are deterministic checks. Live inference, evidence interpretation and
conversation quality require the separate synthetic/human transcript review.
"""
from iam_sra.adaptive_interview import (
    adaptive_goal, explicit_priority_commitment, supplementary_recognition_coverage)
from iam_sra.fn_interview import FNInterview
from iam_sra.chat_client import FNReply


def test_two_topics_alone_do_not_skip_fn_open_or_suggestions(monkeypatch):
    monkeypatch.setenv('IAM_CHAT_ADAPTIVE_MODE', '1')
    fn = FNInterview()
    concerns = [
        {'topic': 'noise', 'evidence_ids': ['m9'], 'spontaneously_raised': True},
        {'topic': 'wildlife', 'evidence_ids': ['m9'], 'spontaneously_raised': True},
    ]
    assert fn.applicable({'id': 'open_more'}, concerns)
    assert fn.applicable({'id': 'suggested_topics'}, concerns)
    fn.facts['topic_scope_closed'] = True
    assert not fn.applicable({'id': 'open_more'}, concerns)
    assert not fn.applicable({'id': 'suggested_topics'}, concerns)


def test_priority_requires_explicit_choice_not_general_safety_opinion():
    assert not explicit_priority_commitment('We should prioritise avoiding noise and safety problems.')
    assert not explicit_priority_commitment('I think we should make sure we do not disturb residents.')
    assert explicit_priority_commitment('My two main priorities are noise and wildlife.')
    assert explicit_priority_commitment('I want to focus on noise and wildlife.')


def test_clear_drone_definition_is_reusable_not_converted_to_assessed_readiness():
    assert supplementary_recognition_coverage('citizen', 'drone_recognition',
        'Yes, it is an aircraft without a pilot, I think.', 'yes') == [('drone_description', 'substantive')]
    assert supplementary_recognition_coverage('citizen', 'drone_recognition',
        'No, I do not know what a drone is.', 'no') == []
    assert supplementary_recognition_coverage('citizen', 'drone_recognition',
        'It might be a flying toy, but I am not sure.', 'uncertain') == []


def test_healthcare_awareness_reuses_only_prior_heard_information():
    statement = 'For photography, videos and I also heard recently about healthcare services.'
    assert supplementary_recognition_coverage('citizen', 'drone_uses', statement, 'substantive') == [
        ('healthcare_awareness', 'yes')]
    assert supplementary_recognition_coverage('citizen', 'drone_uses',
        'Could they ever be used for healthcare?', 'substantive') == []
    assert supplementary_recognition_coverage('citizen', 'drone_uses', statement, 'substantive', [
        {'kind': 'authored_general_background', 'categories': ['delivery_basics']}]) == []


def test_source_critical_questions_and_prefaces_are_not_rewritten():
    for goal in ('open_priorities', 'open_more', 'different_impacts', 'priorities',
                 'decisions', 'participation', 'drone_description'):
        assert not adaptive_goal({'id': goal, 'response_type': 'open'})
    assert not adaptive_goal({'id': 'conditions', 'response_type': 'open',
                              'preface': 'Imagine a proposed service.'})
    assert adaptive_goal({'id': 'priority_understanding', 'response_type': 'open'})


def test_fn_wire_has_no_free_form_decision_summary():
    schema = FNReply.model_json_schema()
    prop = schema['properties']['decision_summary']
    assert prop.get('const') == '' or prop.get('enum') == ['']
    assert FNReply.model_fields['decision_summary'].default == ''



def test_past_drone_definition_and_healthcare_use_advance_without_repetition(monkeypatch):
    monkeypatch.setenv('IAM_CHAT_ADAPTIVE_MODE', '1')
    monkeypatch.setenv('IAM_CHAT_MAX_ADAPTIVE_QUESTIONS', '0')
    from indicator_fixtures import bank
    from fn_fixture import reply
    from iam_sra.chat_session import ChatSession

    class MinimalInterpreter:
        def turn(self, request):
            kind = 'yes' if request['fn']['evidence_goal'] == 'drone_recognition' else 'substantive'
            return reply(request, kind=kind)

    client = MinimalInterpreter()
    s = ChatSession(bank(), synthetic=True)
    for text in ('A', 'Madrid', 'B'):
        s.send(text, client)
    assert s.objective == 'drone_recognition'
    s.send('Yes, it is an aircraft without a pilot, I think.', client)
    assert s.objective == 'drone_uses'
    first = s.active_evidence()[-1]['id']
    assert s.fn.coverage['drone_description']['evidence_ids'] == [first]
    s.send('For photography, videos and I also heard recently about healthcare services.', client)
    assert s.objective == 'drone_other_uses'
    second = s.active_evidence()[-1]['id']
    assert s.fn.coverage['healthcare_awareness']['evidence_ids'] == [second]
    assert s.fn.facts['healthcare_awareness'] == 'yes'
    s.send('No other uses come to mind.', client)
    assert s.objective == 'healthcare_detail'  # What had you heard, not repeated basic awareness.
