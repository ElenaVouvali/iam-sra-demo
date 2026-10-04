"""Simplified full UI with explicit doubles, not a semantic validation claim."""
from test_ui import fresh,click,assert_simple
from test_confirmation import Fake,meaning
from iam_sra.session import State


def test_ui_full_validation_and_export(monkeypatch):
    client=Fake(meaning(scores=('noise','perceived_safety_privacy','welfare_equity'),facets={'perceived_safety_privacy':['personal_privacy']},position='opposed'))
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value('I oppose the hum and cameras.');click(app)
    assert_simple(app);assert app.session_state.session.initial is None
    click(app,'Finish these questions')
    app.checkbox(key='reference_mode').check().run()
    app.checkbox(key='confirm_1').check().run();click(app)
    s=app.session_state.session;original=s.initial
    while s.state==State.FOLLOWUPS:
        q=s.current_question
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0]);click(app)
        assert_simple(app)
    app.radio(key='joint_choice').set_value('unsure');click(app)
    assert_simple(app)
    app.checkbox(key='updated_confirm_'+str(s.version)).check().run();click(app)
    assert s.state==State.FINAL and s.initial==original
    assert len(app.metric)==1 and app.metric[0].label=='Provisional scenario-readiness score'
    assert not app.dataframe and not app.json and len(app.get('download_button'))==2
    data=s.export()
    assert data['final_summary']['selected_profile']=='final_original'
    assert data['final_summary']['modified_assessment_attempted']
    assert len(data['domain_assessments'])==15
    assert any('modified proposal' in item.value for item in app.info)
