"""Full UI path with explicitly injected test doubles, never live validation."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from test_confirmation import Fake, meaning
from test_ui import click

def test_ui_full_validation_and_export(monkeypatch):
    client=Fake(meaning(scores=('noise','perceived_safety_privacy'),facets={'perceived_safety_privacy':['personal_privacy']}))
    monkeypatch.setenv('IAM_MOCK','0')
    monkeypatch.setattr('iam_sra.conversation_client.ConversationClient',lambda:client)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=10).run()
    click(app,'Begin')
    app.text_area(key='citizen_answer').set_value('I oppose the hum and cameras.')
    click(app,'Interpret response')
    assert app.session_state.session.initial is None and not app.metric
    if any(b.label=='Finish discovery' for b in app.button):click(app,'Finish discovery')
    next(c for c in app.checkbox if c.label=='This interpretation reflects what I meant').check().run()
    click(app,'Confirm meaning');click(app,'Calculate initial provisional scores')
    original=app.session_state.session.initial
    app.checkbox(key='all_questions').check().run()
    click(app,'Continue to follow-ups')
    for q in app.session_state.session.questions:
        app.radio(key='choice_'+q['id']).set_value(q['choices'][0])
        click(app,'Interpret and record follow-up')
    app.radio(key='joint_choice').set_value('accept')
    app.text_area(key='joint_text').set_value('Under the combined modifications I accept noise and shielded cameras.')
    click(app,'Interpret combined-proposal response')
    next(c for c in app.checkbox if c.label=='The updated original and hypothetical interpretations reflect what I meant').check().run()
    click(app,'Confirm updated meaning');click(app,'Calculate final provisional scores')
    assert not app.error
    assert app.session_state.session.initial==original
    assert len(app.dataframe[0].value)==15
    assert len(app.get('download_button'))==2
    export=app.session_state.session.export()
    assert export['conditional']['context']=='modified'
    assert export['initial']['aggregate']==export['final_original']['aggregate']
    assert len(export['responses'])==3
