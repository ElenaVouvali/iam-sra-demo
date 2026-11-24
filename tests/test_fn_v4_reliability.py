"""V4 regressions from four live synthetic cases; not semantic validation."""
import pytest
from pydantic import ValidationError

from iam_sra.chat_client import ChatClient
from iam_sra.synthetic_respondent import SimulatedAnswer
from iam_sra.adaptive_interview import adaptive_goal
from test_fn_interpretation import opening, install_http, DEFINITION
from fn_fixture import reply


def test_current_goal_identity_is_server_owned_when_model_semantically_addresses_it(monkeypatch):
    def output(payload, _):
        out = reply(payload)
        out['interpretation']['coverage'] = []
        out['interpretation']['current_goal_addressed'] = True
        return out
    calls = install_http(monkeypatch, output)
    session = opening()
    session.send(DEFINITION, ChatClient())
    assert session.objective == 'drone_uses'
    assert session.fn.coverage['drone_description']['status'] == 'explored'
    assert session.fn.coverage['drone_description']['evidence_ids'] == [session.active_evidence()[-1]['id']]
    assert not session.failures
    assert len([p for p, _ in calls if p == '/v1/chat/completions']) == 1
    wire = next(body['guided_json'] for p, body in calls if p == '/v1/chat/completions')
    semantic = wire['$defs']['FNInterpretation']
    assert semantic['properties']['current_goal_addressed']['type'] == 'boolean'
    assert 'current_goal_addressed' in semantic['required']


def test_semantically_unaddressed_answer_must_not_gain_auto_coverage(monkeypatch):
    def output(payload, _):
        out = reply(payload, action='clarify', coverage=[])
        out['interpretation']['current_goal_addressed'] = False
        out['message'] = 'Could you tell me what you mean by that?'
        return out
    install_http(monkeypatch, output)
    session = opening()
    session.send('This is not about the question.', ChatClient())
    assert 'drone_description' not in session.fn.coverage
    assert session.objective == 'drone_description'
    assert not session.failed_turn_id


def test_invalid_cross_goal_quote_is_never_promoted_to_evidence(monkeypatch):
    def output(payload, _):
        out = reply(payload)
        out['interpretation']['coverage'] = [
            {'goal':'healthcare_awareness', 'evidence_id':payload['current_answer_id'],
             'quote':'Not words the participant said', 'status':'explored'}]
        out['interpretation']['current_goal_addressed'] = True
        return out
    install_http(monkeypatch, output)
    session = opening()
    session.send(DEFINITION, ChatClient())
    assert session.fn.coverage['drone_description']['status'] == 'explored'
    assert 'healthcare_awareness' not in session.fn.coverage


def test_control_marker_rejected_from_synthetic_speech():
    with pytest.raises(ValidationError):
        SimulatedAnswer(text='Control=unsure. I cannot answer.', control='answer')
    assert SimulatedAnswer(text='I am unsure whether the service operates.', control='answer').control == 'answer'


def test_source_critical_questions_are_not_rewritten():
    assert not adaptive_goal({'id':'suggested_topics','response_type':'suggested_topics'})
    assert not adaptive_goal({'id':'priority_understanding','response_type':'open'})
