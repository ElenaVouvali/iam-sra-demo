"""Simplified full UI with explicit doubles, not a semantic validation claim."""
from test_ui import fresh,click,assert_simple
from test_confirmation import Fake,meaning
from iam_sra.session import State


def test_ui_full_validation_and_export(monkeypatch):
    client=Fake(meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']},position='opposed'))
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value('I oppose the hum and cameras.');click(app)
    assert_simple(app);assert app.session_state.session.initial is None
    app.checkbox(key='confirm_1').check().run();click(app)
    app.session_state.session.require_combined_review=True
    click(app,'Continue to follow-up questions')
    s=app.session_state.session;original=s.initial
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
        assert_simple(app)
    if not any(x.key=='joint_choice' for x in app.radio):click(app,'Assess the combined proposal')
    app.radio(key='joint_choice').set_value('unsure');click(app)
    assert_simple(app)
    app.checkbox(key='updated_confirm_'+str(s.version)).check().run();click(app)
    assert s.state==State.FINAL and s.initial==original
    assert len(app.metric)==1 and app.metric[0].label=='Updated SRL after follow-ups'
    assert not app.dataframe and not app.json and len(app.get('download_button'))==2
    data=s.export()
    assert data['final_summary']['selected_profile']=='final_original'
    assert data['final_summary']['modified_assessment_attempted']
    assert len(data['domain_assessments'])==15
    assert data['final_assessment_review']['initial_aggregate']


def test_multiple_choice_answers_finish_directly_without_model_calls_or_outcome_review(monkeypatch):
    client=Fake(meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']}))
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value('I oppose the hum and camera viewing.');click(app)
    app.checkbox(key='confirm_1').check().run();click(app)
    def unexpected(*args,**kwargs):raise AssertionError('Fixed-choice follow-ups must not invoke the model.')
    client.interpret=unexpected;client.score=unexpected
    click(app,'Continue to follow-up questions');s=app.session_state.session
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        assert not any('Score effects:' in x.value for x in app.caption)
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
    assert s.state==State.FINAL and s.updated_confirmed
    assert len(app.metric)==1
    assert not any(c.label=='This reflects what I meant' for c in app.checkbox)
    assert not any(e.label=='Check whether changes work together (optional)' for e in app.expander)
    assert len(s.export()['dialogue_and_confirmations']['presented_followups'])==len(s.responses)
