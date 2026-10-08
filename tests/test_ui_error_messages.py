"""FN-response regressions for confirmation controls and model-error attribution."""
import json
from pathlib import Path
import pytest
from iam_sra.assessment import AssessmentError
from iam_sra.session import State
from iam_sra.ui_errors import user_error
from test_confirmation import Fake,meaning
from test_ui import fresh,click

ROOT=Path(__file__).resolve().parents[1]
FN=json.loads((ROOT/'eval/fn_reference.json').read_text())['citizen_text']


def fn_client():
    m=meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']})
    m.concerns[-1].position='supported'
    return Fake(m)


def test_fn_response_can_complete_with_explicit_confirmations(monkeypatch):
    app=fresh(monkeypatch,fn_client());click(app)
    app.text_area(key='citizen_answer').set_value(FN);click(app)
    s=app.session_state.session
    assert s.state==State.INTERPRETATION and not app.error
    assert next(b for b in app.button if b.label=='Continue').disabled
    assert any('Tick' in c.value for c in app.caption)
    app.checkbox(key='confirm_'+str(s.version)).check().run();click(app)
    assert app.metric[0].value=='4/9' and not app.error
    click(app,'Continue to follow-up questions')
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
    assert not any(b.label=='Confirm and finish' for b in app.button)
    assert s.state==State.FINAL and app.metric[0].value=='6/9' and not app.error


def test_fn_model_evidence_failure_is_not_reported_as_missing_user_answer(monkeypatch):
    client=fn_client();interpret=client.interpret
    def fail(*args,**kwargs):
        raise AssessmentError('Unsupported private diagnostic quotation',code='evidence')
    client.interpret=fail
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value(FN);click(app)
    assert app.session_state.session.state==State.ANSWER
    assert app.text_area(key='citizen_answer').value==FN
    assert 'model returned supporting passages' in app.error[0].value
    assert 'Please choose an answer' not in app.error[0].value
    assert 'private diagnostic quotation' not in app.error[0].value
    assert app.session_state.failure_details['error_code']=='evidence'
    assert app.session_state.session.inference[-1]['stage']=='initial interpretation failure'
    assert any(e.label=='Technical details for this failed attempt' for e in app.expander)
    client.interpret=interpret;click(app)
    assert not app.error and app.session_state.session.state==State.INTERPRETATION
    assert 'failure_details' not in app.session_state


def test_missing_followup_selection_has_specific_instruction(monkeypatch):
    app=fresh(monkeypatch,fn_client());click(app)
    app.text_area(key='citizen_answer').set_value(FN);click(app)
    app.checkbox(key='confirm_1').check().run();click(app)
    click(app,'Continue to follow-up questions')
    s=app.session_state.session;q=s.current_question;initial=s.initial
    click(app)
    assert 'Select one answer to this follow-up question' in app.error[0].value
    assert s.current_question==q and not s.responses and s.initial==initial


def test_incomplete_model_mapping_stays_retryable_without_confirmation(monkeypatch):
    client=fn_client()
    client.last_settings={'unresolved_facet_reviews':{'noise:acoustic_impact':{'code':'schema'}}}
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value(FN);click(app)
    assert app.session_state.session.state==State.ANSWER
    assert app.session_state.session.draft is None
    assert app.text_area(key='citizen_answer').value==FN
    assert 'do not need to rewrite' in app.error[0].value
    assert not any(c.label=='This reflects what I meant' for c in app.checkbox)
    client.last_settings={};click(app)
    assert not app.error and app.session_state.session.state==State.INTERPRETATION


def test_production_initial_mapper_uses_expressed_issue_pipeline():
    from iam_sra.settings import config
    assert config('prompts')['initial_mapping']=='direct_interpretation'


@pytest.mark.parametrize('error,expected',[
    (ValueError('Explicit confirmation is required before scoring.'),'Tick'),
    (ValueError('Explicit updated-meaning confirmation is required.'),'Review your follow-up'),
    (AssessmentError('Enter 1–4000 UTF-8 bytes; input is never truncated.'),'4000 UTF-8 bytes'),
    (AssessmentError('Please explain what should be corrected.',code='clarification'),'Explain what should be corrected'),
    (AssessmentError('Invalid history quotation',code='evidence'),'model returned supporting passages'),
    (AssessmentError('hash mismatch',code='confirmation'),'confirm'),
    (AssessmentError('hidden diagnostic',code='timeout'),'exceeded the time limit'),
    (AssessmentError('hidden diagnostic',code='schema'),'required answer format'),
    (AssessmentError('hidden diagnostic',code='truncated'),'stopped before it was complete'),
    (ValueError('Unexpected private backend detail'),'We could not complete this step'),
])
def test_error_instructions_are_actionable_and_do_not_expose_raw_diagnostics(error,expected):
    message=user_error(error)
    assert expected in message
    assert 'Please choose an answer or clarify the indicated view' not in message
    assert 'private backend detail' not in message and 'hash mismatch' not in message


def test_uncertain_details_are_not_printed_in_interpretation_summary(monkeypatch):
    from test_confirmation import Fake,meaning
    from iam_sra.reporting import clarification_needs
    app=fresh(monkeypatch,Fake(meaning(scores=('airspace_capacity',),position='uncertain')));click(app)
    app.text_area(key='citizen_answer').set_value('I cannot decide about aircraft separation.');click(app)
    assert clarification_needs(app.session_state.session)
    assert all('Not yet clear:' not in item.value for item in app.markdown)


def test_pre_model_confirmation_validation_has_actionable_developer_diagnostics(monkeypatch):
    app=fresh(monkeypatch,fn_client());click(app)
    app.text_area(key='citizen_answer').set_value(FN);click(app)
    s=app.session_state.session
    draft=s.draft.model_dump()
    def fail_confirmation(*args,**kwargs):
        raise ValueError('Diagnostic confirmation failure')
    s.confirm=fail_confirmation
    app.checkbox(key='confirm_1').check().run();click(app)
    details=app.session_state.failure_details
    assert details['message']=='Diagnostic confirmation failure'
    assert details['exception_type']=='ValueError'
    assert details['session_state']==State.INTERPRETATION.value
    assert details['action'].endswith('prepare')
    assert details['failure_location']['function']=='fail_confirmation'
    assert details['request']=={} and details['diagnostics']==[]
    assert s.draft.model_dump()==draft and s.confirmed is None
    assert 'Diagnostic confirmation failure' not in app.error[0].value
