"""Citizen flow skips redundant discovery without changing initial scoring."""
from copy import deepcopy
from iam_sra.session import Session,State
from test_confirmation import Fake,meaning


def initial(position='opposed'):
    client=Fake(meaning(position=position,scores=('noise',)))
    session=Session();session.begin();session.submit('The hum bothers me.',client)
    session.confirm(True,defer_discovery=True);session.score_initial(client)
    return session,client


def test_assessed_answer_goes_directly_to_second_followup_set():
    session,client=initial()
    snapshot=deepcopy(session.initial);confirmed=deepcopy(session.confirmed)
    calls=len(client.calls)
    session.continue_initial_review()
    assert session.state==State.FOLLOWUPS
    assert session.current_question['id']=='u_change_noise'
    assert session.discovery_finished
    assert session.discovery_stop_reason=='covered_by_targeted_followups'
    assert session.discovery_questions==[] and session.discovery_responses==[]
    assert session.blockers=={}
    assert session.initial==snapshot and session.confirmed==confirmed
    assert len(client.calls)==calls


def test_assessed_acceptance_without_reservations_needs_no_question():
    session,_=initial('supported')
    session.continue_initial_review()
    assert session.state==State.UPDATED
    assert session.questions==[] and session.discovery_questions==[]


def test_ui_opposition_shows_targeted_question_without_discovery(monkeypatch):
    from test_ui import fresh,click
    client=Fake(meaning(position='opposed',scores=('noise',)))
    app=fresh(monkeypatch,client);click(app)
    app.text_area(key='citizen_answer').set_value('The hum bothers me.');click(app)
    app.checkbox(key='confirm_1').check().run();click(app)
    click(app,'Continue to follow-up questions')
    session=app.session_state.session
    assert session.state==State.FOLLOWUPS
    assert app.radio(key='choice_u_change_noise')
    assert session.discovery_questions==[]
    assert not any(button.label=='Finish these questions' for button in app.button)


def test_single_set_reaches_combined_acceptance_and_final_export():
    from test_updates import FacetFake,answer_all
    client=FacetFake(meaning(position='opposed',scores=('noise',)))
    session=Session();session.begin();session.submit('The hum bothers me.',client)
    session.confirm(True,defer_discovery=True);session.score_initial(client)
    session.continue_initial_review();answer_all(session,client)
    assert session.state==State.UPDATED and session.joint_required
    session.record_joint('accept',[],'The modified sound is acceptable.',client)
    session.continue_final(True,client)
    assert session.state==State.FINAL
    assert session.discovery_questions==[]
    assert session.export()['final_summary']['modified_assessment_attempted']
